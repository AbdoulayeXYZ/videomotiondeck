"""Render a custom timeline page (film.html exposing window.render(t)) to JPEG frames with Chromium.

  python3 render_frames.py full [workers]          -> fr/f00000.jpg ... (all frames)
  python3 render_frames.py range 1800-2080 0-80    -> re-render only those frame ranges (fast fixes)
  python3 render_frames.py preview 4.5 33 76.4     -> pv/t004.50.jpg ... (look before rendering)
The page is built from film.html with __TIMING__ replaced by timing.json (done here).
Encode: ffmpeg -framerate 25 -i fr/f%05d.jpg -i master.wav -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 256k -shortest -movflags +faststart out.mp4
"""
import asyncio, sys, json, os
from playwright.async_api import async_playwright

FPS = 25
T = json.load(open('timing.json'))
N = int(T['total'] * FPS)
open('film_r.html', 'w', encoding='utf-8').write(open('film.html', encoding='utf-8').read().replace('__TIMING__', json.dumps(T, ensure_ascii=False)))
mode = sys.argv[1]


async def job(b, items, outd, frames):
    p = await b.new_page(viewport={'width': 1920, 'height': 1080}); errs = []
    p.on('pageerror', lambda e: errs.append(str(e)))
    await p.goto('file://' + os.path.abspath('film_r.html')); await p.evaluate('document.fonts.ready')
    await p.evaluate("Promise.all([...document.images].map(i=>i.decode().catch(()=>0)))")
    for i in items:
        t = i / FPS if frames else i
        await p.evaluate(f'render({t})')
        name = f'f{i:05d}.jpg' if frames else f't{t:06.2f}.jpg'
        await p.screenshot(path=f'{outd}/{name}', type='jpeg', quality=92)
    if errs: print('PAGE ERRORS', errs[:3])


async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(args=['--allow-file-access-from-files'])
        if mode in ('full', 'range'):
            os.makedirs('fr', exist_ok=True)
            if mode == 'full':
                fr = list(range(N)); k = int(sys.argv[2]) if len(sys.argv) > 2 else 2
            else:
                fr = []; k = 2
                for r in sys.argv[2:]:
                    x, y = map(int, r.split('-')); fr += list(range(x, min(y, N - 1) + 1))
            await asyncio.gather(*[job(b, fr[i::k], 'fr', True) for i in range(k)])
        else:
            os.makedirs('pv', exist_ok=True); await job(b, [float(x) for x in sys.argv[2:]], 'pv', False)
        await b.close()

asyncio.run(main())
