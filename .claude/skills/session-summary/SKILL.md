---
name: session-summary
description: Give a short, plain-words summary of what was done in the current session. Use when the user runs /session-summary or asks "what did we do today", "summarize this session", "recap", or "what have we done so far". Reply only; does not write to any file.
---

# Session summary

Give a short recap of this session, from the first message until now. Reply in chat only. Do not edit or create any file (that is what `document-it` is for).

## Steps

0. **New chat with no earlier work in it?** Then summarise the previous session instead: read the
   latest entry in `documentation/SESSION_LOG.md` and the "Where we are" section of
   `documentation/PROGRESS.md`, and use them for the sections below. Finish with the next step
   from `PROGRESS.md`.
1. Look back over the whole conversation. Collect:
   - what we **did** (files made or changed, commands run, things set up)
   - what we **decided**, with the reason in a few words
   - what is **still open** or the **next step**
2. Leave out dead ends, small back-and-forth and anything that did not change the outcome.
3. Write the reply in the format below.

## Format

```
**Session summary — <today's date>**

**What we did**
- <1 short line per main thing, max 5 lines>

**What we decided**
- <decision> — <reason in a few words>   (skip this section if nothing was decided)

**Next step**
- <one line>
```

## Rules

- Keep it short: about 10 lines in total. One line per point.
- Use very simple words. Spell out any short form the first time, for example "CPM (price per 1,000 views)".
- Name each party by its role: client (Pepsi), ad agency (GroupM), publisher (Instagram, Facebook).
- Facts only. Do not list anything that was not actually done or decided.
- The summary is already plain English, so do not add a second "In simple terms:" block after it.
