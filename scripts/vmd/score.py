"""Original film score composed from the timeline.

Each "act" (a range of segments) gets a mood. Everything is in D (minor for tension, major for release)
so acts flow into each other. Orchestra is rendered with FluidSynth + a General MIDI SoundFont when available,
otherwise with the built-in numpy instruments. Hybrid synth parts (bass pulse, drums, plucks, drones) are numpy."""
import os, subprocess, shutil
from pathlib import Path
import numpy as np
from .common import log, SR

ROOTPC = {'Dm': (2, (0, 3, 7)), 'D': (2, (0, 4, 7)), 'Bb': (10, (0, 4, 7)), 'F': (5, (0, 4, 7)), 'C': (0, (0, 4, 7)),
          'Gm': (7, (0, 3, 7)), 'G': (7, (0, 4, 7)), 'A': (9, (0, 4, 7)), 'Asus': (9, (0, 5, 7)), 'Bm': (11, (0, 3, 7)),
          'Dadd9': (2, (0, 4, 7, 14))}
GM = {'piano': 0, 'celesta': 8, 'cello': 42, 'trem': 44, 'ostin': 48, 'strings': 49, 'choir': 52, 'timp': 47, 'brass': 60, 'pad': 89}
SOUNDFONTS = ['/usr/share/sounds/sf2/FluidR3_GM.sf2', '/usr/share/soundfonts/FluidR3_GM.sf2',
              '/usr/share/sounds/sf2/default-GM.sf2', '/usr/share/soundfonts/default.sf2', '/opt/homebrew/share/soundfonts/default.sf2']


def chord(name, octave=4, spread=False):
    r, iv = ROOTPC[name]; base = 12 * (octave + 1) + r
    ns = [base + i for i in iv]
    return [base - 12] + ns + [base + 12] if spread else ns


class Score:
    def __init__(self, seed=3):
        self.notes = {k: [] for k in GM}; self.ramps = {k: [] for k in GM}
        self.rng = np.random.default_rng(seed)

    def n(self, inst, t, d, p, v):
        if d > 0.02:
            self.notes[inst].append((float(t), float(d), int(p), int(np.clip(v, 1, 127))))

    def ramp(self, inst, t0, t1, v0, v1):
        self.ramps[inst].append((float(t0), float(t1), float(v0), float(v1)))

    def expr(self, inst, N):
        """expression curve 0..1 per sample (default 0.85 where no ramp is defined)."""
        e = np.full(N, 0.85)
        for t0, t1, v0, v1 in sorted(self.ramps[inst]):
            a, b = int(t0 * SR), max(int(t1 * SR), int(t0 * SR) + 1)
            a2, b2 = max(0, a), min(N, b)
            if b2 > a2:
                e[a2:b2] = np.linspace(v0, v1, b - a)[a2 - a:b2 - a] / 127.0
            # hold the end value until the next ramp
            if b < N:
                e[b:] = v1 / 127.0
        return e


# ------------------------------------------------------------------ moods (write notes into the score)
def mood_night(S, a, b, o):
    d = b - a
    S.n('cello', a + 0.6, d - 0.8, 38, 70); S.n('cello', a + 0.6, d - 0.8, 50, 50)
    S.ramp('cello', a, a + 0.5 * d, 0, 70); S.ramp('cello', a + 0.5 * d, b - 0.2, 70, 100); S.ramp('cello', b - 0.2, b, 100, 0)
    t0 = a + 0.6 * d
    S.n('trem', t0, b - t0 - 0.1, 69, 60); S.n('trem', t0, b - t0 - 0.1, 74, 55)
    S.ramp('trem', t0, b - 0.15, 10, 95); S.ramp('trem', b - 0.15, b, 95, 0)


def mood_reflective(S, a, b, o):
    E8 = 60 / 72 / 2; prog = ['Dm', 'Dm', 'Bb', 'Bb', 'F', 'F', 'C', 'C'] * 4; pat = [0, 2, 1, 3, 2, 1, 2, 3]
    bt = a + 0.25; k = 0
    while bt < b - 0.3:
        c = prog[k % len(prog)]; ns = chord(c, 4); arp = [ns[0], ns[1], ns[2], ns[0] + 12]
        end = min(b - 0.1, bt + 8 * E8)
        for i, ix in enumerate(pat):
            tt = bt + i * E8
            if tt > b - 0.25: break
            S.n('piano', tt + S.rng.normal(0, 0.006), E8 * 1.6, arp[ix], 42 + 8 * (i % 4 == 0) + S.rng.integers(-4, 4) + min(k, 8))
        S.n('piano', bt, end - bt, ns[0] - 24, 48 + min(k, 8))
        for p in chord(c, 3) + [chord(c, 4)[1]]:
            S.n('strings', bt, end - bt + 0.05, p, 66)
        bt += 8 * E8; k += 1
    S.ramp('strings', a, a + 1.0, 0, 0); S.ramp('strings', a + 1.0, a + 6, 0, 60); S.ramp('strings', a + 6, b - 0.3, 60, 92); S.ramp('strings', b - 0.25, b, 80, 0)


def mood_question(S, a, b, o):
    q1 = b - 0.06
    for p, v in ((57, 70), (64, 66), (81, 50)):
        S.n('trem', a + 0.05, q1 - a, p, v)
    S.ramp('trem', a, q1 - 1.0, 20, 55); S.ramp('trem', q1 - 1.0, q1, 55, 105); S.ramp('trem', q1, b, 105, 0)


def mood_tension(S, a, b, o):
    d = b - a; sw = a + d * 0.78
    for p in chord('Dm', 3) + [chord('Dm', 4)[1]]: S.n('pad', a + 0.08, sw - a - 0.05, p, 70)
    for p in chord('Asus', 3) + [69]: S.n('pad', sw, (b - sw) * 0.5, p, 72)
    for p in chord('A', 3) + [73]: S.n('pad', sw + (b - sw) * 0.5, (b - sw) * 0.5 - 0.02, p, 74)
    S.ramp('pad', a, a + 1.5, 20, 80); S.ramp('pad', a + 1.5, b - 0.1, 80, 105); S.ramp('pad', b - 0.1, b, 105, 0)


def mood_hope(S, a, b, o):
    E8 = 60 / 90 / 2; prog = ['D', 'A', 'Bm', 'G'] * 6; bt = a; k = 0
    while bt < b - 0.4:
        c = prog[k % len(prog)]; end = min(b - 0.12, bt + 8 * E8)
        if end - bt < 1.2 and k > 0: c = 'A'
        ns = chord(c, 4); arp = [ns[0], ns[1], ns[2], ns[0] + 12, ns[2], ns[1] + 12 if k > 2 else ns[1], ns[2], ns[0] + 12]
        i = 0
        while bt + i * E8 < end - 0.05:
            S.n('piano', bt + i * E8 + S.rng.normal(0, 0.005), E8 * 1.5, arp[i % 8], 52 + 10 * (i % 8 == 0) + S.rng.integers(-4, 4) + min(k, 6)); i += 1
        S.n('piano', bt, end - bt, ns[0] - 24, 60)
        for p in chord(c, 3) + [chord(c, 4)[2]]: S.n('strings', bt, end - bt + 0.05, p, 70)
        if k >= 1:
            for p in chord(c, 4): S.n('choir', bt, end - bt + 0.05, p, 60)
        bt += 8 * E8; k += 1
    S.ramp('strings', a - 0.01, a, 0, 60); S.ramp('strings', a, a + 1.4, 60, 85); S.ramp('strings', b - 3.0, b - 0.5, 85, 105); S.ramp('strings', b - 0.5, b, 105, 0)
    S.ramp('choir', a, a + 2.6, 0, 0); S.ramp('choir', a + 2.6, a + 5, 0, 70); S.ramp('choir', b - 1.0, b, 75, 0)


def mood_epic(S, a, b, o):
    B = 0.6; BAR = 2.4; prog = ['Dm', 'Bb', 'F', 'C', 'Dm', 'Bb', 'F', 'Gm', 'Bb', 'F', 'Gm', 'A', 'Bb', 'C', 'Dm', 'Bb', 'C']
    cut = b - BAR; t = a; k = 0; tl = []
    while t < cut - 0.05:
        e = min(t + BAR, cut); tl.append((t, e, prog[k % len(prog)])); t = e; k += 1
    tl.append((cut, b, 'A'))
    bstart = a + 0.4 * (b - a)
    for x0, x1, c in tl:
        ns = chord(c, 3); x = x0; j = 0
        while x < x1 - 0.01:
            p = ns[0] + (12 if j % 2 else 0) if j % 4 < 2 else ns[[1, 2][j % 2]]
            S.n('ostin', x, B / 2 * 0.9, p, 70 + 10 * (j % 4 == 0)); x += B / 2; j += 1
        for p in chord(c, 3, spread=True): S.n('strings', x0, x1 - x0 + 0.05, p, 75)
        for p in chord(c, 4): S.n('choir', x0, x1 - x0 + 0.05, p, 70)
        if x0 >= bstart:
            for p in chord(c, 3)[:2] + [chord(c, 2)[0]]: S.n('brass', x0, x1 - x0 + 0.05, p, 80)
    S.ramp('ostin', a, a + 3.5, 30, 70); S.ramp('ostin', a + 3.5, b - 0.3, 70, 110); S.ramp('ostin', b - 0.3, b, 110, 0)
    S.ramp('strings', a - 0.01, a, 0, 50); S.ramp('strings', a, a + 8, 50, 80); S.ramp('strings', a + 8, b, 80, 112)
    S.ramp('choir', a, bstart, 0, 50); S.ramp('choir', bstart, b, 50, 100)
    S.ramp('brass', a, bstart, 0, 30); S.ramp('brass', bstart, b - 0.1, 30, 100); S.ramp('brass', b - 0.1, b, 100, 100)
    x = b - 2.6
    while x < b - 0.05:
        k = (x - (b - 2.6)) / 2.6; S.n('timp', x, 0.06, 38, 30 + 90 * k); x += 0.055
    S.n('timp', a, 1.0, 38, 110); S.n('timp', a + 0.003, 1.0, 26, 100)


def mood_resolve(S, a, b, o):
    """Major-key landing (logos, team, thanks). o['final'] = absolute time of the final chord swell."""
    fin = o.get('final', b - 1.2)
    S.n('timp', a, 1.0, 38, 115); S.n('timp', a + 0.003, 1.0, 26, 105)
    for p in chord('D', 3, spread=True): S.n('strings', a + 0.05, max(0.3, fin - a - 0.1), p, 62)
    for p in chord('Dadd9', 4):
        S.n('choir', a + 0.05, b - a - 0.2, p, 60)
        if fin < b - 0.3: S.n('strings', fin, b - fin - 0.1, p, 72)
    E8 = 60 / 84 / 2; t = a + 0.6; k = 0
    for c in ['D', 'A', 'Bm', 'G', 'D', 'A', 'Bm', 'G', 'D', 'A']:
        ns = chord(c, 4); arp = [ns[0], ns[1], ns[2], ns[0] + 12, ns[2], ns[1], ns[2], ns[0] + 12]
        for i in range(8):
            tt = t + i * E8
            if tt < fin - 0.4: S.n('piano', tt + S.rng.normal(0, 0.005), E8 * 1.6, arp[i], 44 + 8 * (i == 0) + S.rng.integers(-3, 3))
        if t < fin - 0.5: S.n('piano', t, min(8 * E8, fin - 0.4 - t), ns[0] - 24, 50)
        t += 8 * E8
    for p in chord('D', 2): S.n('brass', fin, b - fin - 0.1, p, 90)
    S.ramp('strings', a, fin - 0.05, 60, 90); S.ramp('strings', fin, b - 0.05, 98, 0)
    S.ramp('choir', a, fin - 0.05, 30, 90); S.ramp('choir', fin, b - 0.05, 95, 0)
    S.ramp('brass', fin - 0.1, fin, 100, 100); S.ramp('brass', fin + 0.05, b - 0.05, 100, 0)
    x = fin - 1.3
    while x < fin - 0.02:
        k = (x - (fin - 1.3)) / 1.3; S.n('timp', x, 0.06, 38, 25 + 75 * k); x += 0.055
    S.n('timp', fin, 1.0, 38, 115); S.n('timp', fin + 0.003, 1.0, 26, 105)
    for i, p in enumerate([74, 78, 81, 86]): S.n('celesta', a + 0.05 + i * 0.08, 1.4, p, 58)


MOODS = {'night': mood_night, 'reflective': mood_reflective, 'question': mood_question, 'tension': mood_tension,
         'hope': mood_hope, 'tech': None, 'epic': mood_epic, 'resolve': mood_resolve, 'silence': None}


# ------------------------------------------------------------------ numpy synth parts
def _put(buf, at, s, g=1.0):
    i = int(round(at * SR))
    if i >= buf.shape[1] or i + s.shape[1] <= 0: return
    if i < 0: s = s[:, -i:]; i = 0
    n = min(s.shape[1], buf.shape[1] - i); buf[:, i:i + n] += s[:, :n] * g


def tech_parts(acts_tech, N):
    from . import sfxlib as X
    mtof = lambda m: 440 * 2 ** ((m - 69) / 12)
    ROOT = {'Dm': 38, 'D': 38, 'Bb': 34, 'F': 41, 'C': 36, 'A': 33, 'Gm': 43}
    TONES = {'Dm': (62, 65, 69), 'Bb': (58, 62, 65), 'F': (65, 69, 72), 'C': (60, 64, 67), 'A': (61, 64, 69), 'Gm': (67, 70, 74)}

    def bass_note(m, d, cutoff=900, gain=0.5):
        t = X.t_(d); f = mtof(m)
        y = sum((2 * ((f * k * (1 + det) * t + ph) % 1) - 1) for k, det, ph in ((1, 0, 0), (1, 0.004, .3), (0.5, 0, .1)))
        y = y / 3 + 0.6 * np.sin(2 * np.pi * f * 0.5 * t)
        y = X.svf(y, 80 + cutoff * np.exp(-t * 9), 0.45, 0)
        y *= np.minimum(1, t / 0.004) * np.minimum(1, (d - t) / 0.01)
        return X.st(np.tanh(y * 1.8) * gain)

    def kick(g=0.7):
        t = X.t_(0.45); f = 45 + 110 * np.exp(-t * 35)
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) + 0.25 * X.hp(X.noise(0.45), 2500) * np.exp(-t * 200)
        return X.st(np.tanh(y * 1.5) * g)

    def hat(g=0.1, op=False):
        d = 0.25 if op else 0.06; t = X.t_(d)
        return X.st(X.hp(X.noise(d), 7000, 4) * np.exp(-t * (14 if op else 70)) * g, width=0.3)

    def snare(g=0.16):
        t = X.t_(0.35)
        y = X.bp(X.noise(0.35), 900, 7000) * np.exp(-t * 18) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25)
        return X.verb(X.st(y * g), 0.5, 0.3, 0.4, 1, 0.5)

    def pluck(m, g=0.12, pan=0.0):
        t = X.t_(0.5); f = mtof(m)
        y = (2 * ((f * t) % 1) - 1) * 0.6 + np.sin(2 * np.pi * f * t)
        return X.st(X.svf(y, 300 + 4000 * np.exp(-t * 18), 0.4, 0) * np.exp(-t * 6) * g, pan)

    bass = np.zeros((2, N)); drums = np.zeros((2, N)); plk = np.zeros((2, N)); pump = np.ones(N)
    E, BAR = 0.3, 2.4
    pads = []
    for (a, b, drops) in acts_tech:
        prog = ['Dm', 'Bb', 'F', 'C', 'Dm', 'C', 'Bb', 'C']
        d = b - a; t = a; k = 0
        while t < b - 0.05:
            e = min(t + BAR, b); c = prog[k % len(prog)] if e < b - 0.01 or k == 0 else 'A'
            pads.append((t, e, c))
            u = (t - a) / max(d, 1e-6)
            sec = 'intro' if u < 0.18 else ('groove' if u < 0.45 else ('full' if u < 0.7 else 'pluck'))
            nE = int(round((e - t) / E))
            for i in range(nE):
                tt = t + i * E
                if any(x0 - 0.05 <= tt < x1 for x0, x1 in drops):
                    continue
                if sec == 'intro':
                    _put(bass, tt, bass_note(ROOT[c] + (12 if i % 4 == 3 else 0), E * 0.9, 250 + 900 * u / 0.18, 0.42))
                else:
                    _put(bass, tt, bass_note(ROOT[c] + (12 if i % 8 in (3, 7) else 0), E * 0.85, 1100, 0.45))
                if sec in ('full', 'pluck') and i % 2 == 0:
                    _put(drums, tt, kick(0.7)); k0 = int(tt * SR); L = int(0.22 * SR)
                    pump[k0:k0 + L] = np.minimum(pump[k0:k0 + L], 0.45 + 0.55 * (np.arange(len(pump[k0:k0 + L])) / L) ** 0.7)
                if sec != 'intro' and i % 2 == 1: _put(drums, tt, hat(0.09))
                if sec in ('full', 'pluck') and i % 8 == 6: _put(drums, tt, hat(0.07, True))
                if sec in ('full', 'pluck') and i % 4 == 2: _put(drums, tt, snare(0.16))
                if sec == 'pluck':
                    tones = TONES.get(c, TONES['Dm'])
                    for j in range(2):
                        m = tones[(2 * i + j) % 3] + (12 if (2 * i + j) % 6 >= 3 else 0)
                        _put(plk, tt + j * 0.15, pluck(m, 0.12, -0.35 if j else 0.35))
            t = e; k += 1
        x = b - 1.2
        while x < b - 0.02:
            q = (x - (b - 1.2)) / 1.2; _put(drums, x, snare(0.06 + 0.16 * q)); x += 0.15 if q < 0.5 else 0.075
    bass *= pump; plk *= (0.6 + 0.4 * pump)
    if np.abs(plk).max() > 0:
        plk = X.verb(plk, 0.5, 0.3, 0.4, 1, 0)[:, :N]
    return bass, drums, plk, pads


def drones(acts, N):
    from . import sfxlib as X
    dr = np.zeros((2, N))
    for mood, a, b in acts:
        if mood in ('night', 'reflective', 'tension', 'epic', 'question'):
            g = {'night': 0.35, 'reflective': 0.18, 'tension': 0.22, 'epic': 0.14, 'question': 0.2}[mood]
            br = {'night': 260, 'reflective': 300, 'tension': 340, 'epic': 280, 'question': 300}[mood]
            _put(dr, a, X.fade(X.low_drone(max(0.3, b - a), 36.71, g, br), min(2.0, (b - a) / 3), 0.08))
    return dr


# ------------------------------------------------------------------ renderers
def find_soundfont():
    env = os.environ.get('VMD_SOUNDFONT')
    from .common import CACHE
    for p in ([env] if env else []) + SOUNDFONTS + [str(CACHE / 'FluidR3_GM.sf2')]:
        if p and Path(p).exists() and Path(p).stat().st_size > 1_000_000:
            return p
    return None


def render_fluidsynth(S, N, outdir, sf2):
    import mido, soundfile as sf
    TPS = 960
    stems = {}
    for ch, inst in enumerate(GM):
        if not S.notes[inst]:
            continue
        chn = ch if ch < 9 else ch + 1
        mid = mido.MidiFile(ticks_per_beat=480); trk = mido.MidiTrack(); mid.tracks.append(trk)
        trk.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
        trk.append(mido.Message('program_change', program=GM[inst], channel=chn, time=0))
        for cc, v in ((7, 110), (91, 0), (93, 0), (11, 127)):
            trk.append(mido.Message('control_change', control=cc, value=v, channel=chn, time=0))
        ev = []
        for t, d, p, v in S.notes[inst]:
            ev.append((t, 1, 'on', p, v)); ev.append((t + d, 0, 'off', p, 0))
        ev.sort(key=lambda e: (e[0], e[1]))
        last = 0
        for t, _, kind, p, v in ev:
            tick = int(round(max(0, t) * TPS)); dt = tick - last; last = tick
            trk.append(mido.Message('note_on' if kind == 'on' else 'note_off', note=p, velocity=v, channel=chn, time=dt))
        trk.append(mido.MetaMessage('end_of_track', time=int(2 * TPS)))
        mp = outdir / f'{inst}.mid'; wp = outdir / f'{inst}.wav'
        mid.save(mp)
        subprocess.run(['fluidsynth', '-ni', '-q', '-R', '0', '-C', '0', '-g', '0.6', '-r', str(SR), '-F', str(wp), sf2, str(mp)], check=True, capture_output=True)
        x, _ = sf.read(wp, always_2d=True); x = x.T
        y = np.zeros((2, N)); n = min(N, x.shape[1]); y[:, :n] = x[:, :n]
        stems[inst] = y * S.expr(inst, N)
    return stems


def render_numpy(S, N):
    """Fallback orchestra: additive/subtractive synthesis (no SoundFont needed)."""
    from . import sfxlib as X
    mtof = lambda m: 440 * 2 ** ((m - 69) / 12)
    stems = {}
    for inst, notes in S.notes.items():
        if not notes: continue
        y = np.zeros(N)
        for t, d, p, v in notes:
            f = mtof(p); a = v / 127.0
            if inst in ('piano', 'celesta'):
                L = min(d + 1.2, 4.0); tt = X.t_(L)
                dec = 2.2 if inst == 'piano' else 3.5
                s = sum(np.sin(2 * np.pi * f * k * tt) * (0.6 ** (k - 1)) for k in (1, 2, 3, 4)) * np.exp(-tt * dec * (1 + p / 120))
                s *= np.minimum(1, tt / 0.004)
            elif inst == 'timp':
                L = 1.2; tt = X.t_(L); ff = f * (1 + 0.15 * np.exp(-tt * 20))
                s = np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-tt * 3.5) + 0.2 * X.lp(X.noise(L), 300) * np.exp(-tt * 30)
            else:
                L = d + (0.6 if inst != 'ostin' else 0.15); tt = X.t_(L)
                vib = 1 + 0.003 * np.sin(2 * np.pi * 5.2 * tt)
                saw = sum((2 * ((f * dt * vib * tt + ph) % 1) - 1) for dt, ph in ((1, 0), (1.004, .3), (0.996, .7))) / 3
                cut = {'strings': 2200, 'trem': 2600, 'cello': 1400, 'pad': 1600, 'choir': 1800, 'brass': 2400, 'ostin': 2800}.get(inst, 2000)
                s = X.lp(saw, cut)
                att = {'strings': 0.25, 'trem': 0.08, 'cello': 0.3, 'pad': 0.6, 'choir': 0.35, 'brass': 0.08, 'ostin': 0.01}.get(inst, 0.2)
                envl = np.minimum(1, tt / att) * np.where(tt < d, 1.0, np.exp(-(tt - d) * 8))
                if inst == 'trem': envl *= 0.7 + 0.3 * np.sin(2 * np.pi * 12 * tt)
                s *= envl
            i = int(t * SR); n = min(len(s), N - i)
            if n > 0: y[i:i + n] += s[:n] * a * 0.18
        stems[inst] = np.stack([y, np.roll(y, 240)]) * S.expr(inst, N)
    return stems


# ------------------------------------------------------------------ main entry
def compose(pr, tl):
    N = int(pr.total(tl) * SR) + SR
    idx = pr.seg_index(tl)
    acts = []
    for k, a in enumerate(pr.spec.get('music', [])):
        if a['from'] not in idx or a['to'] not in idx:
            raise SystemExit(f"[vmd] ERROR: music act {k + 1} uses unknown segment ids {a['from']}/{a['to']}")
        t0 = idx[a['from']]['t0']; t1 = idx[a['to']]['t1']
        if a is pr.spec['music'][-1] or a['to'] == tl[-1]['id']:
            t1 += pr.end_hold
        acts.append((a['mood'], t0, t1, a))
    if not acts:
        log('no music acts defined -> silence (add "music": [...] to project.json)')
    S = Score()
    tech = []
    for mood, a, b, cfg in acts:
        if mood not in MOODS:
            raise SystemExit(f"[vmd] ERROR: unknown mood '{mood}' (use: {', '.join(MOODS)})")
        o = dict(cfg)
        if 'final_seg' in cfg and cfg['final_seg'] in idx:
            o['final'] = idx[cfg['final_seg']]['t0'] + float(cfg.get('final_at', 0.3))
        if mood == 'tech':
            drops = [(idx[s]['t0'], idx[s]['t1']) for s in cfg.get('drops', []) if s in idx]
            tech.append((a, b, drops))
        elif MOODS[mood]:
            MOODS[mood](S, a, b, o)
    bass, drums, plk, pads = tech_parts(tech, N) if tech else (np.zeros((2, N)),) * 3 + ([],)
    for t0, t1, c in pads:
        for p in chord(c, 3) + [chord(c, 4)[1]]:
            S.n('pad', t0, t1 - t0 + 0.06, p, 62)
    for (a, b, drops) in tech:
        S.ramp('pad', a, a + 3, 30, 80); S.ramp('pad', b - 0.2, b, 80, 0)
        for x0, x1 in drops:
            S.ramp('pad', x0 - 0.15, x0, 80, 0); S.ramp('pad', x1, x1 + 1.5, 0, 80)
    out = pr.build / 'music'; out.mkdir(exist_ok=True)
    sf2 = find_soundfont()
    if sf2 and shutil.which('fluidsynth'):
        log(f'orchestra: FluidSynth + {Path(sf2).name}')
        stems = render_fluidsynth(S, N, out, sf2)
    else:
        log('orchestra: built-in synth (install fluidsynth + fluid-soundfont-gm for a richer sound)')
        stems = render_numpy(S, N)
    G = dict(piano=1.0, strings=0.85, cello=0.9, trem=0.55, choir=0.45, brass=0.5, timp=0.75, celesta=0.45, ostin=0.6, pad=0.42)
    orch = sum((stems[k] * G[k] for k in stems), np.zeros((2, N)))
    from pedalboard import Pedalboard, Reverb, HighpassFilter
    orch = Pedalboard([HighpassFilter(35), Reverb(room_size=0.82, damping=0.45, wet_level=0.28, dry_level=0.85, width=1.0)])(orch.astype(np.float32), SR)[:, :N]
    syn = bass * 0.85 + drums * 0.75 + plk * 0.8 + drones([(m, a, b) for m, a, b, _ in acts], N)
    music = orch + syn
    # silence acts mute everything inside them
    for mood, a, b, _ in acts:
        if mood == 'silence':
            music[:, int(a * SR):int(b * SR)] = 0
    gains = np.zeros(N)
    for mood, a, b, cfg in acts:
        gdb = float(cfg.get('gain_db', 3.0 if mood in ('reflective', 'hope') else 0.0))
        gains[int(a * SR):int(b * SR)] = gdb
    np.save(out / 'music.npy', music.astype(np.float32)); np.save(out / 'music_gain_db.npy', gains.astype(np.float32))
    log(f'music -> {out / "music.npy"} ({len(acts)} acts)')
    return music
