"""Email through Resend: write to the owner, read their approve/reject replies.

Docs: https://resend.com/docs/api-reference/introduction
"""
import email.utils
import hashlib
import hmac
import html
import json
import os
import re
import urllib.error
import urllib.request

API = "https://api.resend.com"
# shortcut: order ids must be letters and digits (CJ's are), widen the pattern if a supplier's are not
DECISION = re.compile(r"^(approve|reject)-([a-z0-9]+)-([0-9a-f]{16})@(.+)$")


class MailError(Exception):
    pass


def _call(method, path, body=None, key=None):
    headers = {
        # In the Claude cloud environment the network proxy swaps in the real key.
        "Authorization": "Bearer " + os.environ.get("RESEND_API_KEY", "re_injected_by_proxy"),
        "Content-Type": "application/json",
        "User-Agent": "dropship/1.0",  # Resend rejects requests without one
    }
    if key:
        headers["Idempotency-Key"] = key
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 409 and key:
            # Same key used in the last 24 h (Resend also answers 409 if the body changed): an
            # email under this key is already out, so whatever must trigger a new one belongs in the key.
            return None
        raise MailError(f"{path}: HTTP {e.code} {e.read()[:300]!r}") from None


def send(subject, text, html_body=None, key=None):
    """Email the owner, and only the owner. With a key, at most once per 24 h."""
    body = {
        "from": os.environ.get("MAIL_FROM", "Dropship <onboarding@resend.dev>"),
        "to": [os.environ["OWNER_EMAIL"]],
        "subject": subject,
        "text": text,
    }
    if html_body:
        body["html"] = html_body
    return _call("POST", "/emails", body, key)


def code(order_id, cost_usd):
    """Signs the order id AND its cost in cents, so an approval dies if CJ re-prices the order."""
    secret = os.environ["APPROVAL_SECRET"].encode()
    msg = f"{order_id.lower()}:{round(cost_usd * 100)}".encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()[:16]


def address(verb, order_id, cost_usd):
    return f"{verb}-{order_id.lower()}-{code(order_id, cost_usd)}@{os.environ['RESEND_INBOUND']}"


def parse_decisions(emails, owner, inbound):
    """{order id (lowercase): (verb, code)} from the owner's received mail; the latest reply wins.

    The sender check is a weak filter (From can be forged); verdict() checks the code,
    which only ever appears in mail sent to the owner.
    """
    out = {}
    for mail in sorted(emails, key=lambda m: m.get("created_at") or ""):
        if email.utils.parseaddr(mail.get("from") or "")[1].lower() != owner.lower():
            continue
        for to in mail.get("to") or []:
            m = DECISION.match(email.utils.parseaddr(to)[1].lower())
            if m and m[4] == inbound.lower():
                out[m[2]] = (m[1], m[3])
    return out


def verdict(decisions, order_id, cost_usd):
    """"approve", "reject" or None. None when there is no reply or it was for another price."""
    got = decisions.get(order_id.lower())
    return got[0] if got and hmac.compare_digest(got[1], code(order_id, cost_usd)) else None


def decisions():
    # shortcut: looks at the latest 100 inbound emails, page further if replies ever outnumber that
    data = _call("GET", "/emails/receiving?limit=100") or {}
    return parse_decisions(data.get("data") or [], os.environ["OWNER_EMAIL"], os.environ["RESEND_INBOUND"])


def ask(order_id, cost_usd, facts, reasons, today):
    """Ask the owner to approve or reject one held order. One email per order per day."""
    links = {verb: address(verb, order_id, cost_usd) for verb in ("approve", "reject")}
    text = "\n".join(
        [f"Order {order_id} is waiting for you. Cost at CJ: ${cost_usd:.2f}", "", "Why it is held:"]
        + [f"- {r}" for r in reasons]
        + ["", "Details:"]
        + [f"- {f}" for f in facts]
        + ["", "To approve, send any email to:", links["approve"], "", "To reject, send any email to:", links["reject"]]
    )
    esc = html.escape
    button = '<a href="mailto:{to}?subject={verb}%20{oid}&body=Just%20press%20send." style="display:inline-block;padding:10px 18px;margin:4px 8px 4px 0;border-radius:6px;background:{bg};color:#fff;text-decoration:none">{label}</a>'
    html_body = (
        f"<p>Order <b>{esc(order_id)}</b> is waiting for you. Cost at CJ: <b>${cost_usd:.2f}</b></p>"
        "<p>Why it is held:</p><ul>" + "".join(f"<li>{esc(r)}</li>" for r in reasons) + "</ul>"
        "<p>Details:</p><ul>" + "".join(f"<li>{esc(f)}</li>" for f in facts) + "</ul><p>"
        + button.format(to=links["approve"], verb="approve", oid=esc(order_id), bg="#15803d", label="Approve and pay")
        + button.format(to=links["reject"], verb="reject", oid=esc(order_id), bg="#b91c1c", label="Reject")
        + "</p><p>Tap a button, then press send on the email that opens. Nothing happens until you do.</p>"
    )
    return send(f"[dropship] Approve order {order_id}? ${cost_usd:.2f}", text, html_body, key=f"review/{order_id}/{round(cost_usd * 100)}/{today}")
