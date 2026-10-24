#!/usr/bin/env python3
"""videomotiondeck — cinematic pitch-video engine, by AbdoulayeXYZ.

  python vmd.py check                        environment report (+ how to fix what is missing)
  python vmd.py new  my_pitch/ --name GreenBin --partner CityWorks [--template pitch_en]
                                             scaffold a project (project.json + placeholder media/ + voice/)
  python vmd.py import deck.pptx --to my_pitch/   extract a deck's text + pictures (pptx/pdf) -> deck_outline.md
  python vmd.py plan    my_pitch/project.json   timeline + lint + word budget (run after every edit)
  python vmd.py preview my_pitch/project.json   contact sheet of every scene (fast, look at it!)
  python vmd.py script  my_pitch/project.json   export the voice-over text for ElevenLabs / recording
  python vmd.py tts     my_pitch/project.json   offline DRAFT voice (Piper) to time the film before the real voice
  python vmd.py all     my_pitch/project.json --draft-voice     full draft film with the offline voice
  python vmd.py voice   my_pitch/project.json   align the recorded voice, auto-fit + tighten the timeline
  python vmd.py render | assemble | audio | mix | encode | qc   individual stages
  python vmd.py all     my_pitch/project.json   everything: voice -> render -> assemble -> audio -> mix -> encode -> qc
  python vmd.py split   exports/file.mp4 --mb 19   cut a big file for upload limits
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vmd.common import Project, log, die, SKILL_DIR, CACHE
from vmd.lint import lint, SCENES



# ------------------------------------------------------------------ check
def cmd_check():
    rows, critical = [], False

    def row(name, ok, fix, crit=False):
        nonlocal critical
        rows.append((('OK ' if ok else ('MISSING' if crit else 'optional')), name, '' if ok else fix))
        if crit and not ok:
            critical = True
    for mod, crit in [('numpy', 1), ('scipy', 1), ('PIL', 1), ('soundfile', 1), ('pyloudnorm', 1), ('playwright', 1),
                      ('numba', 0), ('librosa', 0), ('mido', 0), ('sherpa_onnx', 0)]:
        try:
            __import__(mod); ok = True
        except Exception:
            ok = False
        row(f'python: {mod}', ok, 'bash scripts/setup.sh', bool(crit))
    r = subprocess.run([sys.executable, '-c', 'import pedalboard,numpy as n;pedalboard.Pedalboard([pedalboard.Reverb()])(n.zeros((2,4800),dtype=n.float32),48000)'], capture_output=True)
    row('python: pedalboard (runs)', r.returncode == 0, 'pip install "pedalboard==0.9.17"  (newer builds can crash with "illegal instruction")', True)
    for b, crit, fix in [('ffmpeg', 1, 'apt-get install -y ffmpeg  |  brew install ffmpeg'), ('ffprobe', 1, 'comes with ffmpeg'),
                         ('fluidsynth', 0, 'apt-get install -y fluidsynth fluid-soundfont-gm  |  brew install fluid-synth (richer orchestra)')]:
        row(f'binary: {b}', shutil.which(b) is not None, fix, bool(crit))
    from vmd.score import find_soundfont
    sf2 = find_soundfont()
    row(f'soundfont: {Path(sf2).name if sf2 else "-"}', bool(sf2), 'apt-get install -y fluid-soundfont-gm  or set VMD_SOUNDFONT=/path/to/GM.sf2')
    from vmd.voice import asr_model
    m = asr_model()
    row(f'whisper model: {Path(m[0]).parent.name if m else "-"}', bool(m), 'bash scripts/setup.sh  (downloads sherpa-onnx Whisper from GitHub)')
    code = ("import asyncio,os\nfrom playwright.async_api import async_playwright\nasync def m():\n async with async_playwright() as p:\n"
            "  kw={'executable_path':os.environ['VMD_CHROMIUM']} if os.environ.get('VMD_CHROMIUM') else {}\n  b=await p.chromium.launch(**kw); await b.close()\nasyncio.run(m())")
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=90)
    row('chromium (playwright)', r.returncode == 0, 'python -m playwright install chromium   (or set VMD_CHROMIUM=/path/to/chrome)', True)
    fonts = list((SKILL_DIR / 'assets' / 'fonts').glob('*.ttf'))
    row(f'fonts ({len(fonts)})', len(fonts) >= 3, 'assets/fonts is incomplete — reinstall the skill', True)
    w = max(len(r[1]) for r in rows)
    for st, n, fix in rows:
        print(f'  {st:<8} {n:<{w}}  {fix}')
    print('\n  READY' if not critical else '\n  NOT READY — run: bash ' + str(SKILL_DIR / 'scripts' / 'setup.sh'))
    return 0 if not critical else 1


# ------------------------------------------------------------------ new
def cmd_new(target, template, name=None, partner=None):
    d = Path(target)
    if (d / 'project.json').exists():
        die(f'{d}/project.json already exists')
    d.mkdir(parents=True, exist_ok=True)
    for sub in ('media', 'voice', 'exports'):
        (d / sub).mkdir(exist_ok=True)
    src = SKILL_DIR / 'templates' / f'{template}.json'
    if not src.exists():
        die(f'unknown template {template} (have: {", ".join(p.stem for p in (SKILL_DIR / "templates").glob("*.json"))})')
    raw = src.read_text(encoding='utf-8')
    tpl = json.loads(raw).get('placeholders', {})
    if name and tpl.get('product_name'):          # the example story speaks about your names right away
        for w in {tpl['product_name'], tpl['product_name'].title()}:
            raw = re.sub(rf'\b{re.escape(w)}\b', name, raw)
    if partner and tpl.get('partner_name'):
        for w in {tpl['partner_name'], tpl['partner_name'].title()}:
            raw = re.sub(rf'\b{re.escape(w)}\b', partner, raw)
    spec = json.loads(raw)
    names = dict(tpl)
    if name:
        names['product_name'] = name
    if partner:
        names['partner_name'] = partner
    spec['placeholders'] = names
    (d / 'project.json').write_text(json.dumps(spec, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    from vmd.placeholders import make_all
    make_all(d / 'media', spec.get('brand'), names)
    log(f'new project in {d}/ — edit project.json, put images/videos in media/, the voice file in voice/')
    log(f'next: python {Path(__file__).name} plan {d}/project.json')


# ------------------------------------------------------------------ plan / lint
def cmd_plan(pr):
    tl = pr.timeline()
    ex = pr.load_json('timeline_extra.json', {}) or {}
    for r in tl:
        what = r.get('scene') if r.get('type', 'scene') == 'scene' else f"{r.get('type')}:{r.get('src', r.get('of', ''))}"
        adj = f'  ({ex[r["id"]]:+.2f}s voice fit)' if r['id'] in ex else ''
        print(f"{r['t0']:7.2f} – {r['t1']:7.2f}  {r['dur']:5.2f}s  {r['id']:<18} {what}{adj}")
    T = pr.total(tl)
    print(f'total {T:.2f}s ({int(T // 60)}:{T % 60:05.2f})' + (f'  / max {pr.max_duration}s' if pr.max_duration else ''))
    W = lint(pr, tl)
    for w in W:
        print(' ', w)
    if any(w.startswith('ERROR') for w in W):
        sys.exit(1)
    return tl


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description='videomotiondeck — cinematic pitch-video engine (by AbdoulayeXYZ)',
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument('command', choices=['check', 'new', 'import', 'plan', 'preview', 'script', 'tts', 'voice', 'render', 'assemble',
                                        'audio', 'mix', 'encode', 'qc', 'all', 'split'])
    ap.add_argument('target', nargs='?', help='project.json (or a folder for `new`, a file for `split`)')
    ap.add_argument('--only', nargs='*', help='segment ids (render/preview)')
    ap.add_argument('--workers', type=int)
    ap.add_argument('--force', action='store_true', help='ignore caches')
    ap.add_argument('--out', help='output file for encode/all (default: exports/<title>_vN.mp4, never overwrites)')
    ap.add_argument('--voice', help='voice file (overrides voice.file)')
    ap.add_argument('--template', default='pitch', help='template for `new` (pitch = French, pitch_en = English)')
    ap.add_argument('--name', help='`new`: your product/startup name (drawn on the placeholder logo + product)')
    ap.add_argument('--partner', help='`new`: the brief owner / partner name (placeholder partner logo)')
    ap.add_argument('--ignore-cap', action='store_true', help='`all`: build even if the voice-fitted film exceeds max_duration')
    ap.add_argument('--cols', type=int, default=4, help='`preview`: tiles per row (2 = bigger tiles, readable small text)')
    ap.add_argument('--mb', type=float, default=19)
    ap.add_argument('--to', help='project folder for `import`')
    ap.add_argument('--draft-voice', action='store_true', help='`all`: generate an offline draft voice (Piper) and use it')
    ap.add_argument('--tts-model', help='draft voice model, e.g. vits-piper-fr_FR-siwis-medium')
    ap.add_argument('--speed', type=float, help='draft voice speed (default: auto, matched to voice.wps)')
    ap.add_argument('--crf', type=int, default=18, help='encode quality (18 = visually lossless, 21 = smaller file)')
    ap.add_argument('--no-asr', action='store_true', help='skip the Whisper intelligibility check in qc')
    a = ap.parse_args()

    if a.command == 'check':
        sys.exit(cmd_check())
    if a.command == 'new':
        return cmd_new(a.target or 'my_pitch', a.template, a.name, a.partner)
    if a.command == 'import':
        from vmd.deck import import_deck
        return import_deck(a.target, a.to or '.')
    if a.command == 'split':
        from vmd.encode import split
        return split(a.target, a.mb)
    if not a.target:
        die('give the path to project.json')
    target = Path(a.target)
    if target.is_dir():
        target = target / 'project.json'
    pr = Project(target)
    t0 = time.time()

    if a.command == 'plan':
        cmd_plan(pr)
    elif a.command == 'preview':
        from vmd.render import preview
        out = preview(pr, pr.timeline(), only=a.only, cols=a.cols)
        log(f'preview sheet -> {out}  (open it and look at every tile)')
    elif a.command == 'script':
        from vmd.voice import export_script
        export_script(pr)
    elif a.command == 'tts':
        from vmd.tts import synth
        out = synth(pr, a.tts_model, a.speed)
        log(f'next: python {Path(__file__).name} all {target} --voice {out.relative_to(pr.root)}')
    elif a.command == 'voice':
        from vmd.voice import align_voice
        align_voice(pr, a.voice)
        cmd_plan(pr)
    elif a.command == 'render':
        from vmd.render import render_scenes
        render_scenes(pr, pr.timeline(), only=a.only, workers=a.workers, force=a.force)
    elif a.command == 'assemble':
        from vmd.assemble import build_picture
        build_picture(pr, pr.timeline(), force=a.force)
    elif a.command == 'audio':
        from vmd.score import compose
        from vmd.sfx import design
        tl = pr.timeline(); compose(pr, tl); design(pr, tl)
    elif a.command == 'mix':
        from vmd.mix import mixdown
        mixdown(pr, pr.timeline())
    elif a.command == 'encode':
        from vmd.encode import encode
        encode(pr, a.out, a.crf)
    elif a.command == 'qc':
        from vmd.qc import qc
        last = (pr.load_json('last_export.json') or {}).get('file')
        f = a.out or last
        if not f or not Path(f).exists():
            die('nothing to check — run encode first (or pass --out file.mp4)')
        qc(pr, f, asr=not a.no_asr)
    elif a.command == 'all':
        tl = cmd_plan(pr)
        if a.draft_voice:
            from vmd.tts import synth
            a.voice = str(synth(pr, a.tts_model, a.speed).relative_to(pr.root))
        vf = pr.p(a.voice or pr.spec.get('voice', {}).get('file'))
        if pr.spec.get('voice', {}).get('lines') and vf and vf.exists():
            from vmd.voice import align_voice
            log('— voice'); align_voice(pr, a.voice); tl = pr.timeline()
            T = pr.total(tl)
            if pr.max_duration and T > float(pr.max_duration) + 0.05 and not a.ignore_cap:
                st = pr.load_json('voice_stats.json') or {}
                over = T - float(pr.max_duration)
                die(f'the film fitted to this voice lasts {T:.1f}s > max_duration {pr.max_duration}s (+{over:.1f}s).\n'
                    f'  Cut ≈{int(over * float(st.get("wps", 2.9))) + 1} words from the script (longest acts first), regenerate the voice, run again.\n'
                    f'  (Rendering now would only produce a film the QC rejects. Use --ignore-cap to build it anyway.)')
        else:
            log('— no voice file: building picture, music and sound design only (run `script`, record, then `all` again)')
            for stale in ('voice_track.wav', 'timeline_extra.json', 'sync.json', 'placed.json'):
                if (pr.build / stale).exists():
                    (pr.build / stale).unlink()
            tl = pr.timeline()
        from vmd.render import render_scenes
        from vmd.assemble import build_picture
        from vmd.score import compose
        from vmd.sfx import design
        from vmd.mix import mixdown
        from vmd.encode import encode
        from vmd.qc import qc
        log('— render'); render_scenes(pr, tl, workers=a.workers, force=a.force)
        log('— assemble'); build_picture(pr, tl, force=a.force)
        log('— music'); compose(pr, tl)
        log('— sound design'); design(pr, tl)
        log('— mix'); mixdown(pr, tl)
        log('— encode'); out = encode(pr, a.out, a.crf)
        log('— qc'); res = qc(pr, out, asr=not a.no_asr)
        log(f'done in {time.time() - t0:.0f}s -> {out}')
        if res['fails']:
            sys.exit(2)
        return
    log(f'{a.command} done in {time.time() - t0:.1f}s')


if __name__ == '__main__':
    main()
