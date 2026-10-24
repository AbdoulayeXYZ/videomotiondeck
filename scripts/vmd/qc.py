"""Quality control of the final file — the checks a picky jury (or client) would do for you.

duration vs max_duration · black frames · frozen/static stretches ("is it over?") · voice dead air ·
loudness/true-peak · voice masked by music/SFX (1-4 kHz SNR) · ASR intelligibility of the final mix ·
1 fps contact sheets to eyeball every second.  Writes build/qc/report.md."""
import json, re, difflib, unicodedata
from pathlib import Path
import numpy as np
from .common import log, run, SR, probe_duration
import subprocess


def _ff(args):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats'] + args, capture_output=True, text=True)
    return r.stderr


def _nz(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9 ]', '', s)


def black_frames(f):
    e = _ff(['-i', str(f), '-vf', 'blackdetect=d=0.08:pix_th=0.08', '-an', '-f', 'null', '-'])
    return [(float(a), float(b)) for a, b in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', e)]


def frozen(f, min_d=1.4):
    e = _ff(['-i', str(f), '-vf', f'freezedetect=n=0.0015:d={min_d}', '-an', '-f', 'null', '-'])
    st = [float(x) for x in re.findall(r'freeze_start: ([\d.]+)', e)]
    en = [float(x) for x in re.findall(r'freeze_end: ([\d.]+)', e)]
    dur = probe_duration(f)
    return [(a, en[i] if i < len(en) else dur) for i, a in enumerate(st)]


def loudness(f):
    e = _ff(['-i', str(f), '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'])
    s = e[e.rfind('Summary:'):]
    i = re.search(r'I:\s+(-?[\d.]+) LUFS', s); tp = re.search(r'Peak:\s+(-?[\d.]+) dBFS', s)
    return (float(i.group(1)) if i else None), (float(tp.group(1)) if tp else None)


def masking(pr):
    from scipy.signal import butter, sosfilt
    try:
        v = np.load(pr.build / 'bus_voice.npy'); r = np.load(pr.build / 'bus_rest.npy')
    except FileNotFoundError:
        return None, []
    sos = butter(4, [1000, 4000], 'bandpass', fs=SR, output='sos')
    hop = 2400

    def env(x):
        y = sosfilt(sos, x); n = len(y) // hop
        return 10 * np.log10((y[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    ev, er = env(v), env(r)
    if not (ev > -90).any():
        return None, []
    act = ev > (np.percentile(ev[ev > -90], 50) - 6)
    bad = np.where(act & (er > ev - 3))[0]
    pct = 100 * len(bad) / max(1, act.sum())
    spots = []
    if len(bad):
        for g in np.split(bad, np.where(np.diff(bad) > 2)[0] + 1):
            if len(g) >= 3:
                spots.append((round(g[0] * hop / SR, 2), round((g[-1] + 1) * hop / SR, 2), round(float(np.min(ev[g] - er[g])), 1)))
    return round(pct, 1), spots


def dead_air(pr, tl, max_gap=1.8):
    """Gaps in the voice longer than max_gap s, not counting segments marked "voice_free": true."""
    placed = pr.load_json('placed.json')
    if not placed:
        return []
    free = [(r['t0'], r['t1']) for r in tl if r.get('voice_free')]
    gaps = []
    for a, b in zip(placed[:-1], placed[1:]):
        g0, g1 = a['t1'], b['t0']
        covered = sum(max(0.0, min(g1, f1) - max(g0, f0)) for f0, f1 in free)
        if (g1 - g0) - covered > max_gap:
            seg = next((r['id'] for r in tl if r['t0'] <= g0 < r['t1']), '?')
            gaps.append((round(g0, 2), round(g1, 2), seg))
    return gaps


def intelligibility(pr, final):
    """Whisper re-listens to the FINAL MIX in ~6 s windows and compares with what it heard on the clean voice
    (or with the script when no clean transcription exists): measures what the music/SFX take away."""
    from .voice import asr_model
    placed = pr.load_json('placed.json')
    m = asr_model()
    if not placed or m is None:
        return None, []
    try:
        import sherpa_onnx, librosa, soundfile as sf
    except ImportError:
        return None, []
    x, sr = sf.read(pr.build / 'master.wav'); x = x.mean(axis=1) if x.ndim > 1 else x
    x16 = librosa.resample(x, orig_sr=sr, target_sr=16000)
    enc, dec, tok = m
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=str(enc), decoder=str(dec), tokens=str(tok), language=pr.lang, task='transcribe', num_threads=2)
    # windows of consecutive phrases (<= 6 s, split on gaps > 0.8 s)
    wins, cur = [], []
    for p in placed:
        if cur and (p['t0'] - cur[-1]['t1'] > 0.8 or p['t1'] - cur[0]['t0'] > 6.0):
            wins.append(cur); cur = []
        cur.append(p)
    if cur:
        wins.append(cur)
    res = []
    for w in wins:
        ref = ' '.join((p.get('asr') or '') for p in w).strip()
        if not ref:   # no clean transcription: compare with the script lines this window starts
            ref = ' '.join(dict.fromkeys(p['script'] for p in w))
        a, b = w[0]['t0'], w[-1]['t1']
        s = rec.create_stream()
        ch = x16[max(0, int((a - 0.05) * 16000)):int((b + 0.05) * 16000)]
        ch = ch / (np.abs(ch).max() + 1e-9) * 0.5
        s.accept_waveform(16000, np.concatenate([np.zeros(1600), ch, np.zeros(1600)]).astype(np.float32)); rec.decode_stream(s)
        heard = s.result.text.strip()
        res.append((w[0]['line'], a, difflib.SequenceMatcher(None, _nz(ref), _nz(heard)).ratio(), ref, heard, b - a))
    tot = sum(r[5] for r in res) or 1
    mean = sum(r[2] * r[5] for r in res) / tot
    return round(float(mean), 3), [r[:5] for r in res if r[2] < 0.75]


def contact_sheets(f, out):
    for old in out.glob('sheet_*.jpg'):
        old.unlink()
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(f), '-vf', "fps=1,scale=384:-1,drawtext=text='%{pts\\:hms}':x=6:y=6:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=6x5:padding=4:color=0x111111",
         '-q:v', '4', str(out / 'sheet_%02d.jpg')])
    return sorted(out.glob('sheet_*.jpg'))


def qc(pr, final, asr=True):
    final = Path(final)
    out = pr.build / 'qc'; out.mkdir(exist_ok=True)
    tl = pr.timeline()
    R, fails, warns = [], [], []
    dur = probe_duration(final)
    R.append(f'# QC — {final.name}\n')
    R.append(f'- duration: **{dur:.2f}s** ({int(dur // 60)}:{dur % 60:05.2f})' + (f' / max {pr.max_duration}s' if pr.max_duration else ''))
    if pr.max_duration and dur > float(pr.max_duration) + 0.05:
        fails.append(f'too long: {dur:.2f}s > {pr.max_duration}s')
    bl = [b for b in black_frames(final) if b[0] > 0.2 and b[1] < dur - 0.3]
    R.append(f'- black frames: {len(bl)} ' + ' '.join(f'[{a:.2f}-{b:.2f}]' for a, b in bl))
    if bl:
        fails.append(f'black frames at {", ".join(f"{a:.2f}s" for a, _ in bl)} (trim the clip in/out points)')
    fz = [z for z in frozen(final) if z[1] < dur - pr.end_hold - 0.3]
    R.append(f'- static stretches ≥1.4s: {len(fz)} ' + ' '.join(f'[{a:.2f}-{b:.2f}]' for a, b in fz))
    if fz:
        warns.append('static picture at ' + ', '.join(f'{a:.1f}s' for a, _ in fz) + ' (add motion: zoom/breathe, or shorten)')
    da = dead_air(pr, tl)
    R.append(f'- voice dead air >1.8s: {len(da)} ' + ' '.join(f'[{a:.1f}-{b:.1f} in {s}]' for a, b, s in da))
    if da:
        warns.append('voice silent at ' + ', '.join(f'{a:.1f}s ({s})' for a, b, s in da) + ' — intended? mark the segment "voice_free": true, else shorten it')
    I, tp = loudness(final)
    tgt = float(pr.spec.get('mix', {}).get('loudness', -14))
    R.append(f'- loudness: **{I} LUFS** (target {tgt}), true peak {tp} dBTP')
    if I is None or abs(I - tgt) > 1.0:
        fails.append(f'loudness {I} LUFS off target {tgt}')
    if tp is not None and tp > -0.5:
        fails.append(f'true peak {tp} dBTP > -0.5')
    pct, spots = masking(pr)
    if pct is not None:
        R.append(f'- voice masking (1–4 kHz SNR<3 dB): {pct}% of voiced frames' + ''.join(f'\n  - {a:.2f}-{b:.2f}s min SNR {s} dB' for a, b, s in spots[:12]))
        if pct > 4 or len(spots) > 3:
            warns.append(f'voice masked {pct}% — lower the SFX/music at ' + ', '.join(f'{a:.1f}s' for a, b, s in spots[:6]))
    if asr:
        m, low = intelligibility(pr, final)
        if m is not None:
            R.append(f'- intelligibility (Whisper on the final mix vs the clean voice): **{m}**' + ''.join(f'\n  - L{k} @{t:.1f}s sim {s:.2f}: "{tx[:70]}" → heard "{h[:70]}"' for k, t, s, tx, h in low))
            if m < 0.85:
                warns.append(f'intelligibility {m} < 0.85 — check the listed lines (masking, TTS errors, words read wrong)')
        else:
            R.append('- intelligibility: skipped (no Whisper model / no voice)')
    import contextlib, io
    from .lint import lint
    with contextlib.redirect_stdout(io.StringIO()):
        L = lint(pr, tl)
    for w in L:
        if 'placeholder' in w:
            warns.append(w.replace('WARN ', '') + ' (fine for a draft, not for the final film)')
    sheets = contact_sheets(final, out)
    R.append(f'- contact sheets (1 frame/s, open and LOOK at them): ' + ', '.join(str(s) for s in sheets))
    R.append('\n## Verdict\n')
    R += [f'- ❌ {x}' for x in fails] + [f'- ⚠️ {x}' for x in warns]
    if not fails and not warns:
        R.append('- ✅ all automatic checks passed — now watch it once, start to end, with headphones.')
    (out / 'report.md').write_text('\n'.join(R) + '\n', encoding='utf-8')
    for line in R:
        print(line)
    return {'fails': fails, 'warns': warns, 'duration': dur, 'lufs': I, 'true_peak': tp, 'sheets': [str(s) for s in sheets]}
