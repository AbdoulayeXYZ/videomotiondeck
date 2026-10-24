"""Score + sound design + mix for a custom film, reusing the vmd audio engine.

  python3 audio_mix.py scenes.json voice.wav [--end-hold 1.5]
scenes.json : {"scenes": [["S1", 0.0], ["S2", 12.3], ...],           # same start times as film.html SC
               "music":  [{"from":"S1","to":"S1","mood":"night"}, ...],  # moods: night tension tech epic hope resolve reflective question
               "cues":   [[time_s, "whoosh", {"gain":0.4}], ...]}         # absolute times; types in scripts/vmd/sfx.py
voice.wav   : the voice already laid on the film timeline (pauses inserted, see timing.py --write-voice)
Writes build/master.wav (-14 LUFS, voice ducking) and build/bus_*.npy for `qc` masking checks.
"""
import json, sys, argparse, shutil
from pathlib import Path
import numpy as np, soundfile as sf
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vmd.common import Project, SR
from vmd import score, sfx, mix

ap = argparse.ArgumentParser(); ap.add_argument('scenes'); ap.add_argument('voice'); ap.add_argument('--end-hold', type=float, default=1.5)
a = ap.parse_args()
S = json.load(open(a.scenes)); sc = S['scenes']
v, sr = sf.read(a.voice, always_2d=True)
if sr != SR: raise SystemExit(f'voice must be {SR} Hz (ffmpeg -ar {SR})')
total = len(v) / SR
r = lambda x: round(x * 25) / 25
segs = []
for i, (sid, t0) in enumerate(sc):
    t1 = sc[i + 1][1] if i + 1 < len(sc) else total - a.end_hold
    segs.append({'id': sid, 'scene': 'title', 'dur': round(r(t1) - r(t0), 4)})
start = {sid: r(t0) for sid, t0 in sc}
def seg_of(t):
    k = sc[0][0]
    for sid, t0 in sc:
        if t >= r(t0) - 1e-6: k = sid
    return k
cues = []
for t, ty, kw in S.get('cues', []):
    s = seg_of(t); d = {'seg': s, 'at': round(t - start[s], 3), 'type': ty}; d.update(kw or {}); cues.append(d)
proj = {'title': 'custom', 'fps': 25, 'end_hold': a.end_hold, 'language': 'fr', 'segments': segs,
        'music': S['music'], 'sfx': {'auto': False, 'cues': cues}, 'mix': S.get('mix', {'loudness': -14, 'music_lufs': -24})}
json.dump(proj, open('project_audio.json', 'w'), ensure_ascii=False, indent=1)
pr = Project('project_audio.json'); tl = pr.timeline()
pr.build.mkdir(exist_ok=True); shutil.copy(a.voice, pr.build / 'voice_track.wav')
score.compose(pr, tl); sfx.design(pr, tl); mix.mixdown(pr, tl)
