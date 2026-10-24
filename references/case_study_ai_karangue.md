# Case study — AI-Karangué × Oh Garage (the film this skill was built from)

**Context.** URBAN SKILLS hackathon, challenge "Défi 04 — drowsiness of ride-hailing (VTC) drivers after long
driving hours", submitted by **Oh Garage** (a network of garages in Dakar serving private fleets, State fleets,
embassies, transport companies and VIP customers). The team (5 people, led by Abdoulaye NIASSE — *AbdoulayeXYZ*)
proposed **AI-Karangué**: an AI dashcam (road camera + driver camera + on-board AI + 4G/GPS) connected to the
Karangué221 fleet platform. Deliverable: a pitch film shown to the jury, followed by a 1-minute live pitch.

## Iterations — what changed and why

| Version | Length | What happened |
|---------|--------|---------------|
| v1 | 4:45 | Cinematic film, first script written like a narrator describing the screen → rewritten as a founder's speech ("legendary pitch"): anaphora, callback question, a named driver (Moussa) and his daughter waiting at home. |
| v1 + voice | 2:52 voice | ElevenLabs voice, one take. Expert sound design added: score by acts, alarms, heartbeat, road ambiences, logo stings; QC found masking (alarm on "il sait", sting on "Merci") → cues moved after the words. |
| v2 | same cut | Second ElevenLabs voice for comparison — new file, new version, nothing overwritten. |
| v3 | 2:57 | **Jury feedback**: max 3 min · no end-of-slide pauses ("we thought it was over") · no repeated platform images · much more about Oh Garage, say they submitted the brief · less commercial · show why Oh Garage should invest · new voice script. Rebuilt in under an hour by reusing everything. |
| v4 | 3:04.7 | Team section +10 s so people can read the five names (cap raised to 3:05 by the user). |

## v4 timeline (beats → durations)

| Time | Segment(s) | Beat |
|------|-----------|------|
| 0:00–0:16 | cold open "Il est 3 h du matin, quelque part à Dakar… Il suffit de quatre secondes." | 1 |
| 0:16–0:41 | world → "un sur trois" → Sénégal (745 deaths/yr, sourced) → Dakar → the driver → the child | 2–3 |
| 0:41–0:45 | **"Qui veille sur Moussa ?"** | 4 |
| 0:45–0:54 | **the brief card: "Cette question, c'est Oh Garage qui nous l'a posée. Défi n°4…"** → "Voici notre réponse : AI-Karangué." | 5 |
| 0:54–1:05 | triad: le chauffeur réveillé · le gestionnaire alerté · le passager rassuré | 6 |
| 1:05–2:05 | dashcam features, voice alert, detections, manager alert, video proof, map, ADAS (collision, lane), harsh driving, "−27 % collisions", "−15 % fuel" — each a different visual, many 2.3–3.5 s | 6 |
| 2:05–2:35 | **Why Oh Garage** (19.6 s): measured driving → anticipated wear (brakes, tyres, engine) → maintenance alert before the breakdown → back to Oh Garage; their client network gains safety, and Oh Garage gains loyalty | 7 |
| 2:25–2:34 | "Vos garages installent. Vos techniciens entretiennent. Notre intelligence veille. De bout en bout, ensemble." | 7 |
| 2:34–2:45 | **the pilot**: "Sur vos véhicules, dans vos garages, avec vos équipes. Vous testez, vous validez. Puis nous déployons, ensemble." | 7 |
| 2:45–3:03 | logos (AI-Karangué × Oh Garage) → team (names held 10 s) | 8 |
| 3:03 | "Alors… qui veille sur Moussa ? Désormais, nous. Merci." | 8 |

The engine reproduces this structure with `title/stat/question/brief/trio/features/screen/loop/network/steps/team/logo`;
the template `templates/pitch.json` is the same skeleton on a fictional subject.

## What made it work

1. **The partner is the hero of the second half.** Their name on the brief card, their logo at the centre of the
   loop and of the network, "vous/vos" everywhere in act 7, and a pilot on *their* vehicles in *their* garages.
2. **A human with a name** (Moussa) and a callback question that the last line answers.
3. **The picture follows the voice** — every cut lands on a sentence, no silence at the end of segments.
4. **One idea per shot, never the same image twice.**
5. **Sound with intent**: dark night score → suspended question → tech groove with drops on the numbers → hope on
   the partnership → epic team → resolved final chord on the logo. Nothing over the key words.
6. **QC like a machine**: duration, black frames, loudness −14 LUFS, masking scan, Whisper re-listening the mix
   (≥ 0.97 similarity), contact sheets of every second.

## The 1-minute live pitch that followed (structure)

Callback question → what Oh Garage expects (garages for installation and maintenance, their client network) →
the technico-commercial partnership with Oh Garage as spearhead ("fer de lance") and first seller → the pilot on
their vehicles, installed in their garages, only to remove the last doubts → joint commercialisation → close.
