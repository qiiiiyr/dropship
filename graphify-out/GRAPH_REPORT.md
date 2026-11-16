# Graph Report - dropship  (2026-11-15)

## Corpus Check
- Corpus is ~5,581 words - fits in a single context window. You may not need a graph.

## Summary
- 164 nodes · 386 edges · 8 communities
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 67 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Email Approval Channel
- CLI Entry And Product Scout
- Order Loop Tests
- CJ Client And Payment
- Incoming Check And Setup Guide
- Scheduled Runs And Agents
- Outgoing Check And Rule Tests
- Project Rules And Design

## God Nodes (most connected - your core abstractions)
1. `run()` - 23 edges
2. `FakeCJ` - 17 edges
3. `order()` - 14 edges
4. `CLAUDE.md (project rules)` - 14 edges
5. `main()` - 12 edges
6. `screen()` - 12 edges
7. `report()` - 12 edges
8. `scout()` - 12 edges
9. `Tick` - 11 edges
10. `Blocked` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Growth path (faster scheduler, TikTok API adapter)` --references--> `run()`  [INFERRED]
  README.md → dropship/tick.py
- `Order flow: TikTok Shop order -> CJ -> review -> pay or ask` --references--> `run()`  [INFERRED]
  README.md → dropship/tick.py
- `Environment settings (CJ_API_KEY, APPROVAL_SECRET, OWNER_EMAIL, RESEND_INBOUND)` --references--> `selfcheck()`  [INFERRED]
  README.md → dropship/__main__.py
- `Rule 1: money moves only through tick` --rationale_for--> `pay()`  [INFERRED]
  CLAUDE.md → dropship/cj.py
- `order-runner agent` --references--> `send()`  [INFERRED]
  .claude/agents/order-runner.md → dropship/mail.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Payment review pipeline** — readme_incoming_check, readme_outgoing_check, readme_email_approval, dropship_review_screen, dropship_review_spend, dropship_mail_ask, dropship_cj_pay [INFERRED 0.85]
- **Daily run agent chain** — claude_commands_daily, claude_agents_order_runner, claude_agents_risk_reviewer, claude_agents_product_scout, claude_agents_daily_reporter [EXTRACTED 1.00]
- **Rules that are not negotiable** — claude_money_rule, claude_limits_rule, claude_untrusted_data_rule, claude_secrets_rule, claude_local_stock_rule [EXTRACTED 1.00]

## Communities (8 total, 0 thin omitted)

### Community 0 - "Email Approval Channel"
Cohesion: 0.15
Nodes (10): address(), ask(), _call(), code(), decisions(), MailError, parse_decisions(), send() (+2 more)

### Community 1 - "CLI Entry And Product Scout"
Cohesion: 0.15
Nodes (7): Product selection criteria, CLI commands (tick, report, scout, selfcheck, mail), clean(), main(), scrub(), selfcheck(), scout()

### Community 2 - "Order Loop Tests"
Cohesion: 0.21
Nodes (4): FakeCJ, FakeMail, order(), Tick

### Community 3 - "CJ Client And Payment"
Cohesion: 0.14
Nodes (9): Passing vs lasting failure triage, balance(), Blocked, call(), CJError, order(), pay(), products() (+1 more)

### Community 4 - "Incoming Check And Setup Guide"
Cohesion: 0.16
Nodes (12): Approve / Reject / Check first rubric, margin_pct(), screen(), Approved product catalogue ([catalog]), CJ Dropshipping (supplier and wallet), CJ shop connection (Apps > TikTok Shop Non-US), Dry run and first-20-orders review, Going live in three stages (+4 more)

### Community 5 - "Scheduled Runs And Agents"
Cohesion: 0.21
Nodes (15): daily-reporter agent, Daily email structure, order-runner agent, product-scout agent, Indonesian listing copy, risk-reviewer agent, /daily command (daily run), /tick command (hourly order run) (+7 more)

### Community 6 - "Outgoing Check And Rule Tests"
Cohesion: 0.16
Nodes (5): spend(), Outgoing check, cfg(), Review, Scout

### Community 7 - "Project Rules And Design"
Cohesion: 0.16
Nodes (6): CLAUDE.md (project rules), .claude/CLAUDE.md (graphify skill registration), graphify rules (query the graph before searching), token(), Environment settings (CJ_API_KEY, APPROVAL_SECRET, OWNER_EMAIL, RESEND_INBOUND), Limits in dropship/config.toml

## Knowledge Gaps
- **3 isolated node(s):** `.claude/CLAUDE.md (graphify skill registration)`, `Indonesian listing copy`, `Daily email structure`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 41 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run()` connect `Scheduled Runs And Agents` to `CLI Entry And Product Scout`, `Order Loop Tests`, `CJ Client And Payment`, `Incoming Check And Setup Guide`, `Outgoing Check And Rule Tests`, `Project Rules And Design`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `run()` (e.g. with `order-runner agent` and `risk-reviewer agent`) actually correct?**
  _`run()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `.claude/CLAUDE.md (graphify skill registration)`, `Indonesian listing copy`, `Daily email structure` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Email Approval Channel` be split into smaller, more focused modules?**
  _Cohesion score 0.14666666666666667 - nodes in this community are weakly interconnected._
- **Why does `CLAUDE.md (project rules)` connect `Project Rules And Design` to `CLI Entry And Product Scout`, `CJ Client And Payment`, `Incoming Check And Setup Guide`, `Scheduled Runs And Agents`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `FakeCJ` (e.g. with `Modules passed as arguments so tests use fakes` and `Blocked`) actually correct?**
  _`FakeCJ` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `CJ Client And Payment` be split into smaller, more focused modules?**
  _Cohesion score 0.1380952380952381 - nodes in this community are weakly interconnected._