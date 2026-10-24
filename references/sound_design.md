# Sound design & mix — half of the emotion

Everything is generated: an original score (no licence issue, no copyright claim on YouTube), a procedural SFX
library (whooshes, hits, braams, risers, alarms, heartbeats, UI pops, engines, road ambiences…) and a mix to
platform loudness. You mostly choose **moods per act** and a few **manual cues**; the rest is automatic.

## Score: one mood per act

Typical journey for a pitch (3:00):

| Act | Mood | Why |
|-----|------|-----|
| Cold open → human | `night` | intimate, dark, lets the voice breathe |
| Question → brief | `question` | suspended, the film holds its breath before the answer |
| Solution → proof | `tech` + `drops` on the key stat/alert | energy, modernity; the drop makes a number land |
| Partner value → proposal | `hope` | major key, warm — the future together |
| Team | `epic` | the heroes |
| Close | `resolve` with `final_seg`/`final_at` on the logo | the final chord lands with the logo / "Merci" |

`gain_db` adjusts one act (+3 for hope/reflective by default). FluidSynth + a GM soundfont gives a real orchestra;
without it a built-in synthesizer is used (still clean, less rich) — `vmd.py check` tells which.

## Automatic sound design (`sfx.auto`)

| Event in the picture | Sound |
|---------------------|-------|
| text/scene enters | whoosh (soft for the question) |
| list items, nodes, pills | UI pops with rising pitch + tick |
| counter running | ticks, then a hit on the number |
| brief card | scan sweep, pop on the highlight, whoosh to the answer |
| team panels | fast swooshes |
| logo | reverse swell into a sting |
| question end | reverse swell into the cut |
| cut between clip/still and scene | whoosh |
| `amb` on a segment | road / interior / city / room / night ambience under the picture |

## Manual cues — rules that keep the voice intelligible

1. **Never put a sound on a key word.** Anchor dramatic sounds *after* the line: `{"after_line": 12, "type": "alarm"}`.
2. Stings, hits and alarms **between** sentences, not under them (the reference film moved its alarm after
   "il sait" and its logo stings after "Merci" because QC showed masking).
3. One big sound per act (impact, braam, alarm). Silence before a big moment makes it bigger (`drops`).
4. Ambiences low (they are auto-ducked); heartbeat only on the human/stakes act.
5. The last word ("Merci.") gets `gain: 1.15` and nothing on top of it.

## Mix (automatic)

- Voice: cleaned and compressed, peak-limited, −16.5 LUFS on its own.
- Music bed −23.5 LUFS (`mix.music_lufs`), SFX ×0.62, ambiences high-passed.
- **Ducking**: when the voice speaks, music −6 dB and an extra −6 dB in the 0.9–4.5 kHz speech band (the music keeps
  its body, the words stay clear); SFX −3/−5 dB; ambiences −4/−6 dB.
- Master: gentle glue compression, light shelves, true-peak limiter at −1.2 dBTP, integrated loudness −14 LUFS
  (`mix.loudness`), audio fade on the end hold.

## When the QC complains

| QC message | Fix |
|------------|-----|
| voice masked at t | find the cue near t → move it `after_line`, lower its `gain`, or lower `mix.music_lufs` to −25 |
| intelligibility < 0.85 | listen to the listed lines; if the TTS mispronounced, regenerate that paragraph; if masked, see above |
| loudness off target | rerun `mix` (it converges); check that no segment is silent for long |
| true peak > −0.5 | rerun `mix`; lower the loudest SFX `gain` |
