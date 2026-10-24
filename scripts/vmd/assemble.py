"""Assemble the picture: scenes, footage clips, stills and freeze-holds -> build/picture.mp4 (hard cuts, no dips to black)."""
import hashlib, json, os, shutil
from pathlib import Path
import numpy as np
from PIL import Image
from .common import log, die, run, need, probe_duration

ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-pix_fmt', 'yuv420p', '-an']


def _hash(obj):
    return hashlib.md5(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _cover(im, W, H):
    r = max(W / im.width, H / im.height)
    return im.resize((int(np.ceil(im.width * r)), int(np.ceil(im.height * r))), Image.LANCZOS)


def _kenburns(src_img, out_dir, n, W, H, mode='push', z=(1.0, 1.06), pan=(0, 0), focus=(0.5, 0.45)):
    """Sub-pixel smooth Ken Burns with PIL affine transforms."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob('f*.jpg'):
        f.unlink()
    base = _cover(src_img.convert('RGB'), int(W * 1.0), int(H * 1.0))
    bw, bh = base.size
    cx0, cy0 = bw * focus[0], bh * focus[1]
    for k in range(n):
        u = k / max(1, n - 1)
        if mode == 'breathe':           # 1 -> z1 -> 1 : invisible in/out joins, ideal for holds
            s = z[0] + (z[1] - z[0]) * (0.5 - 0.5 * np.cos(2 * np.pi * u))
        else:                           # push / pull with ease-in-out
            e = 0.5 - 0.5 * np.cos(np.pi * u)
            s = z[0] + (z[1] - z[0]) * e
        cx = min(max(cx0 + pan[0] * u, W / 2 / s), bw - W / 2 / s)
        cy = min(max(cy0 + pan[1] * u, H / 2 / s), bh - H / 2 / s)
        a = 1 / s
        im = base.transform((W, H), Image.AFFINE, (a, 0, cx - (W / 2) * a, 0, a, cy - (H / 2) * a), resample=Image.BICUBIC)
        im.save(out_dir / f'f{k:05d}.jpg', quality=95)


def _overlay_args(cap_dir, fps):
    return ['-framerate', str(fps), '-i', str(cap_dir / 'f%05d.png')]


def build_picture(pr, tl, force=False):
    need('ffmpeg', 'Install ffmpeg (apt-get install ffmpeg / brew install ffmpeg).')
    W, H = pr.size; fps = pr.fps
    sd = pr.build / 'segs'; sd.mkdir(exist_ok=True)
    files = []
    for idx, r in enumerate(tl):
        sid = r['id']; n = int(round(r['dur'] * fps)); last = idx == len(tl) - 1
        out = sd / f'{idx:03d}_{sid}.mp4'
        typ = r.get('type', 'scene')
        cap = pr.build / 'frames' / (sid + '__cap')
        key = _hash({'r': r, 'last': last, 'hold': pr.end_hold, 'W': W, 'H': H, 'fps': fps,
                     'frames_mtime': max([f.stat().st_mtime for f in (pr.build / 'frames' / sid).glob('f*')] or [0]) if typ == 'scene' else 0,
                     'cap_mtime': max([f.stat().st_mtime for f in cap.glob('f*')] or [0])})
        meta = out.with_suffix('.json')
        if not force and out.exists() and meta.exists() and json.loads(meta.read_text()).get('key') == key:
            files.append(out); continue
        tail = f",tpad=stop_mode=clone:stop={int(round(pr.end_hold * fps))}" if last and pr.end_hold > 0 else ''
        if typ == 'scene':
            fr = pr.build / 'frames' / sid
            if not (fr / 'f00000.jpg').exists():
                die(f'frames missing for scene "{sid}" — run: vmd.py render')
            cmd = ['ffmpeg', '-v', 'error', '-y', '-framerate', str(fps), '-i', str(fr / 'f%05d.jpg'),
                   '-vf', f'trim=end_frame={n},setpts=PTS-STARTPTS,scale={W}:{H}{tail}'] + ENC + [str(out)]
        elif typ == 'clip':
            spd = float(r.get('speed', 1.0)); a = float(r.get('in', 0))
            src_d = probe_duration(pr.p(r['src']))
            b = min(float(r.get('out', src_d)), src_d)
            avail, pad = b - a, 0.0
            if r['dur'] * spd > avail + 1.0 / fps:          # the voice asked for more time than the shot has
                if r.get('extend') and src_d - a >= r['dur'] * spd:
                    b = src_d; avail = b - a                    # allowed to play past "out"
                else:
                    slow = max(avail / r['dur'], 0.7 * spd)    # gentle slow motion (max -30%) ...
                    pad = max(0.0, r['dur'] - avail / slow)     # ... then a held last frame
                    log(f'  clip {sid}: stretched to {r["dur"]:.2f}s (speed {slow:.2f}' + (f', hold {pad:.2f}s' if pad > 0.04 else '') + ')'
                        + (' — set "extend": true to use more footage, or shorten the voice' if pad > 0.04 else ''))
                    spd = slow
            vf = f"setpts=PTS/{spd:.5f},fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
            if r.get('grade', 'soft') == 'soft':
                vf += ',eq=contrast=1.04:saturation=0.94'
            if pad > 0:
                vf += f',tpad=stop_mode=clone:stop_duration={pad + 0.2:.3f}'
            vf += f",trim=end_frame={n},setpts=PTS-STARTPTS"
            inputs = ['-ss', f'{a:.3f}', '-t', f'{avail:.3f}', '-i', str(pr.p(r['src']))]
            if (cap / 'f00000.png').exists():
                inputs += _overlay_args(cap, fps)
                fc = f"[0:v]{vf}[b];[b][1:v]overlay=0:0:shortest=0:eof_action=pass{tail}[v]"
                cmd = ['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex', fc, '-map', '[v]', '-frames:v', str(n + (int(round(pr.end_hold * fps)) if last else 0))] + ENC + [str(out)]
            else:
                cmd = ['ffmpeg', '-v', 'error', '-y'] + inputs + ['-vf', vf + tail] + ENC + [str(out)]
        elif typ in ('still', 'freeze'):
            kb = pr.build / 'kb' / sid
            if typ == 'still':
                im = Image.open(pr.p(r['src']))
            else:
                ref = next((x for x in tl if x['id'] == r['of']), None)
                if ref is None:
                    die(f'freeze "{sid}": segment "{r["of"]}" not found')
                ri = tl.index(ref)
                if ri >= idx:
                    die(f'freeze "{sid}" must come after the segment it freezes ("{r["of"]}")')
                src_mp4 = sd / f'{ri:03d}_{ref["id"]}.mp4'
                at = float(r.get('at', ref['dur'] / 2))
                png = pr.build / 'kb' / f'{sid}_src.png'; png.parent.mkdir(parents=True, exist_ok=True)
                run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{at:.3f}', '-i', str(src_mp4), '-frames:v', '1', str(png)])
                im = Image.open(png)
            z = r.get('zoom', [1.0, 1.035] if typ == 'freeze' else [1.08, 1.0])
            mode = r.get('motion', 'breathe' if typ == 'freeze' else 'push')
            _kenburns(im, kb, n, W, H, mode=mode, z=tuple(z), pan=tuple(r.get('pan', (0, 0))), focus=tuple(r.get('focus', (0.5, 0.45))))
            inputs = ['-framerate', str(fps), '-i', str(kb / 'f%05d.jpg')]
            if (cap / 'f00000.png').exists():
                inputs += _overlay_args(cap, fps)
                cmd = ['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex', f'[0:v][1:v]overlay=0:0{tail}[v]', '-map', '[v]'] + ENC + [str(out)]
            else:
                cmd = ['ffmpeg', '-v', 'error', '-y'] + inputs + (['-vf', tail[1:]] if tail else []) + ENC + [str(out)]
        else:
            die(f'unknown segment type "{typ}" in "{sid}"')
        log(f'  segment {sid} ({typ}, {r["dur"]:.2f}s)')
        run(cmd)
        meta.write_text(json.dumps({'key': key}))
        files.append(out)
    lst = pr.build / 'segs.txt'
    lst.write_text(''.join(f"file '{f.resolve()}'\n" for f in files))
    pic = pr.build / 'picture.mp4'
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(pic)])
    log(f'picture -> {pic}')
    return pic
