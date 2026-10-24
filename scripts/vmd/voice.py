"""Voice-over: export the script for TTS, then align a recorded/generated voice to the picture.

Pipeline: silence segmentation -> Whisper (sherpa-onnx) transcription per chunk -> word alignment with the
script lines -> each line that has a cue (segment + offset) starts exactly there, the rest keep their natural
spacing -> elastic segments are stretched until every line fits -> processed voice track."""
import json, re, unicodedata, difflib
from pathlib import Path
import numpy as np
from .common import log, die, run, CACHE, SR


# ------------------------------------------------------------------ script export
def lines_of(pr):
    v = pr.spec.get('voice', {})
    L = v.get('lines', [])
    if not L:
        die('project.json has no voice.lines — write the voice-over script first (see references/script_writing.md)')
    return L


def export_script(pr):
    L = lines_of(pr)
    tl = pr.timeline(); idx = pr.seg_index(tl)
    plain, marked, cur = [], [], None
    for i, l in enumerate(L):
        seg = l.get('seg')
        if seg and seg != cur:
            cur = seg
            plain.append('')
            r = idx.get(seg)
            marked.append(f"\n### [{seg}] {('@ %.1fs' % (r['t0'] + float(l.get('at', 0.3)))) if r else ''}")
        plain.append(l['text'])
        marked.append(f"{i + 1:>3}. {l['text']}")
    (pr.build / 'voice_script.txt').write_text('\n'.join(plain).strip() + '\n', encoding='utf-8')
    (pr.build / 'voice_script_marked.md').write_text('\n'.join(marked).strip() + '\n', encoding='utf-8')
    words = sum(len(l['text'].split()) for l in L)
    log(f'script: {len(L)} lines, {words} words (~{words / 2.9:.0f}s at ElevenLabs pace, ~{words / 2.3:.0f}s at a calm human pace)')
    log(f'  -> {pr.build / "voice_script.txt"} (paste into ElevenLabs / record it)')
    return pr.build / 'voice_script.txt'


# ------------------------------------------------------------------ audio helpers
def load_voice(path):
    import soundfile as sf
    tmp = Path(path).with_suffix('.vmd48.wav')
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-ac', '1', '-ar', str(SR), str(tmp)])
    x, sr = sf.read(tmp)
    return x.astype(np.float64)


def chunks_by_silence(x, min_sil=0.15, min_len=0.08):
    hop = int(0.01 * SR); n = len(x) // hop
    db = 20 * np.log10(np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1)) + 1e-12)
    floor, speech = np.percentile(db, 10), np.percentile(db, 90)
    thr = max(floor + 12, speech - 27)
    voiced = db > thr
    segs, i, start = [], 0, None
    while i < n:
        if voiced[i]:
            if start is None:
                start = i
            i += 1
        else:
            j = i
            while j < n and not voiced[j]:
                j += 1
            if start is not None and (j - i) >= int(min_sil * 100):
                segs.append((start / 100, i / 100)); start = None
            i = j
    if start is not None:
        segs.append((start / 100, n / 100))
    return [s for s in segs if s[1] - s[0] >= min_len], thr


# ------------------------------------------------------------------ ASR
def asr_model():
    for name in ('small', 'base', 'tiny'):
        d = CACHE / f'sherpa-onnx-whisper-{name}'
        enc = list(d.glob('*-encoder.int8.onnx')) or list(d.glob('*-encoder.onnx'))
        dec = list(d.glob('*-decoder.int8.onnx')) or list(d.glob('*-decoder.onnx'))
        tok = list(d.glob('*-tokens.txt'))
        if enc and dec and tok:
            return enc[0], dec[0], tok[0]
    return None


def transcribe(x, chunks, lang):
    m = asr_model()
    if m is None:
        log('  (no Whisper model in cache — falling back to proportional alignment; run scripts/setup.sh for best results)')
        return None
    try:
        import sherpa_onnx, librosa
    except ImportError:
        log('  (sherpa-onnx/librosa not installed — proportional alignment)')
        return None
    enc, dec, tok = m
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=str(enc), decoder=str(dec), tokens=str(tok), language=lang, task='transcribe', num_threads=2)
    x16 = librosa.resample(x, orig_sr=SR, target_sr=16000)
    out = []
    for a, b in chunks:
        s = rec.create_stream(); c = x16[max(0, int((a - 0.05) * 16000)):int((b + 0.05) * 16000)]
        s.accept_waveform(16000, np.concatenate([np.zeros(1600), c, np.zeros(1600)]).astype(np.float32))
        rec.decode_stream(s); out.append(s.result.text.strip())
    return out


def norm_tokens(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.findall(r'[a-z0-9]+', s)


def align(lines, chunks, texts):
    """Returns for every chunk: (line index, starts_line)."""
    n = len(chunks)
    if texts is None:
        # proportional fallback: characters of script vs speaking time
        chars = np.array([max(1, len(l['text'])) for l in lines], float)
        starts = np.concatenate([[0], np.cumsum(chars)[:-1]]) / chars.sum()
        sp = np.array([b - a for a, b in chunks]); tot = sp.sum()
        cum = np.concatenate([[0], np.cumsum(sp)[:-1]]) / tot
        res, last = [], -1
        for j in range(n):
            li = int(np.searchsorted(starts, cum[j] + 0.008, side='right') - 1)
            li = max(li, last); res.append((li, li != last)); last = li
        return res
    sw, si, sfirst = [], [], []
    for i, l in enumerate(lines):
        tk = norm_tokens(l['text'])
        for k, w in enumerate(tk):
            sw.append(w); si.append(i); sfirst.append(k == 0)
    cw, cj = [], []
    for j, t in enumerate(texts):
        for w in norm_tokens(t):
            cw.append(w); cj.append(j)
    sm = difflib.SequenceMatcher(None, sw, cw, autojunk=False)
    c2s = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            c2s[blk.b + k] = blk.a + k
    res, last = [], -1
    for j in range(n):
        ks = [k for k in range(len(cw)) if cj[k] == j and k in c2s]
        if ks:
            li = si[c2s[ks[0]]]
        else:
            li = max(last, 0)
        li = max(li, last if last >= 0 else 0)
        res.append((li, li != last)); last = li
    return res


# ------------------------------------------------------------------ placement
def place(pr, tl, lines, chunks, amap, min_gap=0.14):
    idx = pr.seg_index(tl)
    T, warn = [], []
    cue_of = {}
    for i, l in enumerate(lines):
        if l.get('seg'):
            if l['seg'] not in idx:
                die(f'voice line {i + 1} refers to unknown segment "{l["seg"]}"')
            cue_of[i] = idx[l['seg']]['t0'] + float(l.get('at', 0.3))
    for j, (a, b) in enumerate(chunks):
        li, st = amap[j]
        if st and li in cue_of:
            t = cue_of[li]
        elif j == 0:
            t = 0.5
        else:
            gap = chunks[j][0] - chunks[j - 1][1]
            t = T[-1][1] + gap + (float(lines[li].get('pause_before', 0)) if st else 0)
        if j > 0 and t < T[-1][1] + min_gap:
            warn.append((j, li, round(T[-1][1] + min_gap - t, 2)))
            t = T[-1][1] + min_gap + 0.01
        T.append((t, t + (b - a)))
    return T, warn


def owner_segments(tl, lines, amap, T):
    """Which segment 'owns' each chunk: the segment of its line's cue, inherited by following uncued lines."""
    own_line, cur = [], None
    for i, l in enumerate(lines):
        if l.get('seg'):
            cur = l['seg']
        own_line.append(cur)
    return [own_line[li] for li, _ in amap]


def fit_timeline(pr, lines, chunks, amap, vf=None, max_iter=40):
    """Grow elastic segments until every line sits on its own picture, then (tighten) trim dead air at the
    end of segments so the next idea starts right after the voice — no 'is it over?' pauses."""
    vcfg = pr.spec.get('voice', {})
    tighten = vcfg.get('tighten', True)
    tail = float(vcfg.get('tail', 0.55))
    extra = {}
    tol = 0.25
    for it in range(max_iter):
        tl = pr.timeline(extra); idx = pr.seg_index(tl)
        T, warn = place(pr, tl, lines, chunks, amap)
        owners = owner_segments(tl, lines, amap, T)
        changed = False
        # 1) a cue was pushed late -> the segment owning the previous chunk must grow
        for j, li, deficit in warn:
            sid = owners[j - 1] if j > 0 else None
            if sid and _elastic(idx[sid]):
                extra[sid] = extra.get(sid, 0) + deficit + 0.1; changed = True
        if changed:
            continue
        # 2) a segment's own voice runs past its end (into the next segment)
        last_end = {}
        for j, sid in enumerate(owners):
            if sid:
                last_end[sid] = max(last_end.get(sid, 0), T[j][1])
        for sid, e in last_end.items():
            r = idx[sid]
            limit = r['t1'] - tol
            if e > limit and _elastic(r):
                extra[sid] = extra.get(sid, 0) + (e - limit) + 0.05; changed = True
        if changed:
            continue
        # 3) tighten: the voice of a segment ends early and the picture just waits -> trim the slack
        if tighten:
            for k, r in enumerate(tl[:-1]):
                sid = r['id']
                if sid not in last_end or not _elastic(r) or r.get('tighten') is False:
                    continue
                slack = r['t1'] - (last_end[sid] + float(r.get('tail', tail)))
                cut = min(slack, r['dur'] - _min_dur(r))
                if cut > 0.3:
                    extra[sid] = extra.get(sid, 0) - cut; changed = True
                    break          # everything after shifts: re-place before trimming the next one
        if not changed:
            break
    ex = {k: round(v, 3) for k, v in extra.items() if abs(v) > 1e-3}
    pr.save_json('timeline_extra.json', {'key': pr.fit_key(vf), 'file': str(vf) if vf else None, 'extra': ex})
    return pr.timeline(ex), ex


_TIME_KEYS = ('at', 'final_at', 'times', 'start', 'count', 'highlight_at', 'badge_times', 'line_times')


def _min_dur(r):
    """Never trim a segment below its last explicitly timed animation (+1.2s) or 2s."""
    if 'min_dur' in r:
        return float(r['min_dur'])
    m = 2.0

    def walk(v, key=None):
        nonlocal m
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, k)
        elif isinstance(v, list):
            for x in v:
                walk(x, key)
        elif isinstance(v, (int, float)) and not isinstance(v, bool) and key in _TIME_KEYS:
            m = max(m, float(v) + 1.2)
    walk(r.get('data', {}))
    if r.get('caption'):
        walk(r['caption'])
    return m


def _elastic(r):
    if 'elastic' in r:
        return bool(r['elastic'])
    return r.get('type', 'scene') in ('scene', 'still', 'freeze', 'clip')


# ------------------------------------------------------------------ main entry
def align_voice(pr, voice_file=None):
    vcfg = pr.spec.get('voice', {})
    vf = pr.p(voice_file or vcfg.get('file'))
    if not vf or not vf.exists():
        die('voice file not found — set voice.file in project.json (mp3/wav from ElevenLabs or your recording)')
    lines = lines_of(pr)
    x = load_voice(vf)
    chunks, thr = chunks_by_silence(x)
    log(f'voice: {len(x) / SR:.1f}s, {len(chunks)} phrases (threshold {thr:.0f} dBFS)')
    words = sum(len(l['text'].split()) for l in lines)
    span = (chunks[-1][1] - chunks[0][0]) if chunks else len(x) / SR
    pr.save_json('voice_stats.json', {'file': vf.name, 'words': words, 'seconds': round(span, 2), 'wps': round(words / max(1.0, span), 3)})
    import hashlib
    key = hashlib.md5(vf.read_bytes() + json.dumps([[round(a, 3), round(b, 3)] for a, b in chunks]).encode() + pr.lang.encode()).hexdigest()
    cache = pr.load_json('asr_cache.json', {}) or {}
    if key in cache:
        texts = cache[key]; log('  transcription: cached')
    else:
        texts = transcribe(x, chunks, pr.lang)
        if texts:
            pr.save_json('asr_cache.json', {key: texts})
    amap = align(lines, chunks, texts)
    covered = sorted(set(li for li, _ in amap))
    missing = [i + 1 for i in range(len(lines)) if i not in covered]
    if missing:
        log(f'  ! script lines not found in the recording (check the TTS read everything): {missing[:20]}')
    if vcfg.get('auto_fit', True):
        tl, extra = fit_timeline(pr, lines, chunks, amap, vf)
        if extra:
            log('  voice fit (+ stretched / − tightened): ' + ', '.join(f'{k} {v:+.2f}s' for k, v in extra.items()))
    else:
        pr.save_json('timeline_extra.json', {'key': pr.fit_key(vf), 'file': str(vf), 'extra': {}}); tl = pr.timeline({})
    T, warn = place(pr, tl, lines, chunks, amap)
    idx = pr.seg_index(tl)
    for j, li, d in warn:
        log(f'  ! line {li + 1} pushed {d:.2f}s later than its cue (not enough room before it)')
    # build the track
    total = pr.total(tl)
    N = int(total * SR) + SR
    out = np.zeros(N)
    cuts = [0.0] + [(chunks[i][1] + chunks[i + 1][0]) / 2 for i in range(len(chunks) - 1)] + [len(x) / SR]
    placed = []
    for j, (a, b) in enumerate(chunks):
        ca, cb = cuts[j], cuts[j + 1]; lead = a - ca
        clip = x[int(ca * SR):int(cb * SR)].copy()
        f = int(0.006 * SR); clip[:f] *= np.linspace(0, 1, f); clip[-f:] *= np.linspace(1, 0, f)
        li = amap[j][0]
        clip *= float(lines[li].get('gain', 1.0))
        s0 = int((T[j][0] - lead) * SR)
        if s0 < 0:
            clip = clip[-s0:]; s0 = 0
        e0 = min(N, s0 + len(clip)); out[s0:e0] += clip[:e0 - s0]
        placed.append({'t0': round(T[j][0], 3), 't1': round(T[j][1], 3), 'line': li + 1, 'starts': amap[j][1],
                       'asr': texts[j] if texts else None, 'script': lines[li]['text']})
    from pedalboard import Pedalboard, HighpassFilter, LowShelfFilter, PeakFilter, HighShelfFilter, Compressor, Reverb, Gain
    vb = Pedalboard([HighpassFilter(85), LowShelfFilter(cutoff_frequency_hz=180, gain_db=1.5), PeakFilter(cutoff_frequency_hz=320, gain_db=-1.5, q=1.0),
                     PeakFilter(cutoff_frequency_hz=3200, gain_db=2.0, q=0.8), HighShelfFilter(cutoff_frequency_hz=9000, gain_db=1.5),
                     PeakFilter(cutoff_frequency_hz=6800, gain_db=-2.0, q=3.0), Compressor(threshold_db=-22, ratio=3, attack_ms=8, release_ms=120), Gain(3)])
    dry = vb(out.astype(np.float32)[None, :], SR)[0]
    rv = Pedalboard([Reverb(room_size=0.32, damping=0.6, wet_level=1.0, dry_level=0.0, width=0.9), HighpassFilter(300)])
    st = np.stack([dry, dry]); voice = st + float(vcfg.get('room', 0.075)) * rv(st.astype(np.float32), SR)
    import soundfile as sf
    sf.write(pr.build / 'voice_track.wav', voice.T[:int(total * SR)], SR, subtype='FLOAT')
    pr.save_json('placed.json', placed)
    # reveal sync: a line with "reveal": k makes item k of its segment appear when the line starts
    sync = {}
    owners = owner_segments(tl, lines, amap, T)
    for j, (li, st) in enumerate(amap):
        if st and 'reveal' in lines[li]:
            sid = lines[li].get('reveal_seg') or owners[j]
            if sid in idx:
                rv = lines[li]['reveal']
                key = rv if isinstance(rv, str) and not rv.isdigit() else str(int(rv))
                sync.setdefault(sid, {})[key] = round(T[j][0] - idx[sid]['t0'] - 0.1, 3)
    pr.save_json('sync.json', sync)
    if sync:
        log('  reveal sync: ' + ', '.join(f'{k}{sorted(v)}' for k, v in sync.items()))
    # report
    rep = ['# Voice placement', f'total picture: {total:.2f}s', '']
    for p in placed:
        seg = next((r['id'] for r in tl if r['t0'] <= p['t0'] < r['t1']), '?')
        rep.append(f"- {p['t0']:7.2f}–{p['t1']:7.2f}  [{seg}] L{p['line']}{'*' if p['starts'] else ' '} {p['asr'] or p['script'][:60]}")
    (pr.build / 'voice_report.md').write_text('\n'.join(rep), encoding='utf-8')
    log(f'voice track -> {pr.build / "voice_track.wav"}  (report: voice_report.md)')
    if pr.max_duration and total > float(pr.max_duration):
        log(f'  ! total {total:.1f}s exceeds max_duration {pr.max_duration}s — shorten segments or the script')
    return tl
