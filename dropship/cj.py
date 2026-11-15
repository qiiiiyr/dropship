"""CJ Dropshipping API 2.0 client. Docs: https://developers.cjdropshipping.com/en/api/api2/"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://developers.cjdropshipping.com/api2.0/v1"
_token = None
_last_call = 0.0


class CJError(Exception):
    pass


class Blocked(Exception):
    """CJ will not let this order be paid right now; a human has to look."""


def call(method, path, params=None, body=None):
    global _last_call
    time.sleep(max(0, _last_call + 1.1 - time.monotonic()))  # CJ allows 1 request/second
    _last_call = time.monotonic()
    url = BASE + path + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    headers = {"Content-Type": "application/json", "User-Agent": "dropship/1.0"}
    if not path.startswith("/authentication/"):
        headers["CJ-Access-Token"] = token()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            res = json.load(e)
        except ValueError:
            raise CJError(f"{path}: HTTP {e.code}") from None
    # Some endpoints answer with code/result, others with success only.
    if res.get("result") is False or res.get("success") is False or res.get("code") not in (None, 200):
        raise CJError(f"{path}: {res.get('code')} {res.get('message')}")
    return res.get("data")


def token():
    global _token
    if not _token:
        # CJ returns the same cached token for 24 h, so asking once per run is fine.
        _token = call("POST", "/authentication/getAccessToken", body={"apiKey": os.environ["CJ_API_KEY"]})["accessToken"]
    return _token


def orders(**params):
    """One page of orders, newest first. Returns {"total": n, "list": [...]}."""
    # shortcut: first 100 only, add paging when a single status holds more than 100 orders
    data = call("GET", "/shopping/order/list", params={"pageNum": 1, "pageSize": 100, **params}) or {}
    return {"total": data.get("total") or 0, "list": data.get("list") or []}


def order(order_id):
    return call("GET", "/shopping/order/getOrderDetail", params={"orderId": order_id})


def balance():
    return float(call("GET", "/shopping/pay/getBalance")["amount"] or 0)


def _tips(data):
    return "; ".join(
        reason.get("simpleTip") or f"code {reason.get('interceptReasonCode')}"
        for blocked in (data or {}).get("interceptOrders") or []
        for reason in blocked.get("interceptReason") or []
    )


def pay(order_id, status, limit_usd):
    """Cart -> confirm -> quote -> pay, for one order. Returns the USD charged.

    One order per payment, so the amount CJ quotes is this order's alone and can
    be checked against what was reviewed before any money moves.
    """
    ids = {"cjOrderIdList": [order_id]}
    if status == "CREATED":
        added = call("POST", "/shopping/order/addCart", body=ids)
        if _tips(added):
            raise Blocked(_tips(added))
    confirm = call("POST", "/shopping/order/addCartConfirm", body=ids) or {}
    shipment = confirm.get("shipmentsId")
    if not shipment:
        # shortcut: an order left UNPAID by an interrupted run lands here, because CJ does not
        # return its payment id again; it is reported and paid by hand in My CJ.
        raise Blocked(_tips(confirm) or "CJ did not confirm the order; open it in My CJ")
    quote = call("POST", "/shopping/order/saveGenerateParentOrder", body={"shipmentOrderId": shipment}) or {}
    money = float(quote.get("orderMoney") or 0)
    if not quote.get("payId") or not money:
        raise Blocked(_tips(quote) or "CJ did not return a payment quote")
    if money > limit_usd:
        raise Blocked(f"CJ quotes ${money:.2f}, above the reviewed ${limit_usd:.2f}")
    call("POST", "/shopping/pay/payBalanceV2", body={"shipmentOrderId": shipment, "payId": quote["payId"]})
    return money


def products(**params):
    data = call("GET", "/product/listV2", params=params) or {}
    return [p for block in data.get("content") or [] for p in block.get("productList") or []]
