"""The jobs the schedule runs. Nothing is stored between runs: CJ is the record of
orders and the mailbox is the record of approvals, so every run starts from the truth."""
import math
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from . import clean, review
from .cj import Blocked

OPEN = ("CREATED", "IN_CART", "UNPAID")
FMT = "%Y-%m-%d %H:%M:%S"


PAID = ("UNSHIPPED", "SHIPPED", "DELIVERED")


def _paid(cj, since, now, **kw):
    # Status is explicit: CJ's docs say an omitted status means CANCELLED, which a payment-date filter rejects.
    pages = [cj.orders(status=s, paymentDateFrom=since.strftime(FMT), paymentDateTo=now.strftime(FMT), **kw) for s in PAID]
    return {"total": sum(p["total"] for p in pages), "list": [o for p in pages for o in p["list"]]}


def _paid_today(cj, now):
    return _paid(cj, now.replace(hour=0, minute=0, second=0, microsecond=0), now)["list"]


def _facts(order, cfg):
    items = [
        f"{i['quantity']} x {cfg['catalog'].get(i['vid'], {}).get('name', 'unlisted item ' + i['vid'])}"
        for i in order.get("productList") or []
    ]
    return [
        f"Shop order: {order.get('platformOrderId') or order.get('orderNum')}",
        f"Buyer: {order.get('shippingCustomerName')}, {order.get('shippingCity')}",
        f"Items: {', '.join(items) or 'none'}",
        f"Buyer pays: Rp{review.revenue_idr(order, cfg):,}",
    ]


def run(cj, mail, cfg, now=None):
    """Review every open order; pay what passes or was approved; ask about the rest."""
    now = now or datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    out = {"dry_run": cfg["dry_run"], "paid": [], "would_pay": [], "held": [], "rejected": [], "waiting": [], "blocked": [], "errors": []}

    balance = cj.balance()
    paid_today = _paid_today(cj, now)
    spent = sum(float(o.get("orderAmount") or 0) for o in paid_today)
    paid_90d = _paid(cj, now - timedelta(days=89), now, pageSize=1)["total"]
    open_orders = [o for status in OPEN for o in cj.orders(status=status)["list"]]
    try:
        decisions = mail.decisions() if open_orders else {}
    except Exception as e:  # a mail outage must not stop orders that need no approval
        decisions = {}
        out["errors"].append({"order": "-", "error": f"cannot read approvals, held orders will wait: {type(e).__name__}: {e}"})
    per_phone = Counter(o.get("shippingPhone") for o in open_orders + paid_today)

    for summary in open_orders:
        oid = summary["orderId"]
        try:
            order = cj.order(oid)
            if order.get("orderAmount") is None:
                out["waiting"].append(oid)  # CJ has not priced it yet
                continue
            cost = float(order["orderAmount"])
            verdict = mail.verdict(decisions, oid, cost)
            if verdict == "reject":
                out["rejected"].append(oid)
                continue
            reasons = review.screen(order, cfg, per_phone[order.get("shippingPhone")]) + review.spend(cost, cfg, spent, balance)
            if paid_90d + len(out["paid"]) + len(out["would_pay"]) < cfg["review_all_first"]:
                reasons.append(f"one of your first {cfg['review_all_first']} orders, which all need approval")
            if reasons and verdict != "approve":
                mail.ask(oid, cost, _facts(order, cfg), reasons, today)
                out["held"].append({"order": oid, "usd": cost, "reasons": reasons})
                continue
            if cost > balance:  # an approval cannot conjure money
                out["blocked"].append({"order": oid, "why": f"approved, but the wallet has ${balance:.2f} and it costs ${cost:.2f}"})
                continue
            if cfg["dry_run"]:
                out["would_pay"].append({"order": oid, "usd": cost})
            else:
                # Never pay more than 5% above the amount that was reviewed.
                cost = cj.pay(oid, order["orderStatus"], cost * 1.05)
                out["paid"].append({"order": oid, "usd": cost})
            spent += cost
            balance -= cost
        except Blocked as e:
            out["blocked"].append({"order": oid, "why": str(e)})
        except Exception as e:  # one bad order must not stop the others
            out["errors"].append({"order": oid, "error": f"{type(e).__name__}: {e}"})

    if balance < cfg["low_balance_usd"]:
        out["low_balance"] = True
        mail.send("[dropship] CJ wallet is low", f"Balance: ${balance:.2f}. Top up at cjdropshipping.com so orders keep shipping.", key=f"lowbal/{today}")
    for b in out["blocked"]:
        mail.send(f"[dropship] Order {b['order']} needs you", f"{b['why']}\n\nOpen it in My CJ > Orders.", key=f"blocked/{b['order']}/{today}")
    out["balance"] = round(balance, 2)
    out["spent_today"] = round(spent, 2)
    return out


def report(cj, cfg, now=None):
    """Numbers for the daily email."""
    now = now or datetime.now(timezone.utc)
    paid = [cj.order(o["orderId"]) for o in _paid_today(cj, now)]
    profit = sum(review.profit_idr(o, cfg) for o in paid if review.margin_pct(o, cfg) is not None)
    late = (now - timedelta(days=2)).strftime(FMT)
    return {
        "date": now.strftime("%Y-%m-%d"),
        "dry_run": cfg["dry_run"],
        "balance_usd": cj.balance(),
        "paid_today": len(paid),
        "spent_usd": round(sum(float(o.get("orderAmount") or 0) for o in paid), 2),
        "est_profit_idr": round(profit),
        "open": {status: cj.orders(status=status, pageSize=1)["total"] for status in OPEN},
        # Paid over two days ago and still not shipped: TikTok counts these as late dispatch.
        "late_risk": [o["orderId"] for o in cj.orders(status="UNSHIPPED")["list"] if (o.get("paymentDate") or "9") < late],
    }


def scout(cj, cfg):
    """Locally stocked CJ products with the price needed to clear the margin rule."""
    keep = 1 - (cfg["platform_fee_pct"] + cfg["min_margin_pct"]) / 100
    found = cj.products(countryCode=cfg["country"], startWarehouseInventory=cfg["scout_min_stock"], endSellPrice=cfg["scout_max_cost_usd"], orderBy=1, size=50)
    out = []
    for p in found:
        prices = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", str(p.get("sellPrice")))]
        if not prices:
            continue
        cost = max(prices)  # a price range means variants; plan for the dearest
        out.append({
            "pid": p.get("id"),
            "sku": p.get("sku"),
            "name": clean(p.get("nameEn"), 80),
            "cost_usd": cost,
            "stock": p.get("warehouseInventoryNum"),
            "listed_by_others": p.get("listedNum"),
            "suggest_price_idr": math.ceil((cost + cfg["est_shipping_usd"]) * cfg["usd_idr"] / keep / 1000) * 1000,
        })
    return out
