"""Render motion-design scenes (and caption overlays) to image sequences with headless Chromium."""
import asyncio, hashlib, json, os, time
from pathlib import Path
from .common import ENGINE, log, die


def _to_url(v, project):
    """Turn relative/absolute media paths inside scene data into file:// URLs."""
    if isinstance(v, dict):
        return {k: _to_url(x, project) for k, x in v.items()}
    if isinstance(v, list):
        return [_to_url(x, project) for x in v]
    if isinstance(v, str) and v.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif')) and not v.startswith(('http', 'file:', 'data:')):
        p = project.p(v)
        if not p.exists():
            die(f'image not found: {v}')
        return p.resolve().as_uri()
    return v


async def _render_job(browser, job, project, stats):
    page = await browser.new_page(viewport={'width': project.size[0], 'height': project.size[1]})
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.on('console', lambda m: errs.append(m.text) if m.type in ('error', 'warning') else None)
    await page.goto(ENGINE.resolve().as_uri())
    cfg = {'scene': job['scene'], 'data': _to_url(job.get('data', {}), project), 'dur': job['dur'],
           'brand': project.brand, 'transparent': job.get('transparent', False), 'lang': project.lang,
           'preroll': float(project.spec.get('preroll', 0.3))}
    try:
        await page.evaluate('cfg => VMD.build(cfg)', cfg)
    except Exception as e:
        die(f"scene '{job['id']}' failed to build: {e}\n{errs[:5]}")
    events = await page.evaluate('VMD.events()')
    out = Path(job['out']); out.mkdir(parents=True, exist_ok=True)
    n = int(round(job['dur'] * project.fps))
    frames = job.get('frames')  # optional list of frame indices to render (preview)
    t0 = time.time()
    rng = frames if frames is not None else range(n)
    for i in rng:
        t = i / project.fps if frames is None else i
        await page.evaluate(f'VMD.render({t})')
        if job.get('transparent'):
            await page.screenshot(path=str(out / f'f{i:05d}.png') if frames is None else str(out / f"t{t:06.2f}.png"), omit_background=True)
        else:
            await page.screenshot(path=str(out / f'f{i:05d}.jpg') if frames is None else str(out / f"t{t:06.2f}.jpg"), type='jpeg', quality=94)
    await page.close()
    if errs:
        log(f"  warnings in '{job['id']}': {errs[:3]}")
    stats[job['id']] = {'events': events, 'frames': n, 'secs': round(time.time() - t0, 1)}


async def _run(jobs, project, workers):
    from playwright.async_api import async_playwright
    stats = {}
    async with async_playwright() as p:
        exe = os.environ.get('VMD_CHROMIUM')
        kw = {'args': ['--allow-file-access-from-files', '--disable-web-security', '--font-render-hinting=none']}
        if exe:
            kw['executable_path'] = exe
        browser = await p.chromium.launch(**kw)
        queue = list(jobs)
        async def worker():
            while queue:
                j = queue.pop(0)
                log(f"  rendering {j['id']} ({j['scene']}, {j['dur']:.2f}s)")
                await _render_job(browser, j, project, stats)
        await asyncio.gather(*[worker() for _ in range(max(1, workers))])
        await browser.close()
    return stats


def scene_jobs(project, tl, only=None):
    jobs = []
    sync = project.load_json('sync.json', {}) or {}
    for r in tl:
        if only and r['id'] not in only:
            continue
        if r.get('type', 'scene') == 'scene':
            data = dict(r.get('data', {}))
            pre = float(project.spec.get('preroll', 0.3))         # voice times are segment times; scenes run pre-rolled
            sy = {k: round(v + pre, 3) for k, v in sync.get(r['id'], {}).items()}
            named = {k: sy.pop(k) for k in list(sy) if not k.isdigit()}
            if sy and 'times' not in data:
                data['sync'] = sy                                   # items/nodes/steps pop on their line
            if 'answer' in named and isinstance(data.get('answer'), dict):
                data['answer'] = {**data['answer'], 'at': named['answer']}   # brief: "Voici notre réponse"
            if 'final' in named:
                data['final_at'] = named['final']                    # logo: "Merci."
            if 'highlight' in named:
                data['highlight_at'] = named['highlight']            # brief: the quote lights up
            jobs.append({'id': r['id'], 'scene': r['scene'], 'data': data, 'dur': r['dur'],
                         'out': str(project.build / 'frames' / r['id'])})
        elif r.get('caption'):
            jobs.append({'id': r['id'] + '__cap', 'scene': 'caption', 'data': r['caption'], 'dur': r['dur'],
                         'transparent': True, 'out': str(project.build / 'frames' / (r['id'] + '__cap'))})
    return jobs


def _job_key(job, project):
    """Cache key: scene data + duration + brand + size + engine version + referenced image mtimes."""
    def mt(v):
        if isinstance(v, dict):
            return [mt(x) for x in v.values()]
        if isinstance(v, list):
            return [mt(x) for x in v]
        if isinstance(v, str) and v.startswith('file:'):
            from urllib.parse import unquote, urlparse
            p = Path(unquote(urlparse(v).path))
            return p.stat().st_mtime if p.exists() else 0
        return None
    data = _to_url(job.get('data', {}), project)
    eng = [(ENGINE.parent / f).stat().st_mtime for f in ('scenes.js', 'scenes.html')]
    blob = json.dumps([job['scene'], data, round(job['dur'], 4), project.brand, project.size, project.fps, project.lang,
                       project.spec.get('preroll', 0.3),
                       job.get('transparent', False), eng, mt(data)], sort_keys=True, default=str)
    return hashlib.md5(blob.encode()).hexdigest()


def render_scenes(project, tl, only=None, workers=None, force=False):
    workers = workers or max(1, min(4, (os.cpu_count() or 2)))
    jobs, skipped = [], []
    for j in scene_jobs(project, tl, only):
        d = Path(j['out']); key = _job_key(j, project); kf = d / 'key.json'
        n = int(round(j['dur'] * project.fps))
        ext = 'png' if j.get('transparent') else 'jpg'
        if not force and kf.exists() and json.loads(kf.read_text()).get('key') == key and (d / f'f{n - 1:05d}.{ext}').exists():
            skipped.append(j['id']); continue
        j['key'] = key
        if d.exists():
            for f in d.glob('f*.*'):
                f.unlink()
        jobs.append(j)
    if skipped:
        log(f'{len(skipped)} scene(s) unchanged (cached): {", ".join(skipped)}')
    if not jobs:
        return {}
    log(f'rendering {len(jobs)} scene(s) with {workers} worker(s)')
    stats = asyncio.run(_run(jobs, project, workers))
    ev = project.load_json('events.json', {})
    for j in jobs:
        if j['id'] in stats:
            ev[j['id']] = stats[j['id']]['events']
            (Path(j['out']) / 'key.json').write_text(json.dumps({'key': j['key']}))
    project.save_json('events.json', ev)
    return stats


def preview(project, tl, times_per_seg=3, only=None, cols=4):
    """Render a few stills per scene and build a contact sheet (fast visual check)."""
    from PIL import Image
    jobs = scene_jobs(project, tl, only)
    for j in jobs:
        d = j['dur']
        j['frames'] = [round(d * k / (times_per_seg + 1), 2) for k in range(1, times_per_seg + 1)] + [round(max(0, d - 0.08), 2)]
        j['out'] = str(project.build / 'preview' / j['id'])
    asyncio.run(_run(jobs, project, max(1, min(4, os.cpu_count() or 2))))
    tiles = []
    for j in jobs:
        for f in sorted(Path(j['out']).glob('t*.*')):
            tiles.append((j['id'], f))
    if not tiles:
        return None
    cols = max(1, int(cols)); tw = 1920 // cols; th = tw * 9 // 16
    sheet = Image.new('RGB', (cols * tw, ((len(tiles) + cols - 1) // cols) * (th + 24)), (20, 20, 20))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(sheet)
    for k, (sid, f) in enumerate(tiles):
        im = Image.open(f).convert('RGBA')
        bg = Image.new('RGBA', im.size, (40, 40, 40, 255)); bg.alpha_composite(im)
        x, y = (k % cols) * tw, (k // cols) * (th + 24)
        sheet.paste(bg.convert('RGB').resize((tw, th)), (x, y + 24))
        dr.text((x + 6, y + 5), f'{sid}  {f.stem[1:]}s', fill=(255, 220, 0))
    out = project.build / ('preview_sheet.jpg' if not only else f'preview_{"_".join(only)[:60]}.jpg')
    sheet.save(out, quality=85)
    return out
