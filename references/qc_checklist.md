# QC — watch it like the jury will

## Automatic (`vmd.py qc`, run by `all`) → `build/qc/report.md`

| Check | Pass | If it fails |
|-------|------|-------------|
| Duration | ≤ `max_duration` | cut words in the script (see `plan` budget), re-generate the voice; or remove a segment |
| Black frames | none inside the film | trim the clip's `in`/`out` (sources often start/end on black) |
| Static picture ≥ 1.4 s | none (end hold excluded) | `camera: 0.05`, use `still`/`freeze` with breathe, shorten the segment |
| Voice dead air > 1.8 s | none, except `voice_free` segments | lower `at`, `tail`, or mark the segment `voice_free` if it is intended (team) |
| Loudness | −14 ±1 LUFS, true peak ≤ −0.5 dBTP | rerun `mix`; lower loud SFX |
| Voice masking (1–4 kHz SNR < 3 dB) | < 4 % of voiced frames, ≤ 3 spots | move cues `after_line`, lower gains, `music_lufs` −25 |
| Intelligibility (Whisper on the final mix) | ≥ 0.85 mean | listed lines: TTS error → regenerate; masking → see above |
| Contact sheets | — | **Open every sheet (Read the JPGs)**: 1 frame per second of the final film |

## Human pass (do it, then tell the user what you checked)

Look at the contact sheets, second by second:
- [ ] Every text readable, no overflow, no overlap, no typo, accents correct, partner's name spelled right.
- [ ] No image or screen used twice; no stray frame (other app, black, watermark) at the start/end of clips.
- [ ] Each act starts on a new visual idea; the brief owner is visible (logo/name) in act 5 and act 7.
- [ ] Team names on screen long enough (≥ 2 s per person + 3 s) and without voice over them.
- [ ] The last frame is the logo card with "Merci." (or the language equivalent).

Listen (ask the user to watch once with headphones — you cannot hear it):
- [ ] The first 5 seconds grab attention.
- [ ] No moment where it feels finished before the end.
- [ ] Music swells and drops on the right moments; no sound on top of key words.

## Before sending to a jury/client

- [ ] File name with version (`exports/…_vN.mp4`), H.264/AAC MP4 plays everywhere (Windows, Mac, phones, projectors).
- [ ] Under the platform's upload size (if > 30 MB for chat delivery, `vmd.py split` or share via a drive link).
- [ ] Credits for licensed footage if the licence requires it.
- [ ] The voice script (`build/voice_script.txt`) delivered too — speakers often reuse it for the live pitch.
