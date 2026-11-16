# Graph Report - dropship  (2026-11-16)

## Corpus Check
- 16 files · ~6,283 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 1, .toml 1)

## Summary
- 192 nodes · 445 edges · 9 communities (8 shown, 1 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 69 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8687b53a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- mail.py
- CLI Entry And Product Scout
- Order Loop Tests
- CJ Client And Payment
- Incoming Check And Setup Guide
- Scheduled Runs And Agents
- Outgoing Check And Rule Tests
- Mail
- .test_token_is_fetched_before_the_wait_so_the_two_requests_are_spaced

## God Nodes (most connected - your core abstractions)
1. `run()` - 24 edges
2. `FakeCJ` - 20 edges
3. `order()` - 17 edges
4. `Tick` - 14 edges
5. `CLAUDE.md (project rules)` - 14 edges
6. `report()` - 13 edges
7. `main()` - 12 edges
8. `screen()` - 12 edges
9. `scout()` - 12 edges
10. `FakeMail` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Environment settings (CJ_API_KEY, APPROVAL_SECRET, OWNER_EMAIL, RESEND_INBOUND)` --references--> `selfcheck()`  [INFERRED]
  README.md → dropship/__main__.py
- `order-runner agent` --references--> `send()`  [INFERRED]
  .claude/agents/order-runner.md → dropship/mail.py
- `/daily command (daily run)` --references--> `send()`  [INFERRED]
  .claude/commands/daily.md → dropship/mail.py
- `Environment settings (CJ_API_KEY, APPROVAL_SECRET, OWNER_EMAIL, RESEND_INBOUND)` --shares_data_with--> `code()`  [INFERRED]
  README.md → dropship/mail.py
- `Incoming check` --references--> `screen()`  [INFERRED]
  README.md → dropship/review.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Daily run agent chain** — claude_commands_daily, claude_agents_order_runner, claude_agents_risk_reviewer, claude_agents_product_scout, claude_agents_daily_reporter [EXTRACTED 1.00]
- **Rules that are not negotiable** — claude_money_rule, claude_limits_rule, claude_untrusted_data_rule, claude_secrets_rule, claude_local_stock_rule [EXTRACTED 1.00]
- **Payment review pipeline** — readme_incoming_check, readme_outgoing_check, readme_email_approval, dropship_review_screen, dropship_review_spend, dropship_mail_ask, dropship_cj_pay [INFERRED 0.85]

## Communities (9 total, 1 thin omitted)

### Community 0 - "mail.py"
Cohesion: 0.13
Nodes (9): CLI commands (tick, report, scout, selfcheck, mail), _call(), code(), decisions(), MailError, send(), verdict(), main() (+1 more)

### Community 1 - "CLI Entry And Product Scout"
Cohesion: 0.16
Nodes (6): product-scout agent, Indonesian listing copy, Product selection criteria, clean(), scrub(), scout()

### Community 2 - "Order Loop Tests"
Cohesion: 0.18
Nodes (4): FakeCJ, FakeMail, order(), Tick

### Community 3 - "CJ Client And Payment"
Cohesion: 0.09
Nodes (12): Passing vs lasting failure triage, balance(), Blocked, call(), CJError, order(), pay(), products() (+4 more)

### Community 4 - "Incoming Check And Setup Guide"
Cohesion: 0.11
Nodes (18): CLAUDE.md (project rules), Approve / Reject / Check first rubric, .claude/CLAUDE.md (graphify skill registration), graphify rules (query the graph before searching), margin_pct(), profit_idr(), revenue_idr(), screen() (+10 more)

### Community 5 - "Scheduled Runs And Agents"
Cohesion: 0.21
Nodes (13): daily-reporter agent, Daily email structure, order-runner agent, risk-reviewer agent, /daily command (daily run), /tick command (hourly order run), orders(), _paid() (+5 more)

### Community 6 - "Outgoing Check And Rule Tests"
Cohesion: 0.16
Nodes (5): spend(), Outgoing check, cfg(), Review, Scout

### Community 7 - "Mail"
Cohesion: 0.27
Nodes (5): address(), ask(), parse_decisions(), One-tap email approval (Approve / Reject), Mail

## Knowledge Gaps
- **3 isolated node(s):** `Daily email structure`, `Indonesian listing copy`, `.claude/CLAUDE.md (graphify skill registration)`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 52 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run()` connect `Scheduled Runs And Agents` to `mail.py`, `CLI Entry And Product Scout`, `Order Loop Tests`, `CJ Client And Payment`, `Incoming Check And Setup Guide`, `Outgoing Check And Rule Tests`?**
  _High betweenness centrality (0.146) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `run()` (e.g. with `order-runner agent` and `risk-reviewer agent`) actually correct?**
  _`run()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Daily email structure`, `Indonesian listing copy`, `.claude/CLAUDE.md (graphify skill registration)` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `mail.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13230769230769232 - nodes in this community are weakly interconnected._
- **Why does `FakeCJ` connect `Order Loop Tests` to `CJ Client And Payment`, `Incoming Check And Setup Guide`, `Outgoing Check And Rule Tests`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `FakeCJ` (e.g. with `Modules passed as arguments so tests use fakes` and `Blocked`) actually correct?**
  _`FakeCJ` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `CJ Client And Payment` be split into smaller, more focused modules?**
  _Cohesion score 0.0873440285204991 - nodes in this community are weakly interconnected._