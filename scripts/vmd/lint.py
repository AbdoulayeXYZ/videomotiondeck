"""Project lint: references, missing files, reused images, leftovers from the template, time budget."""
SCENES = ['title', 'stat', 'question', 'brief', 'features', 'loop', 'network', 'steps', 'team', 'logo', 'trio', 'screen', 'caption']
IMG = ('.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif')


def _all_strings(v):
    out = []
    if isinstance(v, dict):
        for x in v.values():
            out += _all_strings(x)
    elif isinstance(v, list):
        for x in v:
            out += _all_strings(x)
    elif isinstance(v, str):
        out.append(v)
    return out


def lint(pr, tl):
    W = []
    ids = {r['id'] for r in tl}

    def walk_imgs(v, where):
        if isinstance(v, dict):
            for x in v.values():
                walk_imgs(x, where)
        elif isinstance(v, list):
            for x in v:
                walk_imgs(x, where)
        elif isinstance(v, str) and v.lower().endswith(IMG) and not v.startswith(('http', 'data:', 'file:')):
            if not pr.p(v).exists():
                W.append(f'ERROR {where}: image not found "{v}"')
    uses = {}

    def collect(v, sid):
        if isinstance(v, dict):
            for x in v.values():
                collect(x, sid)
        elif isinstance(v, list):
            for x in v:
                collect(x, sid)
        elif isinstance(v, str) and v.lower().endswith(IMG + ('.mp4', '.mov', '.m4v')) and 'logo' not in v.lower():
            uses.setdefault(v, set()).add(sid)
    for r in tl:
        collect({k: r.get(k) for k in ('src', 'data', 'caption')}, r['id'])
    for v, sids in uses.items():
        if len(sids) > 1:
            W.append(f'WARN "{v}" appears in {len(sids)} segments ({", ".join(sorted(sids))}) — a jury notices repeated images; use a different shot')
    for r in tl:
        if r.get('type', 'scene') == 'scene' and r['scene'] not in SCENES:
            W.append(f'ERROR {r["id"]}: unknown scene "{r["scene"]}" (use: {", ".join(SCENES)})')
        walk_imgs(r.get('data', {}), r['id']); walk_imgs(r.get('caption', {}), r['id'])
    from .score import MOODS
    for a in pr.spec.get('music', []):
        for k in ('from', 'to'):
            if a.get(k) not in ids:
                W.append(f'ERROR music: unknown segment "{a.get(k)}"')
        if a.get('mood') not in MOODS:
            W.append(f'ERROR music: unknown mood "{a.get("mood")}" (use: {", ".join(MOODS)})')
    for c in pr.spec.get('sfx', {}).get('cues', []):
        if 'after_line' in c or 'at_line' in c:
            if not 1 <= int(c.get('after_line', c.get('at_line'))) <= len(pr.spec.get('voice', {}).get('lines', [])):
                W.append(f'ERROR sfx cue: line {c.get("after_line", c.get("at_line"))} does not exist')
            continue
        if c.get('seg') not in ids:
            W.append(f'ERROR sfx cue: unknown segment "{c.get("seg")}"')
    lines = pr.spec.get('voice', {}).get('lines', [])
    for i, l in enumerate(lines):
        if l.get('seg') and l['seg'] not in ids:
            W.append(f'ERROR voice line {i + 1}: unknown segment "{l["seg"]}"')
    if lines and not lines[0].get('seg'):
        W.append('ERROR voice line 1 needs a "seg" cue')
    if lines:
        vcfg = pr.spec.get('voice', {})
        words = sum(len(l['text'].split()) for l in lines)
        stats = pr.load_json('voice_stats.json') or {}
        if stats.get('wps'):
            wps, pace = float(stats['wps']), f"measured on {stats.get('file', 'the last voice')}"
            spoken = words / wps
        else:
            wps, pace = float(vcfg.get('wps', 2.9)), 'estimated (no voice yet)'
            spoken = words / wps * 1.12          # + natural pauses
        cued = [l for l in lines if l.get('seg')]
        cuts = sum(float(l.get('at', 0.3)) for l in cued) + len({l['seg'] for l in cued}) * float(vcfg.get('tail', 0.55))
        free = sum(r['dur'] for r in tl if r.get('voice_free'))
        film = spoken + cuts + free + pr.end_hold
        print(f'voice: {len(lines)} lines, {words} words ≈ {spoken:.0f}s spoken at {wps:.2f} words/s ({pace})')
        print(f'estimated film ≈ {film:.0f}s = voice {spoken:.0f}s + cut breaths {cuts:.0f}s + voice-free {free:.0f}s + end {pr.end_hold:.1f}s'
              + (f'  (cap {pr.max_duration}s)' if pr.max_duration else ''))
        if pr.max_duration and film > float(pr.max_duration):
            over = film - float(pr.max_duration)
            W.append(f'WARN script too long by ≈{over:.0f}s → cut ≈{int(over * wps) + 1} words (cut words, not scenes)')
        elif pr.max_duration:
            print(f'room left ≈ {float(pr.max_duration) - film:.0f}s (≈{int((float(pr.max_duration) - film) * wps)} words)')
    # leftovers from the template
    ph = pr.root / 'media' / '.placeholders.json'
    if ph.exists():
        import hashlib, json as _j
        gen = _j.loads(ph.read_text())
        refs = set(_all_strings(pr.spec))
        left = [f for f, h in gen.items() if ('media/' + f) in refs and (pr.root / 'media' / f).exists()
                and hashlib.md5((pr.root / 'media' / f).read_bytes()).hexdigest() == h]
        if left:
            W.append(f'WARN still placeholder media: {", ".join(left)} — replace with real files before the final film')
    blob = ' '.join(_all_strings(pr.spec))
    for marker in ('Prénom NOM', 'First LAST', 'Lorem ipsum'):
        if marker in blob:
            W.append(f'WARN placeholder text "{marker}" still in project.json — fill it or remove that segment (no team info → drop the team segment)')
    if pr.max_duration and pr.total(tl) > float(pr.max_duration):
        W.append(f'WARN timeline {pr.total(tl):.1f}s > max_duration {pr.max_duration}s')
    vf = pr.spec.get('voice', {}).get('file')
    if lines and vf and not pr.p(vf).exists():
        W.append(f'INFO voice file "{vf}" not there yet -> run `script`, generate/record it, save it there, then `all`')
    return W
