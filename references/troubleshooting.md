# Troubleshooting

| Symptom | Cause → fix |
|---------|-------------|
| `vmd.py check` says pedalboard MISSING / process dies with "illegal instruction" | recent pedalboard wheels use CPU instructions some VMs lack → `pip install "pedalboard==0.9.17"` (setup.sh does it) |
| `apt-get update` hangs or fails on a docker/third-party repo | setup.sh retries without `sources.list.d`; or move the broken `.list` file out temporarily |
| Never `pkill -f <pattern>` in an agent shell | it can match and kill your own shell; kill by PID |
| Chromium does not start | `python -m playwright install chromium` (+ `install-deps` on Linux) or `export VMD_CHROMIUM=/path/to/chrome`; in sandboxes with preinstalled Playwright check `PLAYWRIGHT_BROWSERS_PATH` |
| Whisper model download blocked (HuggingFace 403) | the model comes from **GitHub releases** (k2-fsa/sherpa-onnx `asr-models`); if GitHub is blocked too, alignment falls back to proportional timing — keep the script faithful to the voice |
| Fonts look wrong (Times-like) | assets/fonts missing → reinstall the skill; the engine waits for the fonts before layout |
| `image not found` | paths are relative to project.json; check case (`Logo.PNG` ≠ `logo.png`) |
| A scene shows stale content | caches key on data + duration + image mtimes; force with `--force`, or delete `build/frames/<id>` |
| "line N pushed X s later than its cue" | the previous segment cannot grow (`elastic: false` or a clip without footage) → allow it, set `extend: true` on the clip, or cut words |
| "script lines not found in the recording" | the voice skipped/changed text → regenerate that paragraph or edit the line text to what is said |
| Video longer than `max_duration` | `all` stops before rendering and says how many words to cut. Cut words (≈ 2.6 words per second of film), regenerate the voice; lower `tail` to 0.45; remove a non-essential segment. Never speed up the *final* voice (the draft voice is auto-paced already) |
| `plan` says the voice fit is outdated | you edited the script, cues, segment timings or the voice file since the last `voice` → run `voice` (or `all`) again |
| Voice feels late on cuts | lower the line's `at` (0.15–0.3) |
| Too fast / no breathing room | raise `tail` (0.7) on emotional segments only, or add `pause_before` on a line |
| A sound covers a word | anchor it with `after_line`; lower `gain` |
| Render is slow | ~0.1–0.2 s per frame per core; use `--only <ids>` while iterating, `preview` for looks; scenes are cached |
| File too big to send | re-encode smaller with `vmd.py encode project.json --crf 21` (default 18); for chat limits use `vmd.py split file --mb 19` (rejoin with `cat file.part* > file`) or a drive link |
| Disk full in a sandbox | delete `build/frames` and `build/segs` of old projects (they regenerate) |
| Draft voice download fails | the Piper voices come from GitHub releases (k2-fsa/sherpa-onnx `tts-models`); if blocked, record a quick phone draft instead |
| Draft voice mispronounces a name | write it phonetically in the line text for the draft only, or ignore — the final voice replaces it |
| Need a 9:16 / square version | not built in: render 16:9, then crop/pad with ffmpeg (`-vf "scale=-2:1920,crop=1080:1920"`) only for footage-heavy films; text layouts are designed for 16:9 |
