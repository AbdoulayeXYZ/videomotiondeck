# videomotiondeck

A Claude skill that turns a brief or a slide deck into a cinematic, jury-ready pitch film (60 s – 3 min):
founder-voice script, motion-design scenes rendered frame by frame, voice-over aligned automatically,
original score, sound design, -14 LUFS mix and automatic QC. Includes a **custom film mode** for real-footage
films that follow a strict brand charter.

By **AbdoulayeXYZ** (Abdoulaye NIASSE) — built from real pitch films (AI-Karangué × Oh Garage hackathon,
ADEPME Impact PME Innovation).

## Install
- Claude (claude.ai / desktop / Cowork): zip this folder and upload it in *Settings → Capabilities → Skills*,
  or use the packaged `videomotiondeck.skill` from the Releases page.
- Claude Code: copy the folder to `~/.claude/skills/videomotiondeck/`.

Then ask Claude for a pitch video. First run: `bash scripts/setup.sh` (ffmpeg, Chromium, FluidSynth, Whisper).

## Contents
`SKILL.md` (instructions) · `scripts/` (CLI `vmd.py` + engine) · `engine/` (scene library) · `custom/`
(bespoke film mode) · `templates/` · `references/` · `assets/fonts` (Montserrat, OFL).

## License
Code MIT (see `LICENSE.txt`); Montserrat under SIL OFL 1.1.
