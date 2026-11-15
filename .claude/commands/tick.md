---
description: Hourly order run - review open orders, pay what is allowed, ask about the rest
---

Run `python3 -m dropship tick` from the repository root.

- Exit code 0 and `blocked` empty: reply with one line (paid, held, wallet balance) and stop. Do nothing else.
- Otherwise: hand the full JSON to the `order-runner` agent and reply with its one-line result.

The rules in CLAUDE.md apply.
