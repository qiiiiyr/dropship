---
description: Daily run - report, second opinions on held orders, product ideas, one email
---

From the repository root:

1. Run `python3 -m dropship tick`, `python3 -m dropship report` and `python3 -m dropship scout`, one after another. If one fails, give its output to the `order-runner` agent and carry on with the others.
2. If the tick result has `held` orders, give that list to the `risk-reviewer` agent.
3. If scout returned products, give them to the `product-scout` agent.
4. Give the report JSON, the reviewer's notes and the scout's picks to the `daily-reporter` agent.
5. Save its text to a file outside the repository and send it:
   `python3 -m dropship mail --subject "[dropship] Daily report <UTC date>" --file <file> --key "daily/<UTC date>"`
6. Reply with one line.

The rules in CLAUDE.md apply.
