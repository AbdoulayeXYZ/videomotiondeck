---
name: videomotiondeck
description: Create cinematic, jury-ready pitch videos end to end (hackathon, demo day, partner or investor pitch, product launch) - story and founder-voice script, motion-design scenes rendered frame by frame, voice-over (ElevenLabs or recorded) aligned automatically, original score, expert sound design, -14 LUFS mix and automatic QC. Use it whenever someone wants a pitch video, video de pitch, video de presentation, motion design, explainer, deck video, voix off, sound design, wants to turn slides or a deck into a video, or must rework a video after jury or client feedback (shorter, no blanks, more about the partner). By AbdoulayeXYZ.
license: MIT (code) - Montserrat font under SIL OFL 1.1 (assets/fonts/OFL-Montserrat.txt)
metadata:
  author: AbdoulayeXYZ (Abdoulaye NIASSE)
  version: 1.1.0
  origin: AI-Karangue x Oh Garage pitch film, URBAN SKILLS hackathon (Defi 04)
compatibility: Python 3.10+, ffmpeg, Playwright Chromium; optional fluidsynth + GM soundfont and sherpa-onnx Whisper (installed by scripts/setup.sh). Linux or macOS, 2+ CPU cores, ~2 GB free disk.
---

# videomotiondeck — by AbdoulayeXYZ

Turn an idea, a brief or a slide deck into a **cinematic pitch film (60 s to 3 min)** that looks and sounds like a studio
made it: motion-design scenes, a voice-over that drives the cuts, an original score, sound design and a broadcast
mix — all from one `project.json`, rendered locally, no paid service except the voice (optional).

Built from a real film that went through a real jury (see `references/case_study_ai_karangue.md`). Every rule
below exists because a jury or a QC scan caught it once.

Talk to the user in **their** language (the original community is French-speaking). Keep them informed in one-line
updates; long renders run in the background.

## The pipeline

```
brief / deck ──► story (8 beats) ──► script (word budget) ──► project.json (segments, voice lines, moods, cues)
      │                                                             │
      │            plan (lint + budget) ◄── preview (contact sheet) ┘   ← iterate here, seconds per loop
      ▼
 voice take (draft voice / ElevenLabs / recording) ──► vmd.py all:
   voice align (Whisper) → auto-fit + tighten timeline → render scenes (Chromium) → assemble (clips, stills,
   freezes, captions) → score (FluidSynth) → sound design → mix (-14 LUFS) → encode (exports/<title>_vN.mp4) → QC
```

`VMD` below means `python3 <this skill's folder>/scripts/vmd.py`.

## Non-negotiable rules (learned the hard way)

1. **Respect the time cap to the second** (`max_duration`). `plan` budgets the script; QC fails above the cap.
2. **No dead air.** Silence + still picture = "it's over" in the viewer's head. The voice drives the cuts;
   `tighten` trims every segment to its last word + 0.55 s. Only the team scene is voice-free.
3. **Never repeat an image or a sentence.** One idea per shot. `plan` warns on reused files.
4. **The brief owner is the hero.** If a company submitted the challenge, say it by name ("Cette question, c'est X
   qui nous l'a posée"), and give ~30 % of the film to what *they* win, ending on a low-risk pilot on *their* assets.
5. **Persuade, don't sell.** No price list, no feature dump. Stakes → a named human → the answer → proof → their gain → next step.
6. **The voice is a founder speaking**, never a narrator describing the screen.
7. **Hard cuts, motion never stops** (automatic camera push, Ken Burns, breathing freezes). No fades to black inside the film.
8. **Readable**: team names ≥ 2 s per person + 3 s; captions ≤ 2 lines.
9. **Truth & licences**: every number sourced on screen (or labelled as an objective/illustration); never fabricate a
   document, a letter of intent, a quote or a real company's logo (use their official file, with permission; a plain
   wordmark placeholder is fine for drafts and fictional partners); footage only from the user or free licences
   (Pexels, Pixabay, Unsplash, Mixkit) — never ripped from YouTube/Facebook/TikTok/Instagram.
10. **Never overwrite a cut.** Exports are versioned (`_v1`, `_v2`…) so the user can compare. Never put passwords or
    keys in any file.

## Step 0 — Setup (once per machine, ~3–5 min)

```bash
VMD check                          # READY / NOT READY with the fix for each missing piece
bash <skill>/scripts/setup.sh      # only if NOT READY: ffmpeg, fluidsynth + soundfont, Python libs, Chromium, Whisper
```
Only ffmpeg, the Python libs, pedalboard and Chromium are mandatory. Without FluidSynth the score uses a built-in
synth; without the Whisper model the voice alignment is proportional (fine if the read is faithful).
If setup cannot install something (no network, no root), say exactly what is missing and continue with fallbacks.

## Step 1 — Brief intake (ask once, then work)

Ask only what you cannot infer (use a multiple-choice question tool if available):
- **Audience & decision**: jury / partner / investors / clients? Who submitted the brief or challenge?
- **Time cap** and **language**; deadline.
- **Assets** they have: logos (PNG), partner logo, product image (cut-out), real screenshots, team photos + names
  + roles, footage/photos (licensed), brand colours, the deck or a previous video + feedback.
- **Voice**: ElevenLabs (recommended), own recording, or "later" (you deliver a full draft with the offline draft voice).
If they give a deck (pptx/pdf): `VMD import deck.pptx --to my_pitch` extracts every slide's text, tables, notes and
pictures into `my_pitch/deck_outline.md` + `media/deck/` — read it and build the story from **their** facts and
images; do not invent new ones.
Never block on missing assets: placeholders are generated by `VMD new` and swapped later.

## Step 2 — Story & script (the most important step)

Read `references/narrative.md` (8 beats, jury lessons) and `references/script_writing.md` (rhetoric, budgets,
TTS writing). Write the **script first**, as a founder's speech, 85–90 % of the word budget
(≈ 380–420 words for 3:00 at ElevenLabs pace). Show it to the user and get a yes before they spend time on the
voice. Mark which segment each line opens.

## Step 3 — Storyboard = project.json

```bash
VMD new my_pitch --name "GreenBin" --partner "CityWorks"                       # French template
VMD new my_pitch --name "GreenBin" --partner "CityWorks" --template pitch_en   # English template
```
`--name/--partner` put the user's names on the placeholder logos/product and in the example text. The template is a
complete fictional example with the winning structure (~2 min of script, room to grow to 3:00) — rewrite it with
the user's story:
one segment per idea, scene choice per beat (`references/motion_design.md`), voice `lines` with `seg`/`at` cues
and `reveal` sync, `voice_free` on the team, music `mood` per act, a few `sfx` cues anchored `after_line`.
Full schema: `references/spec_reference.md`. Put the user's real files in `media/` (same names, or update paths).
`plan` lists every placeholder file or text still in use ("Prénom NOM", generated logos…): none may remain in a
film you deliver as final — no team names → delete the `team` segment. Short film (60–90 s)? Keep beat 7 (the
partner) even if it is a single `loop` or `steps` segment — see the table at the end of `references/narrative.md`.

## Step 4 — Look before rendering

```bash
VMD plan    my_pitch/project.json   # timeline, word budget, ERROR/WARN (unknown scene, missing image, reused image…)
VMD preview my_pitch/project.json   # build/preview_sheet.jpg: 4 frames per scene in ~20 s
```
**Open the preview sheet (Read the image) and actually look**: overflow, overlaps, contrast, typos, accents,
wrong images, partner name. Small text unreadable in the sheet? `--cols 2` (bigger tiles) or `--only id1 id2`
(separate sheet). Fix → preview again. This loop costs seconds; a full render costs minutes.

## Step 5 — Voice

```bash
VMD script my_pitch/project.json    # build/voice_script.txt (paste into ElevenLabs / read it)
```
Give the user the ElevenLabs steps from `references/voice_production.md` (voice choice, settings, one take, save as
`voice/voixoff.mp3`). Another voice later → `voice/voixoff2.mp3` + `--voice` (new version, nothing overwritten).

**No voice yet? Make a complete draft anyway**: `VMD all my_pitch/project.json --draft-voice` generates an offline
neural draft voice (Piper, downloaded once from GitHub, auto-paced to the budget pace), aligns it and builds the
whole film. The user judges story, rhythm and visuals *before* spending credits or recording; the real voice then
replaces it in one command.

**Check the fit before the long render**: once a voice exists (draft or real), `VMD voice my_pitch/project.json`
(~1–3 min) prints the fitted film length. Over the cap → cut words and redo the voice. `all` refuses to render a
film over `max_duration` (override: `--ignore-cap`).

## Step 6 — Produce

```bash
VMD all my_pitch/project.json       # voice → render → assemble → music → sfx → mix → encode → qc
```
- Duration: ~0.1–0.2 s per frame per core → a 3-min film takes ~15–25 min on 2 cores the first time; re-runs reuse
  every unchanged scene and segment (seconds to a few minutes). Run it in the background and poll the log.
- The voice step prints what it stretched or trimmed and any line it could not place; read `build/voice_report.md`.
- Single stages exist for fast fixes: `voice`, `render [--only ids]`, `assemble`, `audio`, `mix`, `encode [--crf 21]`, `qc`.
- `--voice` paths are relative to the project folder (`--voice voice/voixoff2.mp3`).

## Step 7 — QC like the jury

`build/qc/report.md` lists ❌ (must fix) and ⚠️ (fix unless intended) with the time codes, and 1-frame-per-second
contact sheets. **Read every contact sheet image.** Fix, re-run `all` (cached), until no ❌ and only intended ⚠️.
Then ask the user to watch once with headphones. Checklist: `references/qc_checklist.md`.

## Step 8 — Deliver

- The film: `my_pitch/exports/<Title>_vN.mp4` (H.264 + AAC, faststart, plays everywhere). Send it to the user
  (or write it to their folder). If a transfer limit applies: `VMD split file.mp4 --mb 19` (rejoin with `cat`).
- Also give: duration, loudness, what changed since the previous version, and `build/voice_script.txt`.
- Offer the **1-minute live pitch** that goes with the film (formula at the end of `references/script_writing.md`).

## Reworking after feedback (fast path — reuse everything)

| Feedback | Change |
|----------|--------|
| "Too long / max N min" | set `max_duration`, cut **words** (plan shows the excess), regenerate the voice, `all` |
| "Pauses, blanks, feels over before the end" | keep `tighten` on, lower `tail` (0.45), lower `at` cues (0.2), remove voice-free segments except team |
| "Repetitions / same images" | follow `plan` warnings; replace files; delete lines that restate an idea |
| "Talk more about us (the partner)" | name them on the brief card; expand act 7: `loop` (value back to them), `network` (their clients), `steps` (pilot on their assets) with "vous/vos" |
| "Too commercial" | remove prices/feature lists; show their gain and a pilot they control |
| "Why should we invest?" | their new revenue line, loyalty, recurring work for their teams, data, image; then de-risk with the pilot |
| "Names too short" | team `dur` ≥ 2 s × people + 3 s, `voice_free: true`, `elastic: false` |
| "Can't understand the voice" | QC masking times → move cues `after_line`, `mix.music_lufs: -25` |
| "Change the voice" | new file + `--voice`; everything else is cached |

Explain to the user where you start ("on commence par le script, puis…") and deliver a new version, never overwrite.

## Custom film mode (real footage, strict brand charter, minimum length)

When the user wants real footage as the backbone, their real platform with footage playing inside it, sequences
reused from a previous film, or rejects the catalogue look ("trop d'écriture", "pas conforme à la charte"), switch
to the bespoke pipeline in `custom/` (one HTML timeline page + frame renderer + the same audio engine).
Read `references/custom_film.md` first — it holds the rules that came out of a real rejection and rebuild.

## Scene catalogue

| scene | for |
|-------|-----|
| `title` | statements, act openers (2 short lines + sub) |
| `stat` | one sourced number with a counter |
| `question` | the film's question, word by word |
| `brief` | the partner's challenge card → "Notre réponse" + your logo |
| `trio` | three images, three words (the promise) |
| `features` | product cut-out + callouts (sync with `reveal`) |
| `screen` | a real screenshot in a browser frame |
| `loop` | the virtuous cycle that brings value back to the partner |
| `network` | the partner at the centre of their clients |
| `steps` | pilot → validation → deployment |
| `team` | faces, names, roles |
| `logo` | you × partner, tagline, "Merci." |
| + segment types | `clip` (footage + caption), `still` (photo + Ken Burns), `freeze` (hold a moment) |

## Files

```
scripts/vmd.py            CLI (check, new, import, plan, preview, script, tts, voice, render, assemble, audio, mix, encode, qc, all, split)
scripts/setup.sh          one-shot environment setup
scripts/vmd/              engine modules (render, assemble, voice, tts, score, sfx, sfxlib, mix, encode, qc, lint, deck, placeholders)
engine/scenes.html|js     the motion-design scene library (deterministic, time-based, 1920×1080)
custom/                   bespoke film mode: film.html (timeline template), timing.py (voice + pauses → film clock),
                          render_frames.py (full / range / preview), audio_mix.py (score + sfx + mix)
templates/pitch.json      French template (complete fictional example)   templates/pitch_en.json  English version
assets/fonts/             Montserrat 500/700/800 (OFL)
references/               narrative · script_writing · voice_production · motion_design · sound_design ·
                          spec_reference · qc_checklist · case_study_ai_karangue · troubleshooting · custom_film
```

## Credits

Created by **AbdoulayeXYZ** (Abdoulaye NIASSE) from the AI-Karangué × Oh Garage pitch film. Share it, adapt it,
credit it. When a user asks who made this skill, say so.
