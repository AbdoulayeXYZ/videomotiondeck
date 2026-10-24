"""License-free placeholder media generated on the fly (so a new project previews instantly).
Replace every file in media/ with the real ones — keep the same names or update project.json."""
import math, random, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from .common import SKILL_DIR, log

FONT = SKILL_DIR / 'assets' / 'fonts' / 'Montserrat-800.ttf'
FONT_M = SKILL_DIR / 'assets' / 'fonts' / 'Montserrat-500.ttf'


def _font(size, bold=True):
    try:
        return ImageFont.truetype(str(FONT if bold else FONT_M), size)
    except Exception:
        return ImageFont.load_default()


def _hex(c):
    c = c.lstrip('#'); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def logo(path, text='BRAND', color='#00C8BE', fg='#FFFFFF'):
    W, H = 900, 300
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = _hex(color)
    d.ellipse((20, 40, 240, 260), outline=c + (255,), width=26)
    d.polygon([(95, 95), (185, 150), (95, 205)], fill=c + (255,))
    sz = 118
    while sz > 30 and _font(sz).getlength(text) > W - 300:
        sz -= 4
    d.text((280, 150), text, font=_font(sz), fill=_hex(fg) + (255,), anchor='lm')
    im.save(path)


def partner_logo(path, text='PARTNER', bg='#FFE500'):
    W, H = 760, 260
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, W, H), 36, fill=_hex(bg) + (255,))
    sz = 104
    while sz > 30 and _font(sz).getlength(text) > W - 80:
        sz -= 4
    d.text((W / 2, H / 2), text, font=_font(sz), fill=(15, 15, 20, 255), anchor='mm')
    im.save(path)


def product(path, color='#00C8BE', name='PRODUCT'):
    """Neutral product placeholder (rounded device + name) on transparent background — replace with a real cut-out."""
    W, H = 1400, 1000
    big = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
    d.rounded_rectangle((330, 210, 1070, 790), 110, fill=(40, 47, 56, 255))
    d.rounded_rectangle((350, 228, 1050, 420), 92, fill=(58, 67, 78, 255))
    d.rounded_rectangle((430, 470, 970, 690), 36, fill=(18, 24, 30, 255))
    sz = 92
    while sz > 28 and _font(sz).getlength(name) > 500:
        sz -= 4
    d.text((700, 580), name, font=_font(sz), fill=_hex(color) + (255,), anchor='mm')
    d.ellipse((960, 300, 1000, 340), fill=_hex(color) + (255,))
    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(shadow)
    ds.ellipse((330, 790, 1070, 880), fill=(0, 0, 0, 120)); shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    Image.alpha_composite(shadow, big).save(path)


def screen(path, accent='#00C8BE'):
    """A believable dashboard screenshot mock (charts, KPIs, table)."""
    W, H = 1600, 1000
    im = Image.new('RGB', (W, H), (244, 247, 250)); d = ImageDraw.Draw(im)
    a = _hex(accent)
    d.rectangle((0, 0, 220, H), fill=(16, 32, 48))
    for i in range(7):
        d.rounded_rectangle((24, 110 + i * 64, 196, 150 + i * 64), 8, fill=(30, 52, 72) if i else a)
    d.text((24, 40), 'Dashboard', font=_font(30), fill=(255, 255, 255))
    for i, (k, v) in enumerate([('Units', '128'), ('Alerts', '7'), ('Uptime', '99.2%'), ('Score', '86')]):
        x = 260 + i * 330
        d.rounded_rectangle((x, 40, x + 300, 170), 14, fill=(255, 255, 255))
        d.text((x + 24, 62), k, font=_font(24, False), fill=(110, 120, 130))
        d.text((x + 24, 100), v, font=_font(48), fill=(20, 30, 40))
    d.rounded_rectangle((260, 200, 1100, 600), 14, fill=(255, 255, 255))
    rnd = random.Random(4); pts = []
    for i in range(30):
        pts.append((290 + i * 27, 520 - 200 * (0.5 + 0.35 * math.sin(i / 4) + 0.15 * rnd.random())))
    d.line(pts, fill=a, width=5)
    d.rounded_rectangle((1130, 200, 1570, 600), 14, fill=(255, 255, 255))
    for k, (ang0, ang1, col) in enumerate([(0, 210, a), (210, 300, (255, 196, 0)), (300, 360, (255, 80, 80))]):
        d.pieslice((1200, 250, 1500, 550), ang0 - 90, ang1 - 90, fill=col)
    d.ellipse((1280, 330, 1420, 470), fill=(255, 255, 255))
    d.rounded_rectangle((260, 630, 1570, 960), 14, fill=(255, 255, 255))
    for r in range(6):
        y = 660 + r * 50
        d.line((290, y + 40, 1540, y + 40), fill=(232, 236, 240), width=2)
        for c, w in enumerate([260, 380, 200, 300]):
            x = 290 + sum([260, 380, 200, 300][:c]) + c * 40
            d.rounded_rectangle((x, y + 8, x + w * (0.5 + 0.4 * rnd.random()), y + 26), 6, fill=(200, 208, 216) if r else (150, 160, 170))
    im.save(path, quality=92)


def avatar(path, k, accent='#00C8BE'):
    """Neutral placeholder silhouette (replace with real team photos, ideally background-removed PNGs)."""
    W, H = 800, 1000
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    shade = [(64, 84, 104), (72, 92, 112), (58, 78, 98), (68, 88, 108), (62, 82, 102)][k % 5]
    d.ellipse((140, 640, 660, 1320), fill=shade + (255,))           # shoulders
    d.ellipse((255, 230, 545, 560), fill=shade + (255,))            # head
    d.text((W / 2, 400), '?', font=_font(150), fill=(150, 170, 190, 160), anchor='mm')
    im.filter(ImageFilter.SMOOTH).save(path)


def background(path, seed=1, accent='#00C8BE'):
    """Abstract night-city bokeh (stands in for a b-roll still)."""
    W, H = 1920, 1080
    rnd = np.random.default_rng(seed)
    y = np.linspace(0, 1, H)[:, None]
    base = np.stack([8 + 20 * y, 18 + 30 * y, 30 + 40 * y], -1) * np.ones((1, W, 1))
    im = Image.fromarray(base.astype(np.uint8))
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    a = _hex(accent)
    for i in range(140):
        x, yy, r = rnd.uniform(0, W), rnd.uniform(H * 0.35, H), rnd.uniform(8, 60)
        col = [a, (255, 190, 90), (255, 240, 220), (255, 90, 70)][int(rnd.integers(0, 4))]
        d.ellipse((x - r, yy - r, x + r, yy + r), fill=col + (int(rnd.uniform(30, 110)),))
    lay = lay.filter(ImageFilter.GaussianBlur(14))
    im = Image.alpha_composite(im.convert('RGBA'), lay).convert('RGB')
    im.save(path, quality=90)


def clip(path, secs=8):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                    f'gradients=s=1920x1080:d={secs}:speed=0.015:c0=0x0a2236:c1=0x00c8be:c2=0x020d19:c3=0x203a55:n=4,format=yuv420p',
                    '-r', '25', '-c:v', 'libx264', '-crf', '22', str(path)], check=False)


def make_all(media_dir, brand=None, names=None):
    m = Path(media_dir); m.mkdir(parents=True, exist_ok=True)
    acc = (brand or {}).get('accent', '#00C8BE'); a2 = (brand or {}).get('accent2', '#FFE500')
    names = names or {}
    jobs = {'logo.png': lambda p: logo(p, names.get('product_name', 'BRAND'), acc),
            'partner_logo.png': lambda p: partner_logo(p, names.get('partner_name', 'PARTNER'), a2),
            'product.png': lambda p: product(p, acc, names.get('product_name', 'PRODUCT')), 'screen.jpg': lambda p: screen(p, acc),
            'clip_1.mp4': lambda p: clip(p)}
    for k in range(5):
        jobs[f'broll_{k + 1}.jpg'] = (lambda kk: (lambda p: background(p, 1 + 6 * kk, acc)))(k)
    for k in range(5):
        jobs[f'team_{k + 1}.png'] = (lambda kk: (lambda p: avatar(p, kk, acc)))(k)
    import hashlib, json
    reg_f = m / '.placeholders.json'
    reg = json.loads(reg_f.read_text()) if reg_f.exists() else {}
    for name, fn in jobs.items():
        p = m / name
        if not p.exists():
            fn(p)
            reg[name] = hashlib.md5(p.read_bytes()).hexdigest()
    reg_f.write_text(json.dumps(reg, indent=1))
    log(f'placeholder media in {m}/ (replace them with your real files; `plan` lists the ones still in use)')
