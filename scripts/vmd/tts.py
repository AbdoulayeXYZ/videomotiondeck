"""Draft voice: an offline neural voice (Piper via sherpa-onnx) to hear and time the whole film BEFORE paying
for / recording the final voice. Good enough to validate rhythm and cuts; replace it with ElevenLabs or a real
voice for the final film (then just run `all --voice voice/voixoff.mp3`)."""
import os, shutil, subprocess, tarfile, urllib.request
from pathlib import Path
import numpy as np
from .common import log, die, CACHE, SR

BASE = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/'
DEFAULTS = {'fr': 'vits-piper-fr_FR-siwis-medium', 'en': 'vits-piper-en_US-amy-medium', 'es': 'vits-piper-es_ES-davefx-medium',
            'pt': 'vits-piper-pt_BR-faber-medium', 'de': 'vits-piper-de_DE-thorsten-medium', 'ar': 'vits-piper-ar_JO-kareem-medium'}


def ensure_model(name):
    d = CACHE / 'tts' / name
    if list(d.glob('*.onnx')):
        return d
    d.parent.mkdir(parents=True, exist_ok=True)
    tgz = d.parent / f'{name}.tar.bz2'
    log(f'downloading draft voice {name} (~65 MB, once)…')
    try:
        if shutil.which('curl'):
            subprocess.run(['curl', '-fsSL', '--retry', '3', '-o', str(tgz), BASE + name + '.tar.bz2'], check=True)
        else:
            urllib.request.urlretrieve(BASE + name + '.tar.bz2', tgz)
        with tarfile.open(tgz) as t:
            t.extractall(d.parent)
        tgz.unlink()
    except Exception as e:
        die(f'could not download the draft voice ({e}). Record or generate the voice yourself instead.')
    return d


def synth(pr, model=None, speed=None, out=None):
    try:
        import sherpa_onnx, soundfile as sf
    except ImportError:
        die('pip install sherpa-onnx soundfile')
    from .voice import lines_of
    name = model or DEFAULTS.get(pr.lang[:2], DEFAULTS['en'])
    d = ensure_model(name)
    onnx = [f for f in d.glob('*.onnx')][0]
    cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=str(onnx), tokens=str(d / 'tokens.txt'), data_dir=str(d / 'espeak-ng-data')),
        num_threads=max(1, min(4, os.cpu_count() or 2))))
    tts = sherpa_onnx.OfflineTts(cfg)
    lines = lines_of(pr)
    words = sum(len(l['text'].split()) for l in lines)
    target_wps = float(pr.spec.get('voice', {}).get('wps', 2.9))

    def render(sp):
        parts = []
        for i, l in enumerate(lines):
            a = tts.generate(l['text'], sid=0, speed=sp)
            y = np.asarray(a.samples, dtype=np.float32)
            if a.sample_rate != SR:
                import librosa
                y = librosa.resample(y, orig_sr=a.sample_rate, target_sr=SR)
            gap = 0.6 if (l.get('seg') and i) else 0.3
            parts += [np.zeros(int(gap * SR), np.float32), y]
        return np.concatenate(parts + [np.zeros(int(0.5 * SR), np.float32)])

    # pace-match the draft to the budget pace (voice.wps, ElevenLabs-like 2.9 w/s) so the timing is representative
    if speed:
        sp = speed; voice = render(sp)
    else:
        sp = 1.0
        for i in range(4):
            voice = render(sp)
            ratio = (target_wps / 1.12) / (words / (len(voice) / SR))   # plan's estimate includes +12 % pauses
            if abs(ratio - 1) < 0.04 or i == 3:
                break
            sp = max(0.8, min(1.6, sp * ratio))
    log(f'  draft pace {words / (len(voice) / SR):.2f} words/s (speed {sp:.2f}; target ≈{target_wps / 1.12:.2f} incl. pauses)')
    voice = voice / (np.abs(voice).max() + 1e-9) * 0.7
    out = Path(out) if out else pr.root / 'voice' / 'draft_voice.wav'
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out, voice, SR, subtype='PCM_16')
    log(f'draft voice ({name}) -> {out}  ({len(voice) / SR:.1f}s)')
    log('  model licence: see ' + str(d / 'MODEL_CARD') + ' — a draft for timing; use ElevenLabs or a real voice for the final film')
    return out
