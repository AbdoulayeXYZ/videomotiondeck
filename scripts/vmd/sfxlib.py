"""videomotiondeck — procedural sound-design library (48 kHz stereo arrays, shape (2, n)). By AbdoulayeXYZ."""
import numpy as np
from numba import njit
from scipy.signal import butter, sosfilt
from pedalboard import Pedalboard, Reverb, Delay, Distortion, Chorus, HighpassFilter, LowpassFilter, Compressor, Gain

SR = 48000
rng = np.random.default_rng(7)


def t_(d):
    return np.arange(int(d * SR)) / SR


def noise(d, color='white'):
    n = int(d * SR)
    w = rng.standard_normal(n)
    if color == 'white':
        return w
    if color == 'pink':
        f = np.fft.rfft(w)
        k = np.arange(len(f)); k[0] = 1
        return np.fft.irfft(f / np.sqrt(k), n) * 12
    if color == 'brown':
        b = np.cumsum(w); b -= np.linspace(b[0], b[-1], n)
        return b / (np.abs(b).max() + 1e-9)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'lowpass', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'highpass', fs=SR, output='sos'), x)


@njit(cache=False)
def svf(x, fc, q, mode):
    """Time-varying state-variable filter. fc array (Hz). mode 0=lp 1=bp 2=hp."""
    y = np.zeros_like(x); low = 0.0; band = 0.0
    for i in range(len(x)):
        f = 2.0 * np.sin(np.pi * min(fc[i], 18000.0) / (2.0 * 48000.0))
        for _ in range(2):  # 2x oversample for stability
            high = x[i] - low - q * band
            band += f * high
            low += f * band
        if mode == 0:
            y[i] = low
        elif mode == 1:
            y[i] = band
        else:
            y[i] = high
    return y


def env(n, a, d, curve=3.0):
    """attack seconds, then exponential-ish decay over remaining."""
    e = np.ones(n)
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na) ** 1.5
    rest = n - na
    if rest > 0:
        e[na:] = np.exp(-curve * np.linspace(0, 1, rest) * (rest / SR) / max(d, 1e-3))
    return e


def fade(x, fi=0.005, fo=0.02):
    x = x.copy(); n = x.shape[-1]
    a = int(fi * SR); b = int(fo * SR)
    if a: x[..., :a] *= np.linspace(0, 1, a)
    if b: x[..., -b:] *= np.linspace(1, 0, b)
    return x


def st(x, pan=0.0, width=0.0):
    """mono -> stereo with constant-power pan (-1..1) and optional Haas width."""
    th = (pan + 1) * np.pi / 4
    L = x * np.cos(th); R = x * np.sin(th)
    if width > 0:
        d = int(width * 0.012 * SR)
        R = np.concatenate([np.zeros(d), R[:-d]]) if d else R
    return np.stack([L, R])


def pan_sweep(x, p0, p1):
    p = np.linspace(p0, p1, len(x)); th = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(th), x * np.sin(th)])


def norm(x, peak=0.9):
    return x * (peak / (np.abs(x).max() + 1e-9))


def fx(x, *plugins):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 1:
        x = x[None, :]
    return Pedalboard(list(plugins))(x, SR)


def verb(x, room=0.6, wet=0.35, damp=0.5, width=1.0, tail=1.5):
    if x.ndim == 1:
        x = st(x)
    x = np.concatenate([x, np.zeros((2, int(tail * SR)))], axis=1)
    w = fx(x, Reverb(room_size=room, damping=damp, wet_level=1.0, dry_level=0.0, width=width))
    return x * (1 - wet * 0.5) + w * wet


# ---------------------------------------------------------------- elements
def sub_boom(d=2.5, f0=62, f1=28, gain=1.0):
    t = t_(d)
    f = f1 + (f0 - f1) * np.exp(-t * 6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * env(len(t), 0.004, d * 0.55, 3)
    y = np.tanh(y * 1.6) / np.tanh(1.6)
    return st(y * gain)


def transient(d=0.25, lo=900, hi=9000, gain=0.5):
    n = noise(d)
    y = bp(n, lo, hi) * env(len(n), 0.001, 0.05, 6)
    return st(y * gain, width=0.5)


def braam(d=3.0, root=36.71, gain=0.6):
    """cinematic low brass-like hit (D1 default)"""
    t = t_(d); y = np.zeros(len(t))
    for k, (m, a) in enumerate([(1, 1), (2, .7), (3, .45), (1.5, .35), (4, .2)]):
        for det in (-0.25, 0.0, 0.31):
            ph = 2 * np.pi * root * m * (1 + det / 100 * 1.5) * t + rng.uniform(0, 6)
            y += a * (2 * ((ph / (2 * np.pi)) % 1) - 1)
    fc = 180 + 1800 * np.exp(-t * 2.5)
    y = svf(y / 6, fc, 0.5, 0)
    y = np.tanh(y * 2.5) * env(len(t), 0.02, d * 0.5, 2.8)
    s = np.stack([y, np.roll(y, 220)])
    return s * gain


def whoosh(d=0.9, f0=300, f1=4000, peak=0.6, pan0=-0.6, pan1=0.6, gain=0.5, q=0.7):
    t = t_(d); n = noise(d, 'pink')
    k = (t / d)
    fc = f0 * (f1 / f0) ** np.clip(k / peak, 0, 1) if f1 > f0 else f0 * (f1 / f0) ** k
    y = svf(n, fc, q, 1)
    e = np.where(k < peak, (k / peak) ** 2.2, np.exp(-(k - peak) / (1 - peak) * 4))
    y = y * e
    return pan_sweep(norm(y, 1) * gain, pan0, pan1)


def swoosh_fast(d=0.45, gain=0.4, pan0=-0.8, pan1=0.8, f=2500):
    return whoosh(d, f * 0.25, f * 2, 0.55, pan0, pan1, gain, 0.9)


def riser(d=4.0, f0=200, f1=3000, gain=0.5, tonal=True):
    t = t_(d); k = t / d
    n = noise(d, 'pink')
    fc = f0 * (f1 / f0) ** (k ** 1.6)
    y = svf(n, fc, 0.35, 1) * (k ** 2.5)
    y = norm(y, 1)
    if tonal:
        tone = np.zeros(len(t))
        for m in (1, 1.5, 2.0):
            fr = 110 * m * 2 ** (k ** 2 * 2.0)
            tone += np.sin(2 * np.pi * np.cumsum(fr) / SR)
        y += 0.35 * tone * (k ** 3)
    s = np.stack([y, np.roll(y, 300)])
    return fade(s, 0.05, 0.004) * gain


def reverse_swell(d=2.0, gain=0.5, bright=6000):
    """reverse cymbal: exponential rise, filtered noise, ends abruptly."""
    t = t_(d); k = t / d
    n = noise(d)
    y = svf(n, 800 + bright * k ** 2, 0.6, 2 if bright > 3000 else 1)
    y *= k ** 4
    s = np.stack([y, np.roll(y, 400)])
    return fade(norm(s, 1), 0.01, 0.003) * gain


def shimmer(d=3.0, notes=(74, 81, 86, 90), gain=0.25, spread=0.07):
    """bell/crystal arpeggio (MIDI notes)."""
    y = np.zeros((2, int(d * SR)))
    for i, m in enumerate(notes):
        f = 440 * 2 ** ((m - 69) / 12); off = int(i * spread * SR)
        tt = t_(d - i * spread)
        s = (np.sin(2 * np.pi * f * tt + 1.4 * np.sin(2 * np.pi * f * 3.5 * tt) * np.exp(-tt * 3))
             * np.exp(-tt * 2.2))
        y[:, off:off + len(s)] += st(s, pan=(-0.5 + i / max(1, len(notes) - 1)))
    return verb(y * gain, 0.85, 0.5, 0.3, 1.0, 2.0)


def tick(f=3200, d=0.03, gain=0.25, pan=0.0):
    t = t_(d)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 180) + 0.5 * hp(noise(d), 4000) * np.exp(-t * 400)
    return st(y * gain, pan)


def blip(f=1400, d=0.12, gain=0.25, pan=0.0, up=1.0):
    t = t_(d)
    fr = f * (1 + (up - 1) * np.clip(t / 0.04, 0, 1))
    y = np.sin(2 * np.pi * np.cumsum(fr) / SR) * env(len(t), 0.002, 0.05, 4)
    y += 0.3 * np.sin(2 * np.pi * np.cumsum(fr * 2) / SR) * env(len(t), 0.001, 0.02, 4)
    return st(y * gain, pan)


def ui_pop(f=900, gain=0.3, pan=0.0):
    t = t_(0.09)
    fr = f * (0.6 + 0.4 * np.clip(t / 0.015, 0, 1))
    y = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 45)
    return st(y * gain, pan)


def notif(gain=0.35, base=1318.5):
    """two-tone notification chime (E6 -> B6)"""
    out = np.zeros(int(1.2 * SR))
    for i, f in enumerate((base, base * 1.498)):
        t = t_(1.0)
        s = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * 6)
        o = int(i * 0.11 * SR); out[o:o + len(s)] += s
    return verb(st(out * gain, 0.2), 0.4, 0.25, 0.4, 1, 0.6)


def alert_tone(n=3, f=2100, on=0.13, off=0.07, gain=0.35):
    """dashcam alarm beeps (square-ish)."""
    seg = []
    t = t_(on)
    sq = np.tanh(6 * np.sin(2 * np.pi * f * t)) * 0.6 + 0.4 * np.sin(2 * np.pi * f * 2 * t)
    sq *= np.minimum(1, np.minimum(t / 0.004, (on - t) / 0.006))
    for i in range(n):
        seg += [sq, np.zeros(int(off * SR))]
    y = lp(np.concatenate(seg), 7000)
    return st(y * gain)


def chime_alert(gain=0.4):
    """attention chime used in-cab: three descending FM bells"""
    out = np.zeros(int(1.8 * SR))
    for i, m in enumerate((88, 84, 88)):
        f = 440 * 2 ** ((m - 69) / 12); t = t_(1.2)
        s = np.sin(2 * np.pi * f * t + 2 * np.sin(2 * np.pi * f * 1.41 * t) * np.exp(-t * 8)) * np.exp(-t * 5)
        o = int(i * 0.18 * SR); out[o:o + len(s)] += s
    return verb(st(out * gain), 0.3, 0.2, 0.5, 1, 0.5)


def heartbeat(gain=0.6):
    out = np.zeros(int(0.9 * SR))
    for o, a in ((0.0, 1.0), (0.24, 0.7)):
        t = t_(0.3)
        f = 38 + 30 * np.exp(-t * 30)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18) * a
        s += 0.15 * lp(noise(0.3), 200) * np.exp(-t * 40) * a
        i = int(o * SR); out[i:i + len(s)] += s
    return st(np.tanh(out * 1.4) * gain)


def clock_tick(gain=0.2, f=2600, pan=0.0):
    t = t_(0.05)
    y = bp(noise(0.05), f * 0.7, f * 1.4) * np.exp(-t * 220) + 0.6 * np.sin(2 * np.pi * f * 1.3 * t) * np.exp(-t * 300)
    return st(y * gain, pan)


def glitch(d=0.25, gain=0.25):
    n = int(d * SR); y = np.zeros(n); i = 0
    while i < n:
        L = int(rng.uniform(0.004, 0.03) * SR)
        f = rng.choice([400, 800, 1600, 3200, 6400])
        tt = np.arange(min(L, n - i)) / SR
        y[i:i + len(tt)] = np.sign(np.sin(2 * np.pi * f * tt)) * rng.uniform(0.2, 1)
        i += L + int(rng.uniform(0, 0.02) * SR)
    y = bp(y, 300, 9000) * env(n, 0.002, d * 0.8, 2)
    return st(y * gain, width=0.6)


def data_stream(d=1.2, gain=0.2):
    n = int(d * SR); y = np.zeros(n)
    k = 0.0
    while k < d - 0.03:
        b = blip(rng.uniform(1800, 4200), 0.025, 1.0)[0]
        i = int(k * SR); y[i:i + len(b)] += b[:max(0, min(len(b), n - i))]
        k += rng.uniform(0.02, 0.06)
    y *= np.sin(np.pi * np.arange(n) / n) ** 0.7
    return pan_sweep(y * gain, -0.5, 0.5)


def scan_sweep(d=1.0, gain=0.25, f0=800, f1=2400):
    t = t_(d)
    f = f0 + (f1 - f0) * 0.5 * (1 - np.cos(np.pi * t / d))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) ** 2
    y += 0.3 * svf(noise(d), f * 2, 0.2, 1) * np.sin(np.pi * t / d)
    return pan_sweep(y * gain, -0.4, 0.4)


def servo(d=0.7, gain=0.2):
    t = t_(d)
    f = 520 + 300 * np.sin(np.pi * t / d)
    y = (np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.3 + bp(noise(d), 1500, 4000) * 0.4)
    y = lp(y, 5000) * np.sin(np.pi * t / d) ** 0.5
    return st(y * gain)


def shutter(gain=0.35):
    t = t_(0.18); y = np.zeros(len(t))
    for o in (0.0, 0.07):
        i = int(o * SR); s = bp(noise(0.05), 1500, 8000) * np.exp(-t_(0.05) * 120)
        y[i:i + len(s)] += s
    y += 0.4 * np.sin(2 * np.pi * 180 * t) * np.exp(-t * 50)
    return st(y * gain)


def engine(d=2.5, rpm0=1500, rpm1=4800, gain=0.35):
    t = t_(d); k = t / d
    rpm = rpm0 + (rpm1 - rpm0) * (1 - np.exp(-k * 3)) / (1 - np.exp(-3))
    f0 = rpm / 60 * 2  # 4-cyl firing
    ph = 2 * np.pi * np.cumsum(f0) / SR
    y = sum(a * np.sin(m * ph + rng.uniform(0, 6)) for m, a in ((1, 1), (2, .6), (3, .35), (4, .25), (6, .12)))
    y += 0.3 * svf(noise(d), f0 * 4, 0.4, 1)
    y = np.tanh(y * 1.5)
    y = lp(y, 2500) * env(len(t), 0.15, d, 0.8) * np.minimum(1, (d - t) / 0.4)
    return st(y * gain, width=0.3)


def screech(d=1.1, gain=0.25):
    t = t_(d)
    f = 1650 + 120 * np.sin(2 * np.pi * 7 * t) + rng.standard_normal(len(t)).cumsum() * 0.02
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.5 + svf(noise(d), np.full(len(t), 1800.0), 0.08, 1) * 0.8
    y = y * np.minimum(1, t / 0.05) * np.exp(-t * 1.8)
    return st(y * gain, width=0.4)


def tyre_swoosh(d=1.4, gain=0.3, pan0=-0.7, pan1=0.7):
    t = t_(d)
    y = svf(noise(d, 'pink'), 400 + 900 * np.sin(np.pi * t / d), 0.5, 1) * np.sin(np.pi * t / d) ** 1.5
    return pan_sweep(norm(y, 1) * gain, pan0, pan1)


def rumble_strip(d=1.6, gain=0.35, rate=22):
    t = t_(d)
    y = lp(noise(d, 'brown'), 300) * 0.6 + np.sin(2 * np.pi * 55 * t) * 0.6
    am = (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * rate * t))) ** 1
    y = y * am * np.sin(np.pi * t / d) ** 0.6
    return st(lp(y, 600) * gain)


def lane_chime(gain=0.3):
    out = np.zeros(int(0.7 * SR))
    for i, f in enumerate((1046.5, 784.0)):
        t = t_(0.35)
        s = (np.sin(2 * np.pi * f * t) + 0.2 * np.sin(2 * np.pi * 3 * f * t)) * np.exp(-t * 10)
        o = int(i * 0.16 * SR); out[o:o + len(s)] += s
    return st(out * gain)


def car_horn(d=0.32, gain=0.25, pan=0.3):
    t = t_(d)
    y = sum(np.tanh(4 * np.sin(2 * np.pi * f * t)) for f in (415, 523))
    y = bp(y, 300, 3000) * np.minimum(1, np.minimum(t / 0.01, (d - t) / 0.03))
    return st(y * gain, pan)


def impact_wrench(d=0.55, gain=0.25, pan=-0.3):
    t = t_(d)
    y = np.sign(np.sin(2 * np.pi * 38 * t)) * 0.4 + bp(noise(d), 800, 5000) * np.abs(np.sin(2 * np.pi * 19 * t))
    y += 0.4 * np.sin(2 * np.pi * 2400 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 38 * t))
    y = lp(y, 7000) * np.minimum(1, np.minimum(t / 0.01, (d - t) / 0.05))
    return st(y * gain, pan)


def metal_clank(gain=0.3, base=420, pan=0.2):
    t = t_(1.2)
    y = sum(a * np.sin(2 * np.pi * base * r * t) * np.exp(-t * dcy)
            for r, a, dcy in ((1, 1, 6), (2.76, .6, 9), (5.4, .4, 14), (8.93, .25, 20), (13.3, .15, 30)))
    y += 0.5 * bp(noise(1.2), 2000, 8000) * np.exp(-t * 80)
    return verb(st(y * gain, pan), 0.35, 0.25, 0.4, 1, 0.5)


def snap(gain=0.35, pan=0.0):
    t = t_(0.08)
    y = bp(noise(0.08), 1200, 7000) * np.exp(-t * 150) + 0.5 * np.sin(2 * np.pi * 900 * t) * np.exp(-t * 90)
    return st(y * gain, pan)


def counter_ticks(start, end, n, gain=0.12, f=2900, accel=True):
    """list of (time, sound) for a number counter"""
    ev = []
    for i in range(n):
        k = i / max(1, n - 1)
        tt = start + (end - start) * (1 - (1 - k) ** 1.8 if accel else k)
        ev.append((tt, clock_tick(gain * (0.7 + 0.3 * rng.random()), f * rng.uniform(0.95, 1.05), rng.uniform(-0.2, 0.2))))
    return ev


def tinnitus(d=4.0, f=6100, gain=0.05):
    t = t_(d)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 0.9) * np.minimum(1, t / 0.05)
    return st(y * gain)


def low_drone(d, root=36.71, gain=0.2, bright=350):
    t = t_(d); y = np.zeros(len(t))
    for m, a in ((1, 1), (2, .5), (1.5, .3), (3, .15)):
        for det in (-0.12, 0.13):
            y += a * np.sin(2 * np.pi * root * m * (1 + det / 100) * t + rng.uniform(0, 6))
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)
    y = lp(y, bright) * lfo
    return np.stack([y, np.roll(y, 600)]) * gain / 3


def road_amb(d, gain=0.3, interior=False):
    t = t_(d)
    rum = lp(noise(d, 'brown'), 160 if interior else 260) * 1.4
    tyre = svf(noise(d, 'pink'), np.full(len(t), 700.0 if not interior else 380.0), 0.9, 1) * (0.25 if not interior else 0.12)
    hum = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((48, .25), (96, .12), (144, .05)))
    y = rum + tyre + hum * (1.0 if interior else 0.5)
    y *= 0.85 + 0.15 * np.sin(2 * np.pi * 0.13 * t)
    s = np.stack([y, np.roll(y, 1200)])
    return s * gain / (np.abs(s).max() + 1e-9)


def moto_pass(d=3.0, gain=0.25, pan0=-0.9, pan1=0.9, f=95):
    t = t_(d); k = t / d
    dop = f * (1 + 0.06 * np.tanh((0.5 - k) * 6))
    ph = 2 * np.pi * np.cumsum(dop) / SR
    y = sum(a * (2 * ((m * ph / (2 * np.pi)) % 1) - 1) for m, a in ((1, 1), (2, .5), (3, .3)))
    y += 0.5 * svf(noise(d), dop * 6, 0.5, 1)
    y = svf(y, 1800 + 1500 * np.exp(-((k - 0.5) / 0.15) ** 2), 0.7, 0)
    y *= np.exp(-((k - 0.5) / 0.22) ** 2)
    return pan_sweep(norm(y, 1) * gain, pan0, pan1)


def city_amb(d, gain=0.3):
    t = t_(d)
    y = lp(noise(d, 'pink'), 1200) * 0.7 + lp(noise(d, 'brown'), 200) * 0.8
    y *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.09 * t)
    s = np.stack([y, np.roll(y, 2400)])
    s = verb(s / (np.abs(s).max() + 1e-9), 0.8, 0.3, 0.6, 1, 0.1)[:, :len(t)]
    return s * gain / (np.abs(s).max() + 1e-9)


def room_tone(d, gain=0.02):
    y = lp(noise(d, 'pink'), 3000)
    return np.stack([y, np.roll(y, 777)]) * gain / (np.abs(y).max() + 1e-9)


def logo_sting(gain=0.7, notes=(62, 69, 74, 78, 81)):
    """impact + sub + chord swell + shimmer, starts at hit (t=0)"""
    d = 4.0; out = np.zeros((2, int(d * SR) + int(2.5 * SR)))
    def add(s, at=0.0, g=1.0):
        i = int(at * SR); n = min(s.shape[1], out.shape[1] - i); out[:, i:i + n] += s[:, :n] * g
    add(sub_boom(2.8, 70, 30), 0, 0.9)
    add(transient(0.3, 600, 9000, 0.35), 0)
    add(shimmer(3.5, notes, 0.32, 0.05), 0.02)
    # warm chord pad
    t = t_(d); ch = np.zeros(len(t))
    for m in notes[:3]:
        f = 440 * 2 ** ((m - 69) / 12)
        for det in (-0.2, 0.2):
            ch += np.sin(2 * np.pi * f * (1 + det / 100) * t)
    ch = lp(ch, 2500) * env(len(t), 0.25, 2.5, 2)
    add(verb(st(ch * 0.15), 0.8, 0.4, 0.5, 1, 2.0), 0)
    return out * gain
