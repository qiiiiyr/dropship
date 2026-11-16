# dropship

Runs a TikTok Shop Indonesia store on CJ Dropshipping without you watching it: every order is reviewed, the safe ones are paid from your CJ wallet, the doubtful ones wait for your one-tap approval by email, and you get a daily summary.

```
TikTok Shop order ──(CJ's shop connection)──▶ order in CJ, unpaid
                                                  │
every hour:  python3 -m dropship tick             ▼
               incoming check ──▶ outgoing check ──▶ pay from CJ wallet ──▶ CJ ships
                      │ fails            │ fails
                      └──────────────────┴──▶ email: Approve / Reject ──▶ next run acts on it
```

## Before you trust it: prove the route works (about a day, about $20)

The code cannot fix a supplier that cannot deliver. Do this by hand once:

1. **CJ Dropshipping**: create an account, generate an API key in My CJ ([how](https://developers.cjdropshipping.com/en/api/api2/api/auth.html)), top up about $20. The wallet balance is the hard ceiling on what the AI can ever spend, so keep it small.
2. **TikTok Shop / Tokopedia**: open a seller account for Indonesia.
3. In CJ go to **Apps > TikTok Shop Non-US** and connect the shop. Whether CJ supports Indonesian shops is not confirmed anywhere public; this step tells you.
4. List one product that has stock in CJ's **Indonesia** warehouse, buy it from your own shop, pay for it in CJ by hand and watch: does it ship inside TikTok's deadline, and does the tracking number show up in TikTok?
5. **Resend** (resend.com): create an account with the email address you want approvals sent to, open Emails > Receiving and note your `<id>.resend.app` address.

If 3 or 4 fails, stop here. Goods shipped from outside Indonesia are not an option: Indonesia sets a USD 100 per-unit floor on cross-border marketplace sales, and TikTok penalises late dispatch.

## Settings

Set in the cloud environment (or as ordinary environment variables elsewhere):

| Name | What |
|---|---|
| `CJ_API_KEY` | CJ API key. Secret. |
| `APPROVAL_SECRET` | Any long random text. Secret. Signs the approve/reject links. |
| `OWNER_EMAIL` | Where approvals and reports go. Must be your Resend account's address unless you verify a domain there. |
| `RESEND_INBOUND` | Your `<id>.resend.app` receiving domain. |
| `RESEND_API_KEY` | Resend key. Not needed in the Claude cloud environment, where it is saved as a network secret for `api.resend.com`. |
| `MAIL_FROM` | Optional. Defaults to `Dropship <onboarding@resend.dev>`. |

The cloud environment must allow the hosts `developers.cjdropshipping.com` and `api.resend.com` (saving the Resend key as a network secret allows the second one). Without `api.resend.com` every run stops at its first step.

Check everything with `python3 -m dropship selfcheck`.

## The limits

All in [`dropship/config.toml`](dropship/config.toml). The defaults are cautious: `dry_run = true` pays nothing, and the first 20 orders all need your approval.

**Incoming check** holds an order when it does not ship from and to Indonesia, the margin is under the minimum, an item is not in the catalogue, the value or quantity is high, one phone number has several orders, or the address is incomplete.

**Outgoing check** holds it when the cost is above the per-order cap, the day's spend would pass the daily cap, or the wallet is short.

A held order sends you one email a day with two buttons. Tap one and press send on the email that opens; the next run pays it or leaves it. A rejected order stays unpaid: cancel it yourself in TikTok Seller Center, since cancellations count against your shop.

Products are approved by adding them under `[catalog]` with your TikTok price. Use the lowest price you will sell at: the margin check cannot see TikTok discounts or vouchers, only this number. The CJ variant id is shown in the review email of the first order for that product (`unlisted item <id>`).

## Going live

1. `dry_run = true` for a few days. You will get review emails; approving shows up as "would pay".
2. `dry_run = false`. The first 20 orders still each need your tap.
3. After that, orders inside the limits pay themselves. Raise limits one at a time.

## Running it around the clock

Two Claude scheduled tasks start a fresh cloud session each time: `/tick` every hour and `/daily` once a day. The sub-agents in [`.claude/agents`](.claude/agents) are `order-runner` (fixes or escalates a bad run), `risk-reviewer` (second opinion on held orders), `product-scout` (what to list next) and `daily-reporter` (the daily email).

To grow: `python3 -m dropship tick` is the only entry point, so a faster schedule is a scheduler swap (GitHub Actions cron, or a small server). Buyer chat, cash-on-delivery detection and automatic cancellations need TikTok's own API and somewhere to keep its rotating tokens; that is the next module, not a rewrite.

## What it does not protect you from

- **A buyer refusing a cash-on-delivery parcel** after CJ has been paid. CJ's order data does not show the payment method, so `hold_above_idr` is the only guard.
- **A compromised run.** The checks are code, but the AI running them holds the CJ key. The wallet balance and the short list of allowed network hosts are the real walls. Top up little and often.
- **Marketplace rules, tax and returns.** You are the seller.
- CJ switches off API access after 30 days without a transaction.

## Tests

```bash
python3 -m unittest discover -s tests
```
