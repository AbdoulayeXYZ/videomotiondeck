"""videomotiondeck — shared helpers: project loading, paths, timeline."""
import json, os, shutil, subprocess, sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]
ENGINE = SKILL_DIR / 'engine' / 'scenes.html'
CACHE = Path(os.environ.get('VMD_CACHE', Path.home() / '.cache' / 'videomotiondeck'))
SR = 48000

DEFAULT_BRAND = {"bg": "#020D19", "bg2": "#0A2236", "accent": "#00C8BE", "accent2": "#FFE500",
                 "alert": "#FF4545", "text": "#FFFFFF", "muted": "#B9C6D3"}


def log(*a):
    print('[vmd]', *a, flush=True)


def die(msg):
    print('[vmd] ERROR:', msg, file=sys.stderr, flush=True)
    sys.exit(1)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        die(f"command failed: {' '.join(map(str, cmd))[:300]}\n{r.stderr[-2000:]}")
    return r.stdout


def probe_duration(path):
    out = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)])
    return float(out.strip())


class Project:
    """Loads project.json, resolves paths and the timeline."""

    def __init__(self, path):
        self.path = Path(path).resolve()
        if not self.path.exists():
            die(f'project file not found: {self.path}')
        self.root = self.path.parent
        with open(self.path, encoding='utf-8') as f:
            self.spec = json.load(f)
        self.build = self.root / self.spec.get('build_dir', 'build')
        self.build.mkdir(parents=True, exist_ok=True)
        self.fps = int(self.spec.get('fps', 25))
        self.size = tuple(self.spec.get('size', [1920, 1080]))
        self.brand = {**DEFAULT_BRAND, **self.spec.get('brand', {})}
        self.end_hold = float(self.spec.get('end_hold', 1.6))
        self.max_duration = self.spec.get('max_duration')
        self.lang = self.spec.get('language', 'fr')
        self.segments = self.spec.get('segments', [])
        ids = [s.get('id') for s in self.segments]
        if len(ids) != len(set(ids)) or None in ids:
            die('every segment needs a unique "id"')
        self._validate()

    # ---------------------------------------------------------------- paths
    def p(self, rel):
        if rel is None:
            return None
        q = Path(rel)
        return q if q.is_absolute() else (self.root / q)

    def _validate(self):
        for s in self.segments:
            t = s.get('type', 'scene')
            if t == 'scene' and 'scene' not in s:
                die(f'segment {s["id"]}: type "scene" needs a "scene" name')
            if t in ('clip', 'still') and not s.get('src'):
                die(f'segment {s["id"]}: type "{t}" needs "src"')
            if t in ('clip', 'still') and not self.p(s['src']).exists():
                die(f'segment {s["id"]}: file not found {s["src"]}')
            if t == 'freeze' and not s.get('of'):
                die(f'segment {s["id"]}: type "freeze" needs "of" (the segment id to freeze)')

    # ---------------------------------------------------------------- timeline
    def base_duration(self, s):
        t = s.get('type', 'scene')
        if t == 'clip':
            src_d = probe_duration(self.p(s['src']))
            a = float(s.get('in', 0)); b = float(s.get('out', src_d))
            return max(0.04, (min(b, src_d) - a) / float(s.get('speed', 1.0)))
        return float(s.get('dur', 4.0))

    def fit_key(self, voice_file):
        """Signature of everything the voice fit depends on: script, cues, segment timing fields, the voice file."""
        import hashlib
        v = self.spec.get('voice', {})
        f = Path(voice_file) if voice_file else None
        sig = {'lines': [[l.get('text'), l.get('seg'), l.get('at'), l.get('pause_before')] for l in v.get('lines', [])],
               'opts': [v.get('auto_fit', True), v.get('tighten', True), v.get('tail', 0.55)],
               'segs': [[s.get(k) for k in ('id', 'type', 'dur', 'in', 'out', 'speed', 'src', 'extend', 'elastic', 'tighten', 'tail', 'min_dur', 'voice_free')]
                        for s in self.segments],
               'file': [str(f), f.stat().st_size, int(f.stat().st_mtime)] if f and f.exists() else None}
        return hashlib.md5(json.dumps(sig, sort_keys=True, default=str).encode()).hexdigest()

    _stale_warned = False

    def timeline(self, extra=None):
        """Segments with t0/t1/dur. Uses the last voice fit (build/timeline_extra.json) only if it is still valid."""
        if extra is None:
            data = self.load_json('timeline_extra.json', {}) or {}
            if 'key' in data:
                if data['key'] == self.fit_key(data.get('file')):
                    extra = data.get('extra', {})
                else:
                    extra = {}
                    if not Project._stale_warned:
                        log('! the voice fit is outdated (script, cues, segments or voice file changed) — run `voice` (or `all`) again')
                        Project._stale_warned = True
            else:
                extra = data
        out, t = [], 0.0
        for s in self.segments:
            d = self.base_duration(s) + float(extra.get(s['id'], 0.0))
            d = round(d * self.fps) / self.fps
            out.append({**s, 't0': round(t, 4), 't1': round(t + d, 4), 'dur': d})
            t += d
        return out

    def total(self, tl=None):
        tl = tl or self.timeline()
        return tl[-1]['t1'] + self.end_hold if tl else 0.0

    def seg_index(self, tl):
        return {r['id']: r for r in tl}

    # ---------------------------------------------------------------- json io
    def load_json(self, name, default=None):
        f = self.build / name
        if f.exists():
            with open(f, encoding='utf-8') as fh:
                return json.load(fh)
        return default

    def save_json(self, name, obj):
        with open(self.build / name, 'w', encoding='utf-8') as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)


def need(binary, hint):
    if shutil.which(binary) is None:
        die(f'"{binary}" not found. {hint}')
