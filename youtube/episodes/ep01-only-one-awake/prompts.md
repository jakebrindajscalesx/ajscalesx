# AI voice and animation prompts

These work with any tool. Notes for common ones:
- **Voice:** ElevenLabs. Anything with voice design and `<break>` tags works the same way.
- **Images:** Midjourney, Flux, Ideogram, GPT image, Leonardo.
- **Image to video:** Runway, Kling, Luma, Pika, Veo.

The workflow: **design the voice → generate the character sheet → generate each shot's still → animate
each still → edit to the voiceover.**

---

## Part 1: The voice

### 1.1 Narrator voice design prompt

Paste this into a "design a voice from text" tool:

```
A warm, close, slightly hushed male narrator in his late 20s with a neutral American accent. Sounds
like he is telling a story to one person in a dark room late at night. Calm and intimate, with
controlled tension underneath; never shouty, never a movie-trailer voice. Clear diction, natural
pauses, a slight smile on the lighter lines. Recorded close to the microphone, dry studio sound, no
reverb.
```

If you want a female narrator, swap the first line for "A warm, close, slightly hushed female narrator in
her late 20s" and keep everything else.

### 1.2 Settings (ElevenLabs names; other tools have equivalents)

| Setting | Value | Why |
|---|---|---|
| Model | The most expressive multilingual model you have | Needed for the emotional range in the twist |
| Stability | 40–45% | Lower means more emotion. Below 35% it starts to wobble |
| Similarity | 75% | |
| Style exaggeration | 15–25% | Higher sounds like a trailer voice |
| Speed | 0.95 | The script is timed at 150 words per minute. 0.95 adds breathing room |

### 1.3 How to generate it

- Use **[voiceover.txt](voiceover.txt)**. It's already split into 12 clips, with `<break>` pauses and
  numbers spelled out ("three-twelve A M", "nine-one-one").
- **Generate one clip at a time, not the whole file.** Make 2–3 takes of each and pick the best. It's much
  easier to redo one clip than all 9 minutes.
- Name the files `vo-01.mp3` … `vo-12.mp3` so they line up with the shot list below.
- After the edit, export captions from the final timeline (or run Whisper on the full voiceover) as
  `final-voiceover.srt`. The chapter, edit and retention tools all use that file.

### 1.4 Delivery notes for each clip

Read each note before you generate that clip. Some tools let you put the note in brackets
before the text, like `[whispering, tense]`. Remove the note if the tool reads it out loud.

| Clip | Section | Delivery |
|---|---|---|
| 01 | Hook | Slow and quiet, almost a whisper on "Except you." Small pause before "and why you never should have tried." |
| 02 | The turn | Curious, a little amused. Speed up on "So here's what we're going to do". That's the promise. |
| 03 | The house | Getting more desperate: calm, then louder on "shout it", then flat and hollow on "Nothing." |
| 04 | The street | Hushed, eerie. Slight lift on "the dogs are awake". That's the first real mystery. |
| 05 | The sky | Slow, almost technical, then heavy on "every single one of them has a clock on it." Very quiet on "You don't watch the end." |
| 06 | The lights | Steady and explanatory, then pick up pace on "And that's when the real problem hits you". |
| 07 | The clock | Serious. Land "72 hours" and "20 of them are already gone" like a countdown. Gentle on "maybe you can save them." |
| 08 | The hospital | The one funny moment. A dry smile on "one very bad decision". Then tired and relieved by "Time." |
| 09 | The phone | Back to a whisper. Tight and close. A beat of silence before "This number is not in service." |
| 10 | Waking one | Tender on the song lines. Long pause before "His eyes open." |
| 11 | The twist | Slow and quiet, like the floor's dropping away. "They were never asleep. You were." gets a full stop and 1.5 seconds of silence. |
| 12 | Close | Hopeful and emotional on "You take his hand." Warmer and conversational for the comment question. |

### 1.5 The two other characters' lines

Generate these in separate voices and drop them in during the edit. In clips 10 and 11, the narrator stops just before each line.

**Brother**, clip 10. Voice prompt: *"A boy about 13 years old, sleepy, confused, a little
croaky, just woken up."*
```
Why are you here? <break time="0.4s" /> You're supposed to be the one in the bed.
```
The narrator's clip 10 already includes this line. Either cut the narrator's version in the edit, or keep both
for an echo effect: the brother says it, then the narrator repeats it quieter.

**Mom on the phone**, clip 09. Voice prompt: *"A woman in her 40s, crying quietly, speaking softly
and close to a phone."* Run the result through a phone-line or radio filter in your editor and add static.
```
Can you hear me? <break time="0.6s" /> Please. <break time="0.4s" /> It's been three days. <break time="0.8s" /> We're right here.
```
Keep it **mostly buried under the static** in clip 09. Viewers should only half-hear it. Play it clearly
in clip 11 during the flashback, when the twist shows it was real.

### 1.6 Music and sound effects (optional prompts for an AI music or SFX tool)

| Where | Prompt |
|---|---|
| Clips 01–04 | `Sparse ambient piano, single notes, a low sustained synth drone, eerie and quiet, 70 bpm, no drums` |
| Clips 05–07 | `Tense cinematic pulse, ticking clock rhythm, low strings building slowly, 90 bpm` |
| Clip 08 | `Light quirky pizzicato strings over a tense drone, slightly comedic but uneasy` |
| Clips 09–10 | `Near silence, distant radio static, a soft music-box melody` |
| Clip 11 | `Reversed piano, warped and dissolving, a low swelling string chord` |
| Clip 12 | `Hopeful emotional piano and strings swell, resolving to a warm major chord` |
| SFX | Fridge hum, distant car alarm, phone ringing (a lot), dog whining, a jet overhead, an electrical hum cutting out, hospital monitor beep, a phone hitting a tiled floor |

---

## Part 2: The visuals

### 2.1 Style prefix (paste this at the start of every image prompt)

```
2D digital animation still, clean bold outlines, flat cel shading with soft gradients, cinematic
widescreen composition, moody night palette of deep blues and teals with warm orange accent lighting,
expressive cartoon characters with large eyes, detailed painted backgrounds, high contrast,
16:9 aspect ratio
```

**Negative prompt** (for tools that support one):
```
photorealistic, 3D render, text, watermark, logo, extra fingers, deformed hands, blurry, gore, blood
```

> Use the same style prefix and the same character descriptions in every prompt. That matters most for
> consistency. If your tool supports **character reference / image reference**, upload the character
> sheet from 2.2 for every shot that includes the character.

### 2.2 Character sheet (generate these first)

**YOU (main character):**
```
[STYLE PREFIX] Character turnaround sheet, front, side and back views, of a 17-year-old with messy
dark brown hair, warm brown skin, large expressive eyes, wearing an oversized mustard-yellow hoodie,
grey sweatpants and white socks. Neutral pose, plain light-grey background, consistent proportions.
```

**BROTHER:**
```
[STYLE PREFIX] Character turnaround sheet of a 13-year-old boy with short curly black hair, warm brown
skin, red-and-white striped pajama shirt, navy pajama pants. Plain light-grey background.
```

**MOM:**
```
[STYLE PREFIX] Character turnaround sheet of a woman in her mid 40s with shoulder-length curly black
hair, warm brown skin, light blue bathrobe over a white t-shirt. Plain light-grey background.
```

Pick the best result for each character and save it. **Reuse those exact images as references for
the whole video.** The mustard hoodie is the main thing that identifies "you" in every frame, including the thumbnail.

### 2.3 Shot list

Each shot has an **image** prompt (always add the style prefix) and a **motion** prompt for the image-to-video
tool. Generate 5-second clips and trim them in the edit. Shots marked ⭐ are the most important. Spend
extra takes on those.

#### Clip 01: Hook (0:00–0:14)

| # | Image | Motion |
|---|---|---|
| 1 ⭐ | Extreme close-up of a red digital alarm clock reading 3:12 in a pitch-black bedroom, the red glow the only light | The last digit flips from 1 to 2, then a slow push-in on the glowing numbers |
| 2 | Wide shot of a modern city at night, all apartment windows lit, the streets empty, no people anywhere, perfectly still | Very slow aerial drift forward over the rooftops |
| 3 | The main character in the mustard hoodie, alone in the middle of an empty city street at night, small in the frame, looking up | Slow pull-back that makes the character smaller and smaller |

#### Clip 02: The turn (0:14–0:50)

| # | Image | Motion |
|---|---|---|
| 4 | Dark bedroom, the main character sitting up in bed, rubbing their eyes, lit by the red alarm clock | Character stretches and swings their legs out of bed |
| 5 | Kitchen at night lit by the open fridge, the main character pouring a glass of water at the sink | Water pours into the glass. Fridge light flickers slightly |
| 6 | Over-the-shoulder view from the kitchen window: neighbor's window across the street with a TV glowing, a figure slumped on a couch | Slow push-in toward the neighbor's window |
| 7 | Title card style: large bold white text "HOUR 0" on a dark blue background with a faint clock icon | Text fades in with a subtle glitch. *(Easier to make this in your editor)* |

#### Clip 03: The house (0:50–1:43)

| # | Image | Motion |
|---|---|---|
| 8 | Hallway at night, the main character opening a bedroom door, light spilling in on the younger brother asleep in bed | Door swings open slowly |
| 9 ⭐ | Close-up of the brother asleep, peaceful, eyes visibly moving under closed eyelids, the main character's hands shaking his shoulders | Hands shake him. His head rocks but his face stays peaceful |
| 10 | Parents' bedroom, mom asleep on her side with a glowing phone still in her hand, the main character standing over her with a glass of water | Character tips the water toward her face; she doesn't react |
| 11 | The main character sitting on the kitchen floor against the cupboards, phone to ear, phone screen reading "Calling 911…" | Character's knee bounces nervously, phone screen pulses |
| 12 | An emergency dispatch center, rows of desks with glowing screens and ringing phones, every operator asleep at their desk | Slow pan across the desks, phone lights blinking |

#### Clip 04: The street (1:43–2:21)

| # | Image | Motion |
|---|---|---|
| 13 | Suburban street at night, a car gently rolled into a mailbox, headlights on, the driver slumped asleep over the wheel, no damage | Headlights flicker, exhaust drifts, slow push-in |
| 14 | Gas station at night, the clerk asleep with their head on the counter, fluorescent lights buzzing | Lights flicker once, a moth circles |
| 15 ⭐ | A golden retriever awake and whining, nudging its sleeping owner on a park bench at night | Dog paws at the owner and looks at the camera |
| 16 | The main character crouching next to the dog, both looking at each other in confusion | Dog tilts its head. The character slowly reaches out |

#### Clip 05: The sky (2:21–3:12)

| # | Image | Motion |
|---|---|---|
| 17 | Rooftop at dawn, the main character sitting on the edge, looking up at a pale pink and blue sky, a single white contrail crossing it perfectly straight | Slow tilt up from the character to the contrail |
| 18 ⭐ | Cutaway view inside an airliner cockpit, two pilots asleep in their seats, the autopilot panel glowing green, sunrise through the windscreen | Instrument lights blink, the fuel gauge needle creeps down |
| 19 | Simple infographic-style map of the world covered in hundreds of small white airplane icons | Icons drift slowly along their routes. *(Easier as motion graphics)* |
| 20 ⭐ | Wide sky, the contrail suddenly ending mid-sky, no plane visible, silence | Hold almost still for 2 seconds, then a very slow push-in. **No crash.** |
| 21 | The main character on the rooftop, turning away from the sky, hand over mouth | Character turns away and sits down heavily |

#### Clip 06: The lights (3:12–3:48)

| # | Image | Motion |
|---|---|---|
| 22 | City skyline at dusk, one district's lights going dark while the rest stay lit | The darkness spreads block by block across the skyline |
| 23 | Power plant control room, walls of screens with warning alerts flashing red, empty chairs | Red alarms pulse, screens glitch |
| 24 | The main character running down a dark street, a glowing red-and-white hospital sign far ahead still lit | Character runs toward the camera, the hospital glow behind them |

#### Clip 07: The clock (3:48–4:23)

| # | Image | Motion |
|---|---|---|
| 25 | Close-up of a glass of water on a dark kitchen counter, a soft glow on it | Slow push-in. Add the countdown overlay "52:00:00" in the edit |
| 26 | Split screen: left half the sleeping family in their beds, right half a hospital supply room with shelves of IV bags | Each half slowly pushes in |

#### Clip 08: The hospital (4:23–5:06)

| # | Image | Motion |
|---|---|---|
| 27 ⭐ | Comedy shot: the main character pushing mom down an empty street in a shopping cart, mom asleep in it with her bathrobe trailing, sunrise behind | Cart rattles along, the character straining |
| 28 | A hospital ward with nurses asleep at their station, the main character reading a laminated poster titled "IV SETUP" | Character's eyes scan the poster, a nurse snores softly |
| 29 | The main character's hands carefully connecting an IV line, close-up, nervous | Hands tremble slightly, then steady |
| 30 | The family in three hospital beds side by side, IV lines in, monitors glowing, the main character slumped exhausted in a chair | Monitors pulse, the character's eyes slowly close |

#### Clip 09: The phone (5:06–5:40)

| # | Image | Motion |
|---|---|---|
| 31 ⭐ | Dark hospital ward lit only by monitors, a phone on the bedside table lighting up and buzzing, screen reading "Unknown" | Phone vibrates across the table |
| 32 | Close-up of the main character with the phone to their ear, eyes wide, face lit blue | Faint flicker of static over the image |

#### Clip 10: Waking one (5:40–6:23)

| # | Image | Motion |
|---|---|---|
| 33 | Library at night, the main character surrounded by open books about sleep and the brain, notes stuck everywhere | Pages flutter, slow pan across the notes |
| 34 | The main character at the brother's bedside, holding up a phone playing music, earbuds draped on the pillow | Character hums and sways slightly |
| 35 ⭐ | Extreme close-up of the brother's eyes opening, looking straight at the camera | Eyes open slowly, pupils focus |

#### Clip 11: The twist (6:23–7:37)

| # | Image | Motion |
|---|---|---|
| 36 ⭐ | The hospital ward dissolving at the edges like wet paint running down, the brother sitting up in bed, the main character frozen | The paint melts and drips from the edges of the frame inward |
| 37 ⭐ | Bright daylight real hospital room (warmer, softer colour palette than the rest of the video), the main character asleep in the bed with tubes and monitors, mom beside the bed holding a phone to their ear, crying, brother and dad standing behind | Slow push-in on mom's face |
| 38 | A wall clock in the real hospital room reading 3:12, daylight from the window | Second hand ticks. Hold |
| 39 | Back in the dissolving dream world: the brother standing, holding out his hand toward the camera, the empty city behind him melting | His hand reaches slightly forward |

#### Clip 12: Close (7:37–end)

| # | Image | Motion |
|---|---|---|
| 40 | Over-the-shoulder: the main character looking at the brother's offered hand, the beautiful empty glowing city in the distance | Slow rack focus from the city to the hand |
| 41 ⭐ | The main character taking the hand, a bright white light bursting between them | White flash fills the frame |
| 42 ⭐ | Real hospital room: the main character's eyes opening in the bed, mom gasping, phone falling from her hand | Phone tumbles out of frame. Add the phone-hitting-the-floor SFX |
| 43 | End card background: dark blue, the main character's silhouette in a crowd of people all awake and staring at them | Subtle push-in. Add the title text and next-episode thumbnail in the edit |

**Total: 43 shots** for about 9 minutes. That's one new image every 12–13 seconds. Fill the gaps by
holding shots longer with slow camera moves, and with the title cards ("HOUR 0", "HOUR 14", "DAY 2",
"DAY 3"), which you can make in your editor.

### 2.4 Thumbnail prompt

```
[STYLE PREFIX] Thumbnail composition: the main character (17, messy dark brown hair, warm brown skin,
oversized mustard-yellow hoodie) on the centre-left, close-up from the chest up, eyes wide with fear,
one finger pressed to their lips in a "shh" gesture, warm orange rim light on their face. Background:
a dark desaturated blue city at night, every window lit, no people, a single passenger jet flying
level across the sky. Small red digital clock in the bottom-right corner reading 3:12. Empty space in
the top-right for text. Very high contrast, bold, readable at small size.
```

Add **DON'T WAKE THEM** in your editor, not in the AI prompt. Generated text comes out garbled.
Heavy white font, black stroke, "DON'T" in red. Make the A/B version the same way, with **EXCEPT YOU**
as the text.

---

## Part 3: Assembly checklist

1. Generate the voice clips (`vo-01` to `vo-12`) and lay them on the timeline first. **Edit the visuals to the
   voice**, not the other way round.
2. Drop in the shots for each clip in order, then add title cards, the countdown overlay and the world plane map.
3. Add music for each section and the SFX list.
4. Export captions, then run the tools:
   ```bash
   python3 .claude/skills/yt-edit/deadair.py final-voiceover.srt
   python3 .claude/skills/yt-chapters/chapters.py final-voiceover.srt --target 10
   ```
   The first one finds dead air to trim. The second gives the final chapters for the description.
5. When uploading, tick **Altered or synthetic content** (AI voice plus AI visuals).

Ship it, or change it?
