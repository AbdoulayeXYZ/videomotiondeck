"""Sound design: automatic cues from scene events + ambiences per segment + manual cue list."""
import numpy as np
from .common import log, SR
from . import sfxlib as X

AMB = {
    'road': lambda d: X.road_amb(d, 0.10),
    'interior': lambda d: X.road_amb(d, 0.06, interior=True),
    'city': lambda d: X.city_amb(d, 0.07),
    'room': lambda d: X.room_tone(d, 0.012),
    'night': lambda d: X.road_amb(d, 0.09),
}


def _put(buf, at, s, g=1.0):
    s = np.asarray(s)
    if s.ndim == 1: s = X.st(s)
    i = int(round(at * SR))
    if i < 0: s = s[:, -i:]; i = 0
    n = min(s.shape[1], buf.shape[1] - i)
    if n > 0: buf[:, i:i + n] += s[:, :n] * g


def hit(buf, at, g=1.0, shimmer=False, braam=False):
    _put(buf, at, X.sub_boom(2.2, 66, 30), 0.55 * g)
    _put(buf, at, X.transient(0.25, 700, 9000, 0.22), g)
    if braam: _put(buf, at, X.braam(2.6), 0.45 * g)
    if shimmer: _put(buf, at + 0.01, X.shimmer(2.0, (74, 81, 86), 0.18, 0.05), g)


def cue(buf, c, t, seg_t1=None):
    """Manual cue types (all optional params have sensible defaults)."""
    ty = c['type']; g = float(c.get('gain', 1.0))
    if ty == 'hit': hit(buf, t, g, c.get('shimmer', False), c.get('braam', False))
    elif ty == 'impact': hit(buf, t, 1.2 * g, False, True)
    elif ty == 'braam': _put(buf, t, X.braam(c.get('dur', 2.6)), 0.45 * g)
    elif ty == 'whoosh': _put(buf, t, X.whoosh(c.get('dur', 0.8), 250, 3000, 0.55, -0.5, 0.5, 0.15), g)
    elif ty == 'swoosh': _put(buf, t, X.swoosh_fast(0.4, 0.12), g)
    elif ty == 'riser':
        d = float(c.get('dur', 3.0)); _put(buf, t - d, X.riser(d, 200, 3000, 0.3), g)
    elif ty == 'reverse_swell':
        d = float(c.get('dur', 1.2)); _put(buf, t - d, X.reverse_swell(d, 0.3, 6500), g)
    elif ty == 'alert': _put(buf, t, X.alert_tone(int(c.get('n', 4)), c.get('f', 2100), 0.13, 0.07, 0.42), g)
    elif ty == 'alarm': _put(buf, t, X.alert_tone(6, 2600, 0.08, 0.05, 0.42), g); _put(buf, t, X.braam(2.2), 0.3 * g)
    elif ty == 'chime': _put(buf, t, X.chime_alert(0.3), g)
    elif ty == 'notif': _put(buf, t, X.notif(0.26), g)
    elif ty == 'heartbeat':
        n = int(c.get('count', 8)); dur = float(c.get('dur', 6.0)); ts = t + np.cumsum(np.linspace(1.0, 0.45, n)) * dur / np.sum(np.linspace(1.0, 0.45, n)) - dur / n
        for i, tt in enumerate(ts): _put(buf, tt, X.heartbeat(0.3 + 0.04 * i), g)
    elif ty == 'counter':
        for tt, s in X.counter_ticks(t, t + float(c.get('dur', 2.0)), int(c.get('n', 30)), 0.08, 2900, accel=False): _put(buf, tt, s, g)
    elif ty == 'tinnitus': _put(buf, t, X.tinnitus(c.get('dur', 5.0), 6100, 0.035), g)
    elif ty == 'engine': _put(buf, t, X.engine(c.get('dur', 2.5), 1400, 5200, 0.26), g)
    elif ty == 'screech': _put(buf, t, X.screech(c.get('dur', 1.0), 0.15), g)
    elif ty == 'tyre': _put(buf, t, X.tyre_swoosh(1.5, 0.28, -0.8, 0.8), g)
    elif ty == 'rumble': _put(buf, t, X.rumble_strip(1.5, 0.3), g); _put(buf, t + 0.1, X.lane_chime(0.22), g)
    elif ty == 'horn': _put(buf, t, X.verb(X.car_horn(0.28, 0.07, -0.55), 0.7, 0.4, 0.6, 1, 0.8), g)
    elif ty == 'moto': _put(buf, t, X.moto_pass(c.get('dur', 3.0), 0.12, -0.9, 0.8, 95), g)
    elif ty == 'wrench': _put(buf, t, X.impact_wrench(0.5, 0.09, -0.5), g)
    elif ty == 'clank': _put(buf, t, X.metal_clank(0.1, 420, 0.3), g)
    elif ty == 'snap': _put(buf, t, X.snap(0.2), g)
    elif ty == 'shutter': _put(buf, t, X.shutter(0.2), g)
    elif ty == 'servo': _put(buf, t, X.servo(0.6, 0.08), g)
    elif ty == 'scan': _put(buf, t, X.scan_sweep(1.1, 0.04, 900, 2600), g)
    elif ty == 'data': _put(buf, t, X.data_stream(c.get('dur', 1.1), 0.06), g)
    elif ty == 'glitch': _put(buf, t, X.glitch(0.2, 0.06), g)
    elif ty == 'shimmer': _put(buf, t, X.shimmer(2.0, (74, 81, 86), 0.12, 0.06), g)
    elif ty == 'pop': _put(buf, t, X.ui_pop(c.get('f', 900), 0.16), g)
    elif ty == 'tick': _put(buf, t, X.tick(2600, 0.03, 0.06), g)
    elif ty == 'sting': _put(buf, t, X.logo_sting(0.5), g)
    else:
        raise SystemExit(f"[vmd] ERROR: unknown sfx cue type '{ty}'")


def design(pr, tl):
    N = int(pr.total(tl) * SR) + SR
    sfx = np.zeros((2, N)); amb = np.zeros((2, N))
    ev = pr.load_json('events.json', {})
    cfg = pr.spec.get('sfx', {})
    auto = cfg.get('auto', True)
    idx = pr.seg_index(tl)
    for k, r in enumerate(tl):
        a, b = r['t0'], r['t1']
        if auto and r.get('type', 'scene') == 'scene':
            pops = 0
            for e in ev.get(r['id'], []):
                t = a + float(e['t']); kd = e['kind']
                if kd == 'in': _put(sfx, t - 0.12, X.whoosh(0.7, 250, 3000, 0.55, -0.5, 0.5, 0.13))
                elif kd == 'in_soft': _put(sfx, t - 0.1, X.whoosh(0.9, 200, 1800, 0.5, -0.3, 0.3, 0.07))
                elif kd == 'pop': _put(sfx, t, X.ui_pop(700 + 110 * pops, 0.16)); _put(sfx, t, X.tick((700 + 110 * pops) * 3, 0.03, 0.04)); pops += 1
                elif kd == 'pop_hi': _put(sfx, t, X.ui_pop(1100, 0.16)); _put(sfx, t + 0.02, X.shimmer(1.2, (86, 90), 0.06, 0.06))
                elif kd == 'tick': _put(sfx, t, X.tick(2600, 0.02, 0.04))
                elif kd == 'counter':
                    for tt, s in X.counter_ticks(t, a + float(e['t1']), int(e.get('n', 24)), 0.06, 3000): _put(sfx, tt, s)
                elif kd == 'hit': hit(sfx, t, float(e.get('strength', 0.5)), e.get('shimmer', False))
                elif kd == 'scan': _put(sfx, t, X.scan_sweep(0.9, 0.035, 1200, 2600))
                elif kd == 'whoosh': _put(sfx, t, X.whoosh(0.5, 400, 3500, 0.6, 0.4, -0.4, 0.1))
                elif kd == 'swoosh': _put(sfx, t, X.swoosh_fast(0.35, 0.07, -0.6, 0.6, 2600))
                elif kd == 'sting': _put(sfx, t - 1.0, X.reverse_swell(1.0, 0.22, 6500)); _put(sfx, t, X.logo_sting(0.5))
                elif kd == 'swell_end':
                    L = float(e.get('len', 1.2)); _put(sfx, t - L, X.reverse_swell(L, 0.3, 7000))
        if auto and r.get('type') in ('clip', 'still') and k > 0 and r.get('cut_sound', True):
            prev = tl[k - 1]
            if prev.get('type', 'scene') != r.get('type'):
                _put(sfx, a - 0.15, X.whoosh(0.5, 300, 2600, 0.5, -0.4, 0.4, 0.07))
        if r.get('amb') and r['amb'] in AMB:
            d = r['dur'] + (pr.end_hold if k == len(tl) - 1 else 0)
            _put(amb, a, X.fade(AMB[r['amb']](d), 0.3, 0.4), float(r.get('amb_gain', 1.0)))
    placed = pr.load_json('placed.json') or []
    span = {}
    for p in placed:
        a0, b0 = span.get(p['line'], (1e9, 0))
        span[p['line']] = (min(a0, p['t0']), max(b0, p['t1']))
    for c in cfg.get('cues', []):
        if 'after_line' in c or 'at_line' in c:          # anchored to the voice: never on top of the words
            k = int(c.get('after_line', c.get('at_line')))
            if k not in span:
                log(f'  (sfx cue on line {k} skipped: no voice placed yet)'); continue
            t = (span[k][1] + float(c.get('offset', 0.15))) if 'after_line' in c else (span[k][0] + float(c.get('offset', 0.0)))
            cue(sfx, c, t); continue
        if c.get('seg') not in idx:
            raise SystemExit(f"[vmd] ERROR: sfx cue refers to unknown segment '{c.get('seg')}'")
        cue(sfx, c, idx[c['seg']]['t0'] + float(c.get('at', 0)))
    np.save(pr.build / 'sfx.npy', sfx.astype(np.float32)); np.save(pr.build / 'amb.npy', amb.astype(np.float32))
    log(f'sfx -> {pr.build / "sfx.npy"} ({len(cfg.get("cues", []))} manual cues, auto={auto})')
