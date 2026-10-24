# Script writing — a founder's voice, not a narrator describing the screen

## The one mistake to avoid

Do **not** describe what the viewer is watching ("Here we see the dashboard showing…"). The picture already says it.
The voice is the founder telling a story with conviction; the picture illustrates and punctuates it.
(The first AI-Karangué script was rejected by its author for exactly this reason.)

## Word budget

```
spoken seconds ≈ words / 2.9 × 1.12          (ElevenLabs pace, +12 % natural pauses)
human recording ≈ words / 2.3 × 1.12
voice room     = max_duration − end_hold − voice-free segments (team names…)
```
`vmd.py plan` prints the budget. For 3:00 with a 11 s team scene: ≈ 165 s of voice → **≈ 420 words max**.
Aim for 85–90 % of the max: silence between ideas is part of the music.
If over budget, **cut words, not scenes**: delete adjectives, merge sentences, keep verbs and numbers.

## Rhetoric toolbox (use 3–4 per film, not all)

| Figure | Example (from real scripts) |
|--------|-----------------------------|
| **Anaphora** (same start) | « Vos garages installent. Vos techniciens entretiennent. Vos clients roulent. » |
| **Epiphora** (same end) | « Le chauffeur, réveillé. Le gestionnaire, alerté. Le passager, rassuré. » (parallel endings) |
| **Triad** | « Distraction, téléphone, fatigue. Rien ne lui échappe. » |
| **Antithesis** | « Elle ne surveille pas Moussa. Elle veille sur lui. » |
| **Callback** | opening question « Qui veille sur Moussa ? » → ending « Désormais, nous. » |
| **Concrete time/place** | « Il est 3 h du matin, quelque part à Dakar. » |
| **Short punch after long** | « …une intelligence embarquée qui réagit seule, même sans réseau. Seule. » |
| **Direct address** | « Et vous, leur fidélité. » |

Sentence length: mostly 4–12 words. One long sentence per act, maximum. Read it aloud: if you run out of breath, cut.

## Writing for text-to-speech (ElevenLabs)

- Write numbers the way they must be said when ambiguous: « 745 » is fine, « 3h » → « trois heures »,
  « 27 % » → « vingt-sept pour cent » if the voice stumbles. Dates: « en 2026 » fine.
- Brand names: write them phonetically **in the voice script only** if mispronounced
  (e.g. « AI-Karangué » → « A.I. Karangué » or « Aï Karangué »). Keep the real spelling on screen.
- Punctuation is direction: comma = short breath, period = pause, « … » = suspense, « : » = reveal.
- Avoid parentheses, slashes, abbreviations, emojis, bullet points.
- One paragraph per segment: the exported `voice_script.txt` already separates them with blank lines.

## Marking the script in project.json

(The `//` comments below are explanations only — real JSON has no comments.)

```jsonc
"lines": [
  {"seg": "hook", "at": 0.8, "text": "Il est trois heures du matin, quelque part à Dakar."},
  {"text": "Il suffit de quatre secondes."},                         // no seg = follows naturally
  {"seg": "capteur", "at": 0.3, "reveal": 0, "text": "Un œil sur la route,"},  // item 0 pops on this line
  {"reveal": 1, "text": "un œil sur le conducteur,"},
  {"seg": "fin", "at": 0.4, "gain": 1.15, "text": "Désormais, nous. Merci."}
]
```
- Put a `seg` cue on the **first line of every segment that should start on that line** (= the cut).
- Lines without `seg` keep the natural rhythm of the recording.
- `reveal: k` makes item/node/step *k* of the segment appear exactly when the line starts (features, loop,
  network, steps, trio). `reveal: "answer"` shows the brief's answer on « Voici notre réponse », `reveal: "final"`
  shows « Merci. » when it is said (give it its own line). That sync is what makes motion design feel "edited",
  not "animated".
- The text must match what is said (the aligner compares words with Whisper). Fix the script if the voice
  improvised.

## The 7-act script skeleton (≈ 380–420 words for 3:00)

1. **Cold open** (20–30 words): time + place + image. « Il est… quelque part à… »
2. **Stakes** (30–45 words): the brutal fact, one sourced number, the hidden cause.
3. **Human** (25–40 words): a name, a job, a detail, someone waiting at home.
4. **Question** (8–12 words): « Alors, cette nuit-là, qui veille sur … ? »
5. **Brief + answer** (30–40 words): « Cette question, c'est [Partenaire] qui nous l'a posée. Défi n°… : … Voici notre réponse : [Produit]. »
6. **How + proof** (90–120 words): three benefits (triad), how it reacts, the platform, 1–2 numbers.
7. **Why you + proposal** (90–120 words): their clients by name, their teams, their gain (« et vous, leur fidélité »),
   the virtuous loop back to them, the pilot « Sur vos véhicules, dans vos garages, avec vos équipes. Vous testez,
   vous validez. Puis nous déployons, ensemble. »
8. **Close** (10–15 words): the callback answer + « Merci. »

## Tone checks before sending the script to the voice

- [ ] Could a jury member repeat the product's promise in one sentence after one viewing?
- [ ] Is the brief owner named, and is act 7 about *them*?
- [ ] Zero sentence that describes the screen?
- [ ] Zero sentence said twice in different words?
- [ ] Every number true and sourced (on screen)?
- [ ] Under budget (`plan`)?

## Bonus — the 1-minute live oral pitch (after the video)

Juries often give one minute on stage after the film. Formula (≈ 140 words):
1. Callback to the film's question (1 line).
2. What the partner told you they expect (2 lines) — show you listened.
3. The partnership in one anaphora: « Vos garages pour installer. Vos techniciens pour entretenir. Votre réseau pour
   déployer. Notre intelligence pour veiller. »
4. The low-risk ask: a pilot on their assets, to dissipate remaining doubts — then joint commercialisation.
5. The close: « Vous nous avez posé une question. Nous vous apportons une réponse. Faisons-la rouler ensemble. »
Short sentences, pauses after each anaphora, eyes on the decision-maker.
