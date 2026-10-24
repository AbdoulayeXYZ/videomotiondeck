# Motion design — the visual language

The default look ("AXIOM") is a dark cinematic navy with one teal accent and one yellow secondary accent,
Montserrat 500/700/800, a drifting grid, a soft glow and a vignette. It reads well on projectors and phones and makes
any logo pop. Change `brand` to match the client — keep **one** accent for the story, the second for the partner.

## Picking the scene for each beat

| Beat | Best scenes | Avoid |
|------|-------------|-------|
| Cold open | `clip` + caption (real place, night, motion), `still` + caption | logos, titles with the product name |
| Stakes | `title` (2 short lines), `stat` with `source` | charts with many numbers |
| Human | `still`/`clip` of a person in context + caption (name, job) | stock-looking smiles |
| Question | `question` | anything else on screen |
| Brief → answer | `brief` (the partner's challenge card, then your logo) | inventing a document they did not write — quote their real brief |
| Solution | `trio` (3 promises), `features` (product cut-out + callouts) | more than 5 callouts |
| Platform | `screen` (one screenshot, one idea) | the same screenshot twice — capture different views |
| Proof | `stat` (one number per segment) | numbers without source |
| Partner value | `loop` (cycle back to them), `network` (their clients) | your own logo in the centre — put theirs |
| Proposal | `steps` (pilot → validation → deployment) | prices, contracts |
| Team | `team` (2–6 people, cut-out portraits) | group photo with tiny faces |
| Close | `logo` (you × partner, tagline, "Merci.") | a list of contacts on the last frame of a pitch film |

## Rhythm

- 3–6 s per idea; cuts land on the voice (automatic with `seg` cues). Never a segment longer than ~15 s without a
  new element appearing — split it or use `reveal` to pop items on the words.
- Hard cuts only inside the film (no dissolves, no dips to black). The whoosh on clip↔scene cuts is automatic.
- Motion never stops: every scene has a slow camera push (`camera`), stills have Ken Burns, freezes breathe.
- Reading time: on-screen text must stay ≥ words / 3 + 1 s. Team names: ≥ 2 s per person + 3 s.
- Leave the picture alone on the key sentence: do not pop 4 items while the voice says the line that matters.

## Assets — what to ask the user for, and how to prepare them

| Asset | Ideal | Preparation |
|-------|-------|-------------|
| Logos | PNG with transparency, light version for dark backgrounds | any aspect ratio (the final card lays logos out in a row); a white "inverse" logo works best on navy |
| Partner logo | their official file, with permission (they submitted the brief → usually fine) | yellow/white card via `hub.bg` / `center.bg` if it is dark-on-light |
| Product | cut-out PNG (no background), 3/4 view, ≥ 1400 px | remove background (rembg, Canva/Photoshop) |
| Screenshots | real product screens, 16:10, ≥ 1600 px, no personal data | blur names/plates; one idea per screenshot |
| Team | portrait photos, same framing, background removed (PNG) | `focus` ("18%") to keep faces in frame |
| Footage | own videos or free licences (Pexels, Pixabay, Unsplash, Mixkit) — credit when required | trim `in`/`out` to skip flashes and black frames |

Never download from YouTube/Facebook/TikTok/Instagram or use watermarked stock. Never use a third party's logo
without a relationship (no fake "partners"). Placeholders from `vmd.py new` are fine for drafts (`plan` lists the
ones still in use — none may remain in a final film). No team photos/names → remove the `team` segment.

Tools that help (if available in the session): background removal (`pip install rembg`), screenshots of a web
product with Playwright, image upscaling with PIL `LANCZOS` (do not upscale > 1.5×), a design tool connector
(e.g. Canva) for a missing logo — but never fabricate a partner's logo.

## Typography & markup

- Titles: 2 lines max, 2–5 words per line. Emphasis with `**accent**` on the one word that matters.
- `__accent2__` for the partner's world (their name, their gain). `!!alert!!` for danger words.
- Captions over footage: 1–2 lines, bottom-left, ≤ 30 characters per line.
- The final punctuation of titles is coloured automatically — end titles with "." for a confident tone.
- Long names shrink automatically to fit (team, nodes, pills) — still keep them short.

## Checking the look

`vmd.py preview` renders 4 frames per scene into one sheet in ~20 s. Open it (Read the JPG) and check:
text overflow or overlaps, unreadable contrast, wrong/blurry images, logos on the wrong background, typos,
French accents, the partner named correctly everywhere. Fix and re-preview before any full render.
