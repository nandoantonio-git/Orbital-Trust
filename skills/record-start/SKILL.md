---
name: record-start
description: "Start a recorder session for skill learning. Run before a Ralph loop or manual work session. Triggers on: start recording, record session, begin session, record start."
user-invocable: true
---

# Record Start

Start a skill learning session before running Ralph or doing manual work.

---

## What to do

1. Run the following command from the project root:

```bash
bash scripts/record.sh start
```

2. Report the session ID from the output to the user.

3. Remind the user to run `/record-end` when the session is done (after Ralph completes or after manual work is finished).

---

## Notes

- If a session is already active, the recorder will warn and return the existing session ID — do NOT start a second one.
- The `sessions.db` database is created automatically on first run — no manual `--init` needed.
- Sessions capture: provider used, active skills, AGENTS.md hash, and timestamp.
