---
name: record-end
description: "End the active recorder session and mark it good or bad. Run after a Ralph loop or manual work session completes. Triggers on: end recording, stop recording, finish session, record end, mark session."
user-invocable: true
---

# Record End

End the current skill learning session after Ralph or manual work finishes.

---

## What to do

1. Ask the user: **"Was this session good or bad?"** (default: good)

   - **good** — Ralph completed stories, work was productive, no major issues
   - **bad** — Ralph failed repeatedly, session had major problems, not useful for learning

2. Run with the appropriate signal:

```bash
# If good (most common):
bash scripts/record.sh end good

# If bad:
bash scripts/record.sh end bad
```

3. Report the session summary and good session count from the output.

4. If the output shows **3 or more good sessions**, tell the user:

> You have enough good sessions to generate a skill. Run:
> ```bash
> bash loops/distill.sh
> ```
> Then review the candidate in `skills/pending/` and promote it to `skills/active/` if it looks useful.

---

## Notes

- If no session is active, the recorder will warn — this is harmless.
- The session count check happens automatically inside `record.sh end`.
- After promoting a skill to `skills/active/`, commit it so it persists across container rebuilds.
