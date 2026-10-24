"""Mix & master: voice on top, music/ambience/SFX ducked (with a speech-band carve), -14 LUFS, -1.2 dBTP."""
import numpy as np
from scipy.ndimage import maximum_filter1d, uniform_filter1d
from scipy.signal import resample_poly, sosfiltfilt, butter
from .common import log, SR


def limit(x, ceil_db=-1.2, look=0.004, rel=0.12):
    ceil = 10 ** (ceil_db / 20)
    up = np.abs(resample_poly(x, 4, 1, axis=1)).max(axis=0)
    pk = up.reshape(-1, 4).max(axis=1)[:x.shape[1]] if len(up) >= 4 * x.shape[1] else np.abs(x).max(axis=0)
    L = int(look * SR); pk = maximum_filter1d(pk, size=2 * L + 1)
    g = np.minimum(1.0, ceil / (pk + 1e-12))
    out = np.empty_like(g); cur = 1.0; a = 1 - np.exp(-1 / (rel * SR))
    # fast path in numpy chunks is tricky (recursive) — numba if available
    try:
        from numba import njit
        @njit(cache=False)
        def smooth(g, a):
            out = np.empty_like(g); cur = 1.0
            for i in range(len(g)):
                cur = g[i] if g[i] < cur else cur + a * (g[i] - cur)
                out[i] = cur
            return out
        out = smooth(g, a)
    except Exception:
        for i in range(len(g)):
            cur = g[i] if g[i] < cur else cur + a * (g[i] - cur); out[i] = cur
    return x * out


def mixdown(pr, tl):
    import soundfile as sf, pyloudnorm as pyln
    from pedalboard import Pedalboard, PeakFilter, Compressor, HighpassFilter, LowShelfFilter, HighShelfFilter
    total = pr.total(tl); N = int(round(total * SR))
    meter = pyln.Meter(SR)

    def fitN(x):
        y = np.zeros((2, N)); n = min(N, x.shape[1]); y[:, :n] = x[:, :n]; return y

    def lufs(x):
        try: return meter.integrated_loudness(x.T)
        except Exception: return -70.0

    def gain_to(x, target):
        l = lufs(x)
        return x if l < -69 else x * 10 ** ((target - l) / 20)

    vpath = pr.build / 'voice_track.wav'
    if vpath.exists():
        v, _ = sf.read(vpath, always_2d=True); voice = fitN(v.T)
        voice = gain_to(voice, -16.5); voice = limit(voice, -5.0, 0.002, 0.05); voice = gain_to(voice, -16.5)
    else:
        log('no voice_track.wav — music & sound design only'); voice = np.zeros((2, N))
    mp = pr.build / 'music' / 'music.npy'
    music = fitN(np.load(mp)) if mp.exists() else np.zeros((2, N))
    if np.abs(music).max() > 0:
        music = Pedalboard([PeakFilter(cutoff_frequency_hz=2800, gain_db=-3.0, q=0.7), PeakFilter(cutoff_frequency_hz=1200, gain_db=-1.5, q=0.8),
                            Compressor(threshold_db=-20, ratio=2.0, attack_ms=30, release_ms=250)])(music.astype(np.float32), SR)
        music = gain_to(music, float(pr.spec.get('mix', {}).get('music_lufs', -23.5)))
        gp = pr.build / 'music' / 'music_gain_db.npy'
        if gp.exists():
            gdb = np.load(gp)[:N]; gdb = np.concatenate([gdb, np.zeros(N - len(gdb))])
            gdb = uniform_filter1d(gdb, int(0.4 * SR))
            music = music * 10 ** (gdb / 20)
    sfx = fitN(np.load(pr.build / 'sfx.npy')) * 0.62 if (pr.build / 'sfx.npy').exists() else np.zeros((2, N))
    amb = fitN(np.load(pr.build / 'amb.npy')) if (pr.build / 'amb.npy').exists() else np.zeros((2, N))
    if np.abs(amb).max() > 0:
        amb = Pedalboard([HighpassFilter(70)])(amb.astype(np.float32), SR) * 8.5
    # ducking key
    hop = 240; v = np.abs(voice).max(axis=0)
    e = np.sqrt(np.maximum(uniform_filter1d(v[:len(v) // hop * hop].reshape(-1, hop).mean(axis=1) ** 2, 3), 0))
    on = (20 * np.log10(e + 1e-9) > -42).astype(float)
    on = maximum_filter1d(on, size=int(0.25 * SR / hop))
    look = int(0.06 * SR / hop); on = np.concatenate([on[look:], np.zeros(look)])
    sm = np.zeros_like(on); a_att = 1 - np.exp(-1 / (0.05 * SR / hop)); a_rel = 1 - np.exp(-1 / (0.4 * SR / hop))
    for i in range(1, len(on)):
        a = a_att if on[i] > sm[i - 1] else a_rel
        sm[i] = sm[i - 1] + a * (on[i] - sm[i - 1])
    key = np.repeat(sm, hop); key = np.concatenate([key, np.zeros(max(0, N - len(key)))])[:N]
    sos = butter(2, [900, 4500], 'bandpass', fs=SR, output='sos')

    def duck(x, full_db, band_db):
        if np.abs(x).max() == 0: return x
        band = sosfiltfilt(sos, x, axis=1); rest = x - band
        return rest * 10 ** (full_db * key / 20) + band * 10 ** ((full_db + band_db) * key / 20)
    music_d, amb_d, sfx_d = duck(music, -6.0, -6.0), duck(amb, -4.0, -6.0), duck(sfx, -3.0, -5.0)
    mixed = voice + music_d + amb_d + sfx_d
    np.save(pr.build / 'bus_voice.npy', voice.mean(axis=0).astype(np.float32))
    np.save(pr.build / 'bus_rest.npy', (music_d + amb_d + sfx_d).mean(axis=0).astype(np.float32))
    np.save(pr.build / 'bus_sfx.npy', sfx_d.mean(axis=0).astype(np.float32))
    master = Pedalboard([Compressor(threshold_db=-16, ratio=1.8, attack_ms=20, release_ms=200),
                         LowShelfFilter(cutoff_frequency_hz=60, gain_db=0.5), HighShelfFilter(cutoff_frequency_hz=12000, gain_db=0.8)])(mixed.astype(np.float32), SR)
    target = float(pr.spec.get('mix', {}).get('loudness', -14.0))
    lim = master
    for _ in range(4):
        lim = limit(master)
        d = target - lufs(lim)
        if abs(d) < 0.05: break
        master = master * 10 ** (d / 20)
    master = lim
    f = int(min(1.6, pr.end_hold) * SR)
    if f > 0: master[:, -f:] *= np.linspace(1, 0, f) ** 1.5
    master[:, :int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))
    sf.write(pr.build / 'master.wav', master.T, SR, subtype='PCM_24')
    rep = {'voice_lufs': round(float(lufs(voice)), 1), 'music_lufs_after_ducking': round(float(lufs(music_d)), 1),
           'sfx_lufs': round(float(lufs(sfx_d)), 1), 'master_lufs': round(float(lufs(master)), 1),
           'master_peak_db': round(float(20 * np.log10(np.abs(master).max() + 1e-9)), 1)}
    pr.save_json('mix_report.json', rep)
    log(f'master -> {pr.build / "master.wav"}  {rep}')
    return rep
