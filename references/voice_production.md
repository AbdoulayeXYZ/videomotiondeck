# Voice production — ElevenLabs or your own voice

The voice is the spine of the film: the engine cuts the picture **to the voice**. Get one clean, complete take.

## 1. Export the script

```bash
python3 <skill>/scripts/vmd.py script my_pitch/project.json
```
→ `build/voice_script.txt` (one paragraph per segment, ready to paste) and `build/voice_script_marked.md`
(numbered lines with the segment each one opens — useful to review with the user).

## 2. Draft voice first (free, offline, 10 seconds)

```bash
python3 <skill>/scripts/vmd.py all my_pitch/project.json --draft-voice
```
Generates `voice/draft_voice.wav` with an offline Piper neural voice (sherpa-onnx; French = SIWIS, CC-BY 4.0;
English = Amy; also es/pt/de/ar — `--tts-model vits-piper-…` for others, `--speed 0.9` slower) and builds the full
film with it. Use it to validate the story, the timing and the visuals with the user. It sounds synthetic: for the
film you present, use ElevenLabs or a human voice — everything else stays cached.

## 2a. ElevenLabs (recommended — what the reference film used)

Give the user these steps (the UI evolves; names may differ slightly):
1. elevenlabs.io → **Text to Speech** (or Studio for long texts).
2. **Voice**: a warm, low, confident voice in the film's language (for French: a male or female "narration /
   storytelling" voice with a natural accent). Listen to 2–3 candidates on the first paragraph only.
3. **Model**: the most expressive multilingual model available. If it supports *audio tags* (e.g. Eleven v3),
   a few tags help: `[calm]`, `[serious]`, `[softly]`, `[pause]`, `[confident]` — one per paragraph at most.
   Do not leave tags that the model would read aloud: test first.
4. **Settings** (starting point): Stability ≈ 40–50 %, Similarity ≈ 75 %, Style ≈ 15–30 %, Speaker boost on,
   Speed 0.95–1.0. More stability = flatter; less = more emotion but more risk of glitches.
5. Paste the **whole script in one generation** if the plan allows (consistent tone); otherwise per act, same settings.
6. Listen once, fully. Regenerate only the paragraphs that are wrong (mispronounced name, wrong emphasis) — then
   download the full MP3.
7. Save it as `my_pitch/voice/voixoff.mp3`. A second voice → `voixoff2.mp3`; never overwrite the first.

## 2b. Recording your own voice

- Quiet, soft room (a wardrobe full of clothes is a great booth). Phone or USB mic 15–20 cm from the mouth,
  slightly off-axis. Airplane mode.
- Record WAV/M4A, peaks around −12 dBFS, one continuous take per act; leave 1 s of silence between paragraphs.
- Smile on the hopeful acts, slow down on the stakes, lower the voice on the question.
- Pace target: ~2.3 words/s. Set `"voice": {"wps": 2.3}` so `plan` budgets correctly.

## 3. Align and build

```bash
python3 <skill>/scripts/vmd.py voice my_pitch/project.json            # alignment only (fast check)
python3 <skill>/scripts/vmd.py all   my_pitch/project.json            # full film
python3 <skill>/scripts/vmd.py all   my_pitch/project.json --voice voice/voixoff2.mp3   # another voice → new version
```
What happens:
1. Silence detection splits the take into phrases (adaptive threshold).
2. Whisper (sherpa-onnx, offline) transcribes each phrase; the words are matched to your script lines.
   Without the model it falls back to proportional matching (works if the read is faithful).
3. Each line with a `seg` cue starts exactly at `segment start + at`; other phrases keep their natural spacing.
4. **auto_fit** grows any segment whose voice overflows; **tighten** trims dead air at the end of segments;
   clips stretch with gentle slow motion (≤ 30 %) then hold.
5. Voice chain: high-pass, warmth, presence, de-ess, compression, a touch of room (`voice.room`, default 0.075).

Read `build/voice_report.md`: every phrase with its time, segment, and what Whisper heard. Lines "not found" mean the
voice skipped or changed them → fix the script text or regenerate that paragraph.

## Options (`voice` in project.json)

| key | default | meaning |
|-----|---------|---------|
| `file` | — | path of the take (mp3/wav/m4a) |
| `auto_fit` | true | stretch segments so each line stays on its picture |
| `tighten` | true | trim the end of segments to last word + `tail` |
| `tail` | 0.55 | seconds kept after the last word of a segment (0.4 = punchier, 0.8 = calmer) |
| `room` | 0.075 | reverb amount on the voice (0 = dry) |
| `wps` | 2.9 | words per second used by `plan` for the budget |
| line `gain` | 1.0 | per-line level (e.g. 1.15 for the final "Merci") |
| line `pause_before` | 0 | extra silence before an uncued line |
| segment `tail` / `tighten: false` / `min_dur` | | per-segment overrides |
