# Episode 1: What IF You Were the Only One Awake for 72 Hours?

An original "What IF You…" episode in the style of
[What IF You Could Stop Time? (IFOLOGY)](https://www.youtube.com/watch?v=YznR5NmI3bc).
It copies the **format**, not the content: the premise, story, characters and twist are all new.

## The reference format

Taken from IFOLOGY's channel page: 53K subscribers, 50 videos, about "what if gets taken seriously".
The video itself was blocked behind YouTube's bot check, so the format comes from its title and the
channel's recent uploads.

- **Title pattern:** always "What IF You…" with a capital IF, in the second person. One impossible
  power or situation: stop time, X-ray vision, portals, the Backrooms, cloning yourself.
- **Length:** 10–25 minutes, mostly 18–25. Some ideas get multi-part series (Zombie
  Apocalypse parts 1–3).
- **Story shape:** "One question. One impossible idea. One story that follows it all the way."
  It escalates by time jumps and ends on a turn.
- **Upload pace:** very high, several a week.

## Files

| File | What's in it | Tool used |
|---|---|---|
| [script.md](script.md) | 2 scored hooks plus the full script with `[ON SCREEN]` animation notes on every part | `yt-script` + `hookscore.py` |
| [package.md](package.md) | 10 titles ranked, the winning title and thumbnail pair, thumbnail brief | `yt-package` + `title.py` |
| [seo.md](seo.md) | Description, checked chapters, tags, upload settings | `yt-seo` + `yt-chapters` + `chapters.py` |
| [shorts.md](shorts.md) | 5 Shorts with new scored opening lines, on-screen text and loop points | `yt-shorts` + `hookscore.py` |
| [plan.md](plan.md) | Production week, hours, what to do after it's live | `yt-plan` |
| [script-timed.srt](script-timed.srt) | The script timed at 150 wpm, used to generate the chapters | (generated) |

## Tools that couldn't run yet, and why

| Tool | Needs | When to use it |
|---|---|---|
| `yt-edit` / `deadair.py` | Captions of your **real recorded** voiceover | After you record. It lists the dead air and retakes to cut |
| `yt-retention` / `retention.py` | A retention CSV from YouTube Studio | 48 hours after upload |
| `yt-comment` | Real comments | In the first few hours after upload |
| `yt-viral` / `swipe.py` | View counts for 4+ videos per channel | YouTube hid view counts from this cloud server. Paste a list of titles and views and I'll rank them |
| `yt-audit` | Your own channel | Once you have about 10 uploads |

## Before you publish

1. Check every line in the script marked *(Check: …)*.
2. Fill in [`../../voice.md`](../../voice.md). The script uses a neutral narrator voice until you do.
3. Tick **Altered or synthetic content** if any AI visuals or voices look realistic.
4. Re-run `chapters.py` on the real voiceover captions.

Ship it, or change it?
