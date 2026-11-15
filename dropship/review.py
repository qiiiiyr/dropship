"""The two payment checks. Pure functions: an empty list means "safe to pay"."""


def margin_pct(order, cfg):
    """Profit as % of what the buyer paid, or None if an item is not in the catalogue."""
    revenue = 0
    for item in order.get("productList") or []:
        entry = cfg["catalog"].get(item["vid"])
        if not entry:
            return None
        revenue += entry["price_idr"] * item["quantity"]
    if not revenue:
        return None
    cost = float(order.get("orderAmount") or 0) * cfg["usd_idr"]
    return (revenue * (1 - cfg["platform_fee_pct"] / 100) - cost) / revenue * 100


def revenue_idr(order, cfg):
    return sum(
        cfg["catalog"].get(i["vid"], {}).get("price_idr", 0) * i["quantity"]
        for i in order.get("productList") or []
    )


def screen(order, cfg, orders_to_buyer):
    """Incoming check: is this order safe to fulfil?"""
    reasons = []
    want = cfg["country"]
    if order.get("fromCountryCode") != want:
        reasons.append(f"ships from {order.get('fromCountryCode') or 'an unknown country'}, not {want}")
    if order.get("shippingCountryCode") != want:
        reasons.append(f"ships to {order.get('shippingCountryCode') or 'an unknown country'}, not {want}")
    for field in ("shippingCustomerName", "shippingPhone", "shippingAddress", "shippingCity"):
        if not (order.get(field) or "").strip():
            reasons.append(f"address is missing {field}")
    items = order.get("productList") or []
    if not items:
        reasons.append("order has no items")
    qty = sum(i["quantity"] for i in items)
    if qty > cfg["max_qty"]:
        reasons.append(f"{qty} units, above the limit of {cfg['max_qty']}")
    margin = margin_pct(order, cfg)
    if margin is None:
        reasons.append("contains an item that is not in the approved catalogue")
    else:
        if margin < cfg["min_margin_pct"]:
            reasons.append(f"margin {margin:.0f}% is below {cfg['min_margin_pct']}%")
        value = revenue_idr(order, cfg)
        if value > cfg["hold_above_idr"]:
            reasons.append(f"order value Rp{value:,} is above Rp{cfg['hold_above_idr']:,}")
    if orders_to_buyer > cfg["max_orders_per_buyer"]:
        reasons.append(f"{orders_to_buyer} recent orders to the same phone number")
    return reasons


def spend(cost_usd, cfg, spent_today_usd, balance_usd):
    """Outgoing check: may the AI spend this without asking?"""
    reasons = []
    if cost_usd > cfg["per_order_cap_usd"]:
        reasons.append(f"cost ${cost_usd:.2f} is above the per-order cap ${cfg['per_order_cap_usd']}")
    if spent_today_usd + cost_usd > cfg["daily_cap_usd"]:
        reasons.append(
            f"would bring today's spend to ${spent_today_usd + cost_usd:.2f}, above the daily cap ${cfg['daily_cap_usd']}"
        )
    if cost_usd > balance_usd:
        reasons.append(f"wallet has ${balance_usd:.2f}, order costs ${cost_usd:.2f}")
    return reasons
