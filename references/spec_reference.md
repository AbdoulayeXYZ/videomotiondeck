# project.json — complete reference

One file drives the whole film. Paths are relative to the folder of `project.json`.
Text fields accept light markup: `**accent**`, `__accent2__`, `!!alert!!`; the final `.`/`?`/`!` of a title is
coloured automatically. French typography (non-breaking space before `? ! : ; %`) is automatic.

## Top level

| key | default | |
|-----|---------|--|
| `title` | — | used for the export file name `exports/<Title>_vN.mp4` |
| `author` | — | written in the MP4 metadata |
| `language` | `fr` | Whisper language + UI words (`fr`, `en`, `es`, `pt`; others fall back to English UI) |
| `fps` | 25 | 25 is the norm for screens/projectors; 30 for US/social |
| `size` | [1920,1080] | the scenes are designed for 1920×1080 |
| `max_duration` | — | hard cap in seconds (QC fails above, `plan` budgets the script) |
| `end_hold` | 1.6 | seconds the last frame holds (music tail, fade of the audio only) |
| `output` | auto | force an output path (otherwise versioned, never overwrites) |
| `build_dir` | `build` | caches and intermediate files |
| `preroll` | 0.3 | scenes start 0.3 s into their entrance animation, so the first frame after a cut is never empty |
| `placeholders` | — | `{product_name, partner_name}` used by `vmd.py new` to draw placeholder logos (set by `--name/--partner`) |
| `brand` | AXIOM navy/teal | `bg bg2 accent accent2 alert text muted` (hex) and optional `font` (a font family installed on the machine; Montserrat is bundled and used by default) |
| `segments` | — | the timeline, in order (below) |
| `voice` | — | voice-over (below) |
| `music` | [] | score acts (below) |
| `sfx` | `{auto:true}` | sound design (below) |
| `mix` | | `loudness` (−14 LUFS), `music_lufs` (−23.5) |

## Segments

Common keys: `id` (unique, short), `type` (`scene` default | `clip` | `still` | `freeze`), `dur` (s),
`amb` (`road` `interior` `city` `room` `night`) + `amb_gain`, `elastic` (voice may stretch it; default true),
`tighten` (false = never trimmed), `tail`, `min_dur`, `voice_free` (true = intentional silence, e.g. team names),
`cut_sound` (false = no whoosh on the cut).

### `clip` — video footage
`src`, `in`, `out` (seconds in the source), `speed` (0.5 = slow motion), `grade` (`soft` default | `none`),
`extend` (true = may play past `out` if the voice needs time), `caption` (see caption scene).
Duration = (out − in) / speed. Trim `in`/`out` to avoid flashes, black frames or unwanted screens at the edges.

### `still` — photo with Ken Burns
`src`, `dur`, `zoom` [start,end] (default [1.08,1.0] = slow pull-out), `motion` (`push` | `breathe`),
`pan` [dx,dy] px, `focus` [x,y] 0–1 (point kept in frame), `caption`.

### `freeze` — hold a moment of an earlier segment
`of` (segment id, must be earlier), `at` (time inside it), `dur`, `zoom` (default [1.0,1.035] breathe).
Use it to extend a moment (e.g. the team) without a visible freeze.

### `scene` — motion design (`scene` + `data`)
Every opaque scene also accepts: `bg_image`, `bg_opacity` (0.28), `bg_blur`, `grid` (false hides the grid),
`camera` (slow push amount, 0.03 default, 0 = off), `camera_origin` (CSS, e.g. `"30% 50%"`).

| scene | use for | data |
|-------|---------|------|
| `title` | statement, act opener | `eyebrow`, `lines` [..] (or `title`), `sub`, `align` (`left`/`center`), `valign` (`bottom`), `size` (px), `width`, `y`, `start`, `dot` |
| `stat` | one number that hits | `eyebrow`, `value`, `from` (0), `prefix`, `suffix`, `decimals`, `caption`, `caption_size`, `source` (shown as "Source : …"), `color` (`accent`/`accent2`/`alert`/hex), `size`, `align`, `y`, `count` [t0,t1] or `count_dur` |
| `question` | the question of the film | `text` (markup spans words; ≤ 12 words reads best), `size` (76, shrinks automatically to fit `max_lines`), `max_lines` (2), `sub`, `start`, `words_dur`, `swell` (false = no reverse swell at the end) |
| `brief` | the challenge document → your answer | `eyebrow`, `title`, `subtitle`, `title_size`, `highlight_at`, `card` {`logo`, `header_color`, `tag`, `kicker`, `heading`, `body` with `[[highlighted quote]]`}, `answer` {`title`, `logo`, `at`, `stamp`} |
| `features` | product + 2–5 callouts | `eyebrow`, `title`, `title_size`, `image` (cut-out PNG), `items` [{`label`, `sub`}], `times` |
| `loop` | a virtuous cycle (value for the partner) | `eyebrow`, `lines`, `line_gap`, `center` {`logo` or `text`, `bg`}, `nodes` [{`title`, `sub`, `color`, `num`}] (3–5), `times` |
| `network` | hub & spokes (their clients, ecosystem) | `eyebrow`, `lines`, `hub` {`logo`/`text`, `bg`}, `items` [{`label`, `icon`, `color`}] (3–7), `badges` [{`text`, `color`}], `times`, `badge_times` |
| `steps` | roadmap / pilot / process | `eyebrow`, `title`, `steps` [{`key`, `title`, `lines` [..]}] (2–4), `times`, `line_times` |
| `trio` | three words, three images | `items` [{`image`, `eyebrow`, `word`}] ×3, `times` |
| `screen` | a screenshot in a browser frame | `image`, `eyebrow`, `title`, `side` (`right`/`left`), `tilt`, `focus`, `height`, `caption_y` |
| `team` | faces + names + roles | `eyebrow`, `members` [{`name`, `role`, `photo`, `focus` ("18%"), `bg`}] (2–6), `photo_top`, `start`, `stagger` |
| `logo` | the final card | `logo`, `partner_logo` (any aspect ratio: laid out in a centred row), `connector` ("×"), `name`, `tagline`, `final` ("Merci."), `final_at`, `final_size`, `start`, `row_top` |
| `caption` | (internal) text over clips/stills — set via a segment's `caption` | `eyebrow`, `lines`, `position` (`bl` bottom-left / `tl` top-left), `scrim` (false), `size` (96), `start`, `out` (exit time), `width` |

Icons for `network`: car, flag, building, truck, star, user, users, shield, wrench, chart, bolt, globe, phone, heart,
leaf, home, school, hospital, money, camera, cloud, check, pin.

Timing keys (`times`, `at`, `final_at`…) are seconds of the scene's own clock (≈ segment time + `preroll`). Prefer
voice sync (`reveal`) over hand-written `times`: it is computed for you from the recording.

## voice

```json
"voice": {"file": "voice/voixoff.mp3", "auto_fit": true, "tighten": true, "tail": 0.55, "room": 0.075, "wps": 2.9,
          "lines": [{"seg": "hook", "at": 0.8, "text": "…"}, {"text": "…", "reveal": 1, "gain": 1.0, "pause_before": 0}]}
```
Line keys: `text` (what is said), `seg` + `at` (cue: this line starts the segment at `at` s),
`reveal` (an item index to pop on this line — features items, loop nodes, network pills, steps, trio panels —
or a named moment: `"answer"` = the brief's answer appears, `"final"` = the logo's final word ("Merci."),
`"highlight"` = the brief quote lights up; `reveal_seg` targets another segment), `gain`, `pause_before`.
Tip: put "Merci." on its own line with `"reveal": "final"` so the word appears exactly when it is said.
Items without a `reveal` line keep their default timing, but never appear before an earlier item (+0.25 s).
Lines are numbered from **1** in the order of `voice.lines` (as in `build/voice_script_marked.md`); `after_line`
and `at_line` in sfx cues use that numbering.
The first line must have a `seg`.

## music — acts of the original score

```json
"music": [{"from": "hook", "to": "awa", "mood": "night"},
          {"from": "trio", "to": "impact", "mood": "tech", "drops": ["impact"]},
          {"from": "fin", "to": "fin", "mood": "resolve", "final_seg": "fin", "final_at": 0.3, "gain_db": 0}]
```
Moods (a D minor → D major journey): `night` (low cello + tremolo strings, dark and sparse), `reflective`
(piano + strings), `question` (suspended tremolo, holds the breath), `tension` (pad Dm → Asus → A, rising),
`hope` (major: piano, strings, soft choir), `tech` (electronic groove: bass pulse, kick/hat/snare, plucks, pumping
pad — `drops` = segments where the beat stops for impact), `epic` (ostinato, strings, choir, brass, timpani),
`resolve` (timpani roll, strings, choir, brass + celesta on the final chord at `final_seg` + `final_at`), `silence`.
Acts must cover the film in order; gaps are silent. `gain_db` per act (+3 default for reflective/hope).

## sfx — sound design

`auto: true` (default) creates sounds from scene events: text in (whoosh), items (pops, rising pitch),
counters (ticks), stats (hit), brief (scan, pop, whoosh), team (swooshes), logo (reverse swell + sting),
question (reverse swell to the cut), type changes clip↔scene (whoosh).

Manual cues: `{"seg": "x", "at": 1.2, "type": "alarm", "gain": 1.0}` or anchored to the voice (best — never on top
of a word): `{"after_line": 12, "type": "alert", "offset": 0.15}` / `{"at_line": 5, "type": "hit"}`.

Types: `hit` (opt. `shimmer`, `braam`), `impact`, `braam`, `whoosh`, `swoosh`, `riser` (ends at the time, `dur`),
`reverse_swell` (`dur`), `alert` (`n`, `f`), `alarm`, `chime`, `notif`, `heartbeat` (`count`, `dur`), `counter`
(`dur`, `n`), `tinnitus`, `engine`, `screech`, `tyre`, `rumble`, `horn`, `moto`, `wrench`, `clank`, `snap`,
`shutter`, `servo`, `scan`, `data`, `glitch`, `shimmer`, `pop` (`f`), `tick`, `sting`.

## mix
`loudness` −14 (YouTube/LinkedIn/projection), −16 for podcasts/Apple, −23 for broadcast (EBU R128).
`music_lufs` −23.5 default; −25 if the voice feels crowded, −22 for a more cinematic bed.

## Files written in build/
`timeline_extra.json` (voice fit), `sync.json` (reveals), `placed.json` + `voice_report.md`, `events.json`,
`frames/<id>/` (cached), `segs/` (cached), `picture.mp4`, `music/`, `sfx.npy`, `master.wav`, `mix_report.json`,
`qc/report.md` + `qc/sheet_XX.jpg`, `last_export.json`.
