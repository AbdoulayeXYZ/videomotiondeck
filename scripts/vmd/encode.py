"""Final encode (H.264 + AAC, web/phone friendly) with automatic versioning — never overwrites a previous cut."""
import re, unicodedata
from pathlib import Path
from .common import log, die, run, need, probe_duration


def slug(s):
    s = unicodedata.normalize('NFKD', s or 'video').encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_') or 'video'


def next_version(pr):
    """exports/<Title>_v1.mp4, _v2.mp4 ... (spec "output" overrides)."""
    if pr.spec.get('output'):
        return pr.p(pr.spec['output'])
    d = pr.root / 'exports'; d.mkdir(exist_ok=True)
    base = slug(pr.spec.get('title'))
    k = 1
    while (d / f'{base}_v{k}.mp4').exists():
        k += 1
    return d / f'{base}_v{k}.mp4'


def encode(pr, out=None, crf=18):
    need('ffmpeg', 'Install ffmpeg.')
    pic, wav = pr.build / 'picture.mp4', pr.build / 'master.wav'
    if not pic.exists():
        die('build/picture.mp4 missing — run: vmd.py assemble')
    if not wav.exists():
        die('build/master.wav missing — run: vmd.py mix')
    out = Path(out) if out else next_version(pr)
    out.parent.mkdir(parents=True, exist_ok=True)
    total = probe_duration(pic)
    meta = ['-metadata', f"title={pr.spec.get('title', '')}",
            '-metadata', 'comment=Made with videomotiondeck by AbdoulayeXYZ']
    if pr.spec.get('author'):
        meta += ['-metadata', f"artist={pr.spec['author']}"]
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(pic), '-i', str(wav), '-map', '0:v', '-map', '1:a',
         '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-profile:v', 'high', '-pix_fmt', 'yuv420p',
         '-r', str(pr.fps), '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-t', f'{total:.3f}',
         '-movflags', '+faststart'] + meta + [str(out)])
    mb = out.stat().st_size / 1e6
    log(f'final -> {out}  ({probe_duration(out):.2f}s, {mb:.1f} MB)')
    pr.save_json('last_export.json', {'file': str(out)})
    return out


def split(path, mb=19):
    """Split a big file into <mb> MB parts (for upload limits). Rejoin: cat file.part* > file"""
    p = Path(path); size = p.stat().st_size; chunk = int(mb * 1024 * 1024)
    parts = []
    with open(p, 'rb') as f:
        k = 0
        while True:
            b = f.read(chunk)
            if not b:
                break
            q = p.with_name(f'{p.name}.part{k:02d}'); q.write_bytes(b); parts.append(q); k += 1
    log(f'{p.name}: {size / 1e6:.1f} MB -> {len(parts)} parts. Rejoin with:  cat "{p.name}".part* > "{p.name}"')
    return parts
