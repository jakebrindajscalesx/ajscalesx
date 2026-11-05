# Production week

This follows the `/yt-plan` approach: one main video, one cheap video, and Shorts cut from the main one.
**It assumes about 15 hours that week. Tell me your real hours and I'll resize it.** Upload days are
placeholders until your channel has its own analytics to go on.

| Day | Format | Working title | What it promises | What already exists |
|---|---|---|---|---|
| Mon–Wed | Production | (main video) | Voiceover, animation, edit | Script, shot list (the `[ON SCREEN]` notes), thumbnail brief |
| Thu | **Main long video** | What IF You Were the Only One Awake for 72 Hours? | You follow the last person awake for 72 hours | Everything in this folder |
| Fri | Short 2 | ONLY YOU. AND THE DOGS. | Why only people fell asleep | Cut from the main video |
| Sat | Short 1 | 72 HOURS LEFT | The thirst countdown | Cut from the main video |
| Sun | Cheap video: community post or poll | "Would you have stayed?" | Get comments going for episode 2 | The video's closing question |
| Mon (wk 2) | Short 3 | DON'T ANSWER IT | The phone call | Cut from the main video |

## Rough hours

| Task | Hours |
|---|---|
| Voiceover (AI voice or your own) plus pickups | 1–2 |
| Animation or visuals for 12 scenes | 8–10 |
| Edit, music, sound | 2–3 |
| Thumbnail (2 versions for the A/B test) | 1 |
| Shorts (4 cut-downs) | 1–2 |
| **Total** | **13–18** |

**Cut first if the week goes wrong:** the Sunday community post, then Short 3. Never cut the
thumbnail A/B test.

## After it's live

- Once the video has 48 hours of data, export the audience retention CSV from Studio (Analytics → Engagement →
  audience-retention chart → download) and run:
  ```bash
  python3 .claude/skills/yt-retention/retention.py retention.csv --transcript final-voiceover.srt
  ```
  It shows the exact line where viewers left. Bring it back to me with `/yt-retention`.
- Paste the comments into `/yt-comment` in the first few hours after upload.
- Episode 2 is already set up by the ending: **"What IF Everyone Else Woke Up and You Didn't?"**
