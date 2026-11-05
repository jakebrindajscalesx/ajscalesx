# Description, chapters and tags

## The three searches this video should win

1. `what if everyone fell asleep`
2. `what if you were the last person on earth`
3. `what if you were the only one awake`

The title and the first two description lines include the words from all three.

## Description (paste as-is)

```
What if everyone fell asleep at 3:12 a.m. and you were the only one awake on Earth? Follow your
72 hours as the last person awake: the planes, the power grid, and the one call you shouldn't answer.

This is a fictional animated story. Real-world details (autopilot, the power grid, how long people
can go without water) are simplified for the story.

0:00 Everyone falls asleep at 3:12 a.m.
0:14 The world is still running
1:43 Nobody is awake but the dogs
2:21 The planes are on autopilot
3:12 The lights start going out
3:48 You have 72 hours
4:23 Saving your family
5:06 A phone call from nowhere
5:40 Waking your brother
6:23 Why nobody could wake up

Next episode: What IF everyone else woke up and you didn't?

#whatif #animation #story
```

### About the chapters

The timestamps came from `yt-chapters/chapters.py`, run on a timed caption file built from the script
at 150 words per minute. They pass YouTube's three rules: they start at 0:00, there are at least 3, and each one
is at least 10 seconds long. **Re-run it on your real voiceover captions once the video is cut**, because
your actual pacing will move these by a few seconds:

```bash
python3 .claude/skills/yt-chapters/chapters.py final-voiceover.srt --target 10
```

Keep the last chapter title vague ("Why nobody could wake up"). A chapter named "You were the
one in a coma" would spoil the twist for anyone who reads the description.

## Tags (15, for spellings and close matches only; tags barely matter)

```
what if, what if everyone fell asleep, last person awake, last person on earth, only one awake,
what if animation, what if story, what if scenario, ifology style, animated story,
alternate reality, sleep mystery, 72 hours challenge story, what if you, hypothetical story
```

Drop "ifology style" if you'd rather not tag another channel's name.

## Required settings when uploading

- **Altered or synthetic content: YES** if any visuals or the voice are AI-generated and look realistic.
  For a stylised cartoon it's optional, but ticking it costs nothing.
- **Made for kids: NO.** The themes are coma, death and planes running out of fuel.
- **Category:** Film & Animation.
