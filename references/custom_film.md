# Custom film mode — bespoke motion design over real footage

Use it when the scene catalogue is not enough: a film that must open on real footage (a mine at night, a road,
a factory), insert real product footage *inside* the user's software, reuse sequences from a previous film, or
follow a strict brand charter shot by shot. Everything lives in one HTML page (`custom/film.html`) whose
`window.render(t)` draws any instant; Chromium renders it frame by frame.

Built from the ADEPME "Impact PME Innovation" film (mining, 3:00), rebuilt after this feedback from its owner:
"too much text, not enough animated graphics", "yellow is not in our charter", "you say 4 a.m. but the footage is
daylight", "show what the platform really does, with real footage inside it", "at least 3 minutes", "the team must
be exactly the one from the other film". Each rule below answers one of those.

## Workflow

```bash
cp -r <skill>/custom my_film && cd my_film            # film.html, timing.py, render_frames.py, audio_mix.py
VMD voice project.json                                 # or any Whisper pass -> chunks.json [[start,end,text],...]
python3 timing.py chunks.json --after="-1:4.2,7:2.2,21:8,40:20" --voice-end 127.1 --end 4 \
        --write-voice voice.mp3 voice_track.wav        # pauses inserted after phrases -> timing.json + voice on the film clock
# footage -> frame folders (grade here, once):
ffmpeg -ss 12 -i clip.mp4 -t 4 -an -q:v 3 -start_number 1 footage/f%04d.jpg
python3 render_frames.py preview 3 18 33 47 72        # look at pv/*.jpg (contact sheet) before any full render
python3 render_frames.py full 2                        # ~13 fps on 2 cores: 3 min ≈ 6 min
python3 render_frames.py range 1800-2080               # re-render only what changed
python3 audio_mix.py scenes.json voice_track.wav       # score + sfx + -14 LUFS mix -> build/master.wav
ffmpeg -framerate 25 -i fr/f%05d.jpg -i build/master.wav -c:v libx264 -crf 18 -pix_fmt yuv420p \
       -c:a aac -b:a 256k -shortest -movflags +faststart film_v1.mp4
```
`P(i)` / `E(i)` in the page are the start/end of voice phrase *i* on the film clock: every scene start, caption and
counter is anchored to a phrase, so changing a pause never desyncs anything.

## Rules

1. **The brand charter is law.** Only the brand tokens in `:root`; no extra accent "for emphasis" (a single yellow
   highlight got the whole film rejected). Red only for danger/alerts. One typeface. The caption pattern of the
   reference film: small spaced kicker + short 800-weight headline ending with an accent-coloured period.
2. **One idea on screen at a time, as a graphic.** A headline of 1–4 words + a moving graphic (counter with a bar,
   dot grid, ring, map lighting up, route drawing, ladder). Never a sentence the voice is already saying, never cards
   with paragraphs, never emoji/stock icons ("icônes à deux balles"), never fake "AI" interfaces.
3. **Picture matches the words.** "4 a.m." needs night: grade daylight footage at extraction
   (`eq=brightness=-0.10:contrast=1.12:saturation=0.40:gamma=0.80,colorbalance=bs=.12:bm=.08,curves=…`) and darken
   the sky with a top gradient in the page. Check the first and last frames of every clip: stock clips often start on
   another shot (a taxi before the mine) — skip those frames.
4. **Show the real product, with real footage inside it.** Real screenshots of the user's platform in 3D panels
   (perspective, slow drift), the footage playing in a player window *on* the UI, then shrinking to
   picture-in-picture while the panels behind change (map → driver report). Highlight the real row/cell that matters.
5. **Reuse what already won.** If the user loved a previous film, extract its sequences (product reveal, platform
   montage, team) as frame folders and cut them in — video only, never its old voice — and copy its caption system.
   When the user says "exactly the same team", reuse that segment frame for frame.
6. **Hitting a minimum length without padding**: the voice is fixed, so add *designed* voice-free moments only —
   cold open (footage + sound), a product reveal, a platform montage (music-driven, cuts every 2–4 s), the team,
   a logo hold. Stay ≤ 20 s per voice-free stretch and keep a hard cap (e.g. 3:00) to the second.
7. **Fluid edit**: 0.28 s crossfades between graphic scenes, hard cuts on match cuts (lens zoom → face), every
   shot moves (push-in, drift), sound on every cut (whoosh/swoosh), hits on reveals, ticks on counters.
8. **QC**: 1 fps contact sheets of the encode, read every tile; black-frame, loudness (-14 LUFS, peak ≤ -1 dBTP)
   and voice-onset checks (each anchored phrase starts where the timing says).

## Delivery gotcha
Transfer bridges that cap file size: split (`split -b 19000000`), commit the parts, `cat` them on the target, then
verify with `ffmpeg -i f.mp4 -map 0 -c copy -f md5 -` (packet hash) rather than `md5sum` — some bridges insert a
content-credentials (C2PA `uuid`) box into MP4-looking files, which changes the file hash but not the media.
