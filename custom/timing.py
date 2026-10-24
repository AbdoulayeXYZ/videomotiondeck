"""Custom-film timing: map a recorded voice (phrase chunks) onto a longer film by inserting pauses.

Input  : chunks.json  [[start, end, text], ...]  (original voice times, e.g. from `vmd voice` / Whisper)
Config : INS_AFTER = [(phrase_index_or_-1, seconds), ...]  - a pause inserted after that phrase (-1 = before the first)
Output : timing.json {"ins": [[pos, dur]...], "ph": [[mapped_start, mapped_end, text]...], "total": seconds}

Usage  : python3 timing.py chunks.json --after="-1:4.2,7:2.2,21:8.0" --voice-end 127.09 --end 4.0
The film's HTML reads timing.json (P(i)/E(i) = mapped start/end of phrase i) so every cut stays on the voice.
"""
import json, argparse

ap = argparse.ArgumentParser()
ap.add_argument('chunks'); ap.add_argument('--after', default='')
ap.add_argument('--voice-end', type=float, required=True); ap.add_argument('--end', type=float, default=3.0)
ap.add_argument('--out', default='timing.json')
ap.add_argument('--write-voice', nargs=2, metavar=('VOICE_IN', 'VOICE_OUT'), help='also write the voice with the pauses inserted (48 kHz wav)')
a = ap.parse_args()
C = json.load(open(a.chunks))
ins = []
for item in filter(None, a.after.split(',')):
    k, d = item.split(':'); k = int(k); d = float(d)
    pos = 0.0 if k < 0 else (C[k][1] + C[k + 1][0]) / 2 if k + 1 < len(C) else C[k][1] + 0.15
    ins.append((round(pos, 3), d))
M = lambda t: t + sum(d for p, d in ins if p <= t + 1e-9)
ph = [[round(M(s), 3), round(M(e), 3), x] for s, e, x in C]
total = round(M(a.voice_end) + a.end, 3)
json.dump({'ins': ins, 'ph': ph, 'total': total}, open(a.out, 'w'), ensure_ascii=False)
print(f'total {total:.2f}s ({int(total//60)}:{total%60:05.2f}) - {len(ins)} pauses, +{sum(d for _, d in ins):.1f}s')

if a.write_voice:
    import numpy as np, soundfile as sf, subprocess, tempfile
    src, dst = a.write_voice
    tmp = tempfile.mktemp(suffix='.wav'); subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-ar', '48000', '-ac', '2', tmp], check=True)
    v, sr = sf.read(tmp, always_2d=True); parts = []; cur = 0
    for p, d in sorted(ins):
        k = int(round(p * sr)); parts += [v[cur:k], np.zeros((int(round(d * sr)), v.shape[1]))]; cur = k
    parts.append(v[cur:]); out = np.concatenate(parts)
    n = int(round(total * sr)); out = out[:n] if len(out) >= n else np.concatenate([out, np.zeros((n - len(out), v.shape[1]))])
    sf.write(dst, out, sr, subtype='FLOAT'); print('voice ->', dst)
