#!/usr/bin/env bash
# videomotiondeck — one-shot environment setup (Linux / macOS). Safe to re-run.
#   bash scripts/setup.sh            full setup (Whisper "small" model, ~360 MB)
#   VMD_WHISPER=base bash setup.sh   lighter model (~160 MB), slightly less precise alignment
#   VMD_NO_MODEL=1 bash setup.sh     skip the model (voice alignment falls back to proportional timing)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"
CACHE="${VMD_CACHE:-$HOME/.cache/videomotiondeck}"
MODEL="${VMD_WHISPER:-small}"
say() { printf '\n\033[1;36m[vmd setup]\033[0m %s\n' "$*"; }
SUDO=""; if [ "$(id -u)" != "0" ] && command -v sudo >/dev/null 2>&1; then SUDO="sudo"; fi

pipi() {  # pip install that works on PEP-668 systems too
  $PY -m pip install -q "$@" 2>/dev/null || $PY -m pip install -q --break-system-packages "$@" 2>/dev/null || $PY -m pip install -q --user "$@"
}

# ---------------------------------------------------------------- system packages
say "system packages (ffmpeg, fluidsynth, GM soundfont)"
if [ "$(uname)" = "Darwin" ]; then
  if command -v brew >/dev/null; then
    for p in ffmpeg fluid-synth poppler; do brew list $p >/dev/null 2>&1 || brew install $p; done
    # macOS: a GM soundfont is not shipped with fluid-synth -> download FluidR3_GM if missing
    if [ ! -f "$CACHE/FluidR3_GM.sf2" ] && ! ls /opt/homebrew/share/soundfonts/*.sf2 >/dev/null 2>&1; then
      mkdir -p "$CACHE"
      curl -fsSL -o "$CACHE/FluidR3_GM.sf2" "https://github.com/pianobooster/fluid-soundfont/releases/download/v3.1/FluidR3_GM.sf2" \
        || say "could not download a soundfont — the built-in synth will be used (still good)"
    fi
  else
    say "Homebrew not found: install ffmpeg yourself (https://ffmpeg.org) — fluidsynth is optional"
  fi
elif command -v apt-get >/dev/null; then
  need=""
  command -v ffmpeg >/dev/null || need="$need ffmpeg"
  command -v fluidsynth >/dev/null || need="$need fluidsynth"
  [ -f /usr/share/sounds/sf2/FluidR3_GM.sf2 ] || need="$need fluid-soundfont-gm"
  command -v pdftoppm >/dev/null || need="$need poppler-utils"
  if [ -n "$need" ]; then
    # a broken third-party repo (e.g. docker) must not block the install: retry without sources.list.d
    $SUDO timeout 180 apt-get update -qq >/dev/null 2>&1 || $SUDO timeout 180 apt-get update -qq -o Dir::Etc::sourceparts="$(mktemp -d)" >/dev/null 2>&1 || true
    DEBIAN_FRONTEND=noninteractive $SUDO timeout 600 apt-get install -y -qq $need >/dev/null 2>&1 \
      || say "apt could not install:$need — install them manually (only ffmpeg is mandatory)"
  fi
elif command -v dnf >/dev/null; then
  $SUDO dnf install -y ffmpeg fluidsynth fluid-soundfont-gm >/dev/null 2>&1 || say "install ffmpeg (+ fluidsynth) manually"
fi

# ---------------------------------------------------------------- python packages
say "python packages"
pipi numpy scipy pillow soundfile pyloudnorm numba mido librosa playwright sherpa-onnx python-pptx
# pedalboard: recent wheels can die with 'illegal instruction' on some CPUs -> pin a known-good build
if ! $PY -c "import pedalboard,numpy as n;pedalboard.Pedalboard([pedalboard.Reverb()])(n.zeros((2,4800),dtype=n.float32),48000)" >/dev/null 2>&1; then
  pipi "pedalboard==0.9.17"
  $PY -c "import pedalboard" >/dev/null 2>&1 || say "pedalboard failed to install — run: $PY -m pip install pedalboard==0.9.17"
fi

# ---------------------------------------------------------------- headless Chromium
say "headless Chromium (Playwright)"
if [ -n "${VMD_CHROMIUM:-}" ]; then echo "  using VMD_CHROMIUM=$VMD_CHROMIUM"
elif ! $PY - <<'EOF' >/dev/null 2>&1
import asyncio
from playwright.async_api import async_playwright
async def m():
    async with async_playwright() as p:
        b = await p.chromium.launch(); await b.close()
asyncio.run(m())
EOF
then
  $PY -m playwright install chromium >/dev/null 2>&1 || say "playwright could not download Chromium — set VMD_CHROMIUM=/path/to/chrome"
  if [ "$(uname)" != "Darwin" ]; then $SUDO $PY -m playwright install-deps chromium >/dev/null 2>&1 || true; fi
fi

# ---------------------------------------------------------------- Whisper (alignment + intelligibility QC)
if [ -z "${VMD_NO_MODEL:-}" ]; then
  say "Whisper model ($MODEL) -> $CACHE"
  mkdir -p "$CACHE"
  D="$CACHE/sherpa-onnx-whisper-$MODEL"
  if ls "$D"/*encoder*.onnx >/dev/null 2>&1; then echo "  already there"
  else
    URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-$MODEL.tar.bz2"
    if curl -fL --retry 3 -o "$CACHE/w.tar.bz2" "$URL"; then
      tar -xjf "$CACHE/w.tar.bz2" -C "$CACHE" && rm -f "$CACHE/w.tar.bz2"
      # keep only the int8 weights (4x smaller, same accuracy for our use)
      if ls "$D"/*encoder.int8.onnx >/dev/null 2>&1; then rm -f "$D/$MODEL-encoder.onnx" "$D/$MODEL-decoder.onnx"; fi
      rm -rf "$D/test_wavs"
    else
      say "model download failed (GitHub unreachable?) — alignment will use proportional timing"
    fi
  fi
fi

say "final check"
$PY "$HERE/vmd.py" check
