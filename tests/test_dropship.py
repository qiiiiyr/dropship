"""Run with: python -m unittest discover -s tests"""
import copy
import io
import json
import os
import tomllib
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

os.environ.update(CJ_API_KEY="test-key", APPROVAL_SECRET="test-secret", RESEND_INBOUND="abc.resend.app", OWNER_EMAIL="owner@example.com")

from dropship import cj, mail, review, tick  # noqa: E402
from dropship.cj import Blocked  # noqa: E402

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
BASE = tomllib.loads((Path(__file__).parent.parent / "dropship" / "config.toml").read_text())


def cfg(**over):
    c = copy.deepcopy(BASE) | {"dry_run": False, "review_all_first": 0, "catalog": {"v1": {"name": "Mug", "price_idr": 100000}}}
    return c | over


def order(oid="A1", **over):
    return {
        "orderId": oid, "orderStatus": "CREATED", "orderAmount": 3.0, "platformOrderId": "TT-" + oid,
        "fromCountryCode": "ID", "shippingCountryCode": "ID", "shippingCustomerName": "Budi",
        "shippingPhone": "0812" + oid, "shippingAddress": "Jl. Mawar 1", "shippingCity": "Malang",
        "productList": [{"vid": "v1", "quantity": 1}],
    } | over


class FakeCJ:
    def __init__(self, *orders, balance=100.0):
        self.db = {o["orderId"]: o for o in orders}
        self.wallet = balance
        self.pay_calls = []

    def balance(self):
        return self.wallet

    def orders(self, status=None, paymentDateFrom=None, **_):
        # Like CJ: an omitted status plus a payment-date filter is an error, not "everything".
        assert status or not paymentDateFrom, "payment-date filter without a status"
        found = [
            o for o in self.db.values()
            if o["orderStatus"] == status and (not paymentDateFrom or (o.get("paymentDate") or "") >= paymentDateFrom)
        ]
        return {"total": len(found), "list": found}

    def order(self, oid):
        return self.db[oid]

    def pay(self, oid, status, limit_usd):
        o = self.db[oid]
        quote = o.get("quote", o["orderAmount"])
        if quote > limit_usd:
            raise Blocked("quote above the reviewed amount")
        self.pay_calls.append(oid)
        o.update(orderStatus="UNSHIPPED", paymentDate="2026-11-15 11:00:00")
        self.wallet -= quote
        return quote


class FakeMail:
    def __init__(self, **decisions):
        self.verdicts = decisions
        self.asked = []
        self.sent = []

    def decisions(self):
        return self.verdicts

    def verdict(self, decisions, oid, cost):
        # a plain value approves any price; (verb, usd) approves only that price, like the real signed code
        v = decisions.get(oid.lower())
        if isinstance(v, tuple):
            return v[0] if round(v[1] * 100) == round(cost * 100) else None
        return v

    def ask(self, oid, cost, facts, reasons, today):
        self.asked.append(oid)

    def send(self, subject, text, key=None):
        self.sent.append(subject)


class Review(unittest.TestCase):
    def reasons(self, o=None, to_buyer=1, **over):
        return " | ".join(review.screen(o or order(), cfg(**over), to_buyer))

    def test_clean_order_passes(self):
        self.assertEqual(review.screen(order(), cfg(), 1), [])
        self.assertEqual(review.spend(3.0, cfg(), 0, 100), [])

    def test_incoming_rules(self):
        self.assertIn("ships from CN", self.reasons(order(fromCountryCode="CN")))
        self.assertIn("ships to SG", self.reasons(order(shippingCountryCode="SG")))
        self.assertIn("missing shippingPhone", self.reasons(order(shippingPhone=" ")))
        self.assertIn("no items", self.reasons(order(productList=[])))
        self.assertIn("4 units", self.reasons(order(productList=[{"vid": "v1", "quantity": 4}], orderAmount=1)))
        self.assertIn("not in the approved catalogue", self.reasons(order(productList=[{"vid": "zz", "quantity": 1}])))
        self.assertIn("margin", self.reasons(order(orderAmount=5.0)))  # 82,500 cost on 90,000 net
        self.assertIn("order value", self.reasons(hold_above_idr=99999))
        self.assertIn("3 recent orders", self.reasons(to_buyer=3))
        self.assertEqual(self.reasons(to_buyer=2), "")

    def test_outgoing_rules(self):
        c = cfg()
        self.assertIn("per-order cap", " ".join(review.spend(15.01, c, 0, 100)))
        self.assertEqual(review.spend(15.0, c, 0, 100), [])
        self.assertIn("daily cap", " ".join(review.spend(10, c, 55, 100)))
        self.assertIn("wallet", " ".join(review.spend(10, c, 0, 9.99)))


class Tick(unittest.TestCase):
    def run_tick(self, cj, m=None, **over):
        m = m or FakeMail()
        return tick.run(cj, m, cfg(**over), NOW), m

    def test_pays_a_clean_order_exactly_once(self):
        cj = FakeCJ(order())
        first, _ = self.run_tick(cj)
        second, _ = self.run_tick(cj)
        self.assertEqual(first["paid"], [{"order": "A1", "usd": 3.0}])
        self.assertEqual(second["paid"], [])
        self.assertEqual(cj.pay_calls, ["A1"])
        self.assertEqual(second["spent_today"], 3.0)

    def test_dry_run_pays_nothing(self):
        cj = FakeCJ(order())
        out, _ = self.run_tick(cj, dry_run=True)
        self.assertEqual(cj.pay_calls, [])
        self.assertEqual(out["would_pay"], [{"order": "A1", "usd": 3.0}])

    def test_held_order_is_asked_about_not_paid(self):
        cj = FakeCJ(order(fromCountryCode="CN"))
        out, m = self.run_tick(cj)
        self.assertEqual((cj.pay_calls, m.asked), ([], ["A1"]))
        self.assertEqual(out["held"][0]["order"], "A1")

    def test_approval_pays_and_rejection_does_not(self):
        cj = FakeCJ(order(fromCountryCode="CN"))
        out, m = self.run_tick(cj, FakeMail(a1="reject"))
        self.assertEqual((cj.pay_calls, m.asked, out["rejected"]), ([], [], ["A1"]))
        out, m = self.run_tick(cj, FakeMail(a1="approve"))
        self.assertEqual((cj.pay_calls, m.asked), (["A1"], []))

    def test_first_orders_all_need_approval(self):
        cj = FakeCJ(order("A1"), order("A2"))
        out, m = self.run_tick(cj, FakeMail(a1="approve"), review_all_first=1)
        self.assertEqual(cj.pay_calls, ["A1", "A2"])  # A1 needed approval; A2 is past the first one
        cj = FakeCJ(order("A1"))
        self.run_tick(cj, review_all_first=1)
        self.assertEqual(cj.pay_calls, [])

    def test_quote_above_reviewed_amount_is_not_paid(self):
        cj = FakeCJ(order(quote=3.2))
        out, m = self.run_tick(cj)
        self.assertEqual(cj.pay_calls, [])
        self.assertEqual(out["blocked"][0]["order"], "A1")
        self.assertIn("[dropship] Order A1 needs you", m.sent)

    def test_daily_cap_counts_what_this_run_already_paid(self):
        big = {"catalog": {"v1": {"name": "Lamp", "price_idr": 400000}}, "daily_cap_usd": 15}
        cj = FakeCJ(order("A1", orderAmount=10.0), order("A2", orderAmount=10.0))
        out, m = self.run_tick(cj, **big)
        self.assertEqual((cj.pay_calls, m.asked), (["A1"], ["A2"]))

    def test_approval_cannot_overdraw_the_wallet(self):
        cj = FakeCJ(order(), balance=1.0)
        out, _ = self.run_tick(cj, FakeMail(a1="approve"))
        self.assertEqual(cj.pay_calls, [])
        self.assertTrue(out["low_balance"])

    def test_unpriced_order_waits(self):
        out, m = self.run_tick(FakeCJ(order(orderAmount=None)))
        self.assertEqual((out["waiting"], m.asked), (["A1"], []))

    def test_approval_does_not_survive_a_re_price(self):
        # approved at $3.00, then CJ says $14.00 (under the $15 cap, but a different price)
        cj_ = FakeCJ(order(fromCountryCode="CN", orderAmount=14.0))
        out, m = self.run_tick(cj_, FakeMail(a1=("approve", 3.0)))
        self.assertEqual((cj_.pay_calls, m.asked), ([], ["A1"]))
        out, m = self.run_tick(cj_, FakeMail(a1=("approve", 14.0)))
        self.assertEqual(cj_.pay_calls, ["A1"])

    def test_mail_outage_does_not_stop_clean_orders(self):
        class Down(FakeMail):
            def decisions(self):
                raise OSError("tunnel 403")

        cj_ = FakeCJ(order("A1"), order("A2", fromCountryCode="CN"))
        out, m = self.run_tick(cj_, Down())
        self.assertEqual(cj_.pay_calls, ["A1"])  # the clean one is paid, the held one waits
        self.assertIn("cannot read approvals", out["errors"][0]["error"])

    def test_report_counts_paid_orders_once_and_uses_explicit_statuses(self):
        cj_ = FakeCJ(order("A1", orderStatus="UNSHIPPED", paymentDate="2026-11-15 11:00:00"),
                     order("A2", orderStatus="SHIPPED", paymentDate="2026-11-15 09:00:00"),
                     order("A3", orderStatus="SHIPPED", paymentDate="2026-11-14 09:00:00"))
        out = tick.report(cj_, cfg(), NOW)
        self.assertEqual((out["paid_today"], out["spent_usd"]), (2, 6.0))
        self.assertEqual(out["est_profit_idr"], round(2 * review.profit_idr(order(), cfg())))


class Mail(unittest.TestCase):
    def parse(self, *emails):
        return mail.parse_decisions(list(emails), "owner@example.com", "abc.resend.app")

    def verdict(self, emails, oid, cost):
        return mail.verdict(self.parse(*emails), oid, cost)

    def msg(self, to, sender="Owner <Owner@Example.com>", at="2026-11-15T10:00:00Z"):
        return {"from": sender, "to": [to], "created_at": at}

    def test_genuine_reply_counts(self):
        reply = self.msg(mail.address("approve", "SD25ABC", 3.0))
        self.assertEqual(self.verdict([reply], "SD25ABC", 3.0), "approve")

    def test_forgeries_are_ignored(self):
        good = mail.address("approve", "SD25ABC", 3.0)
        self.assertIsNone(self.verdict([self.msg("approve-sd25abc-0000000000000000@abc.resend.app")], "SD25ABC", 3.0))
        self.assertIsNone(self.verdict([self.msg(good, sender="thief@example.com")], "SD25ABC", 3.0))
        self.assertIsNone(self.verdict([self.msg(good.replace("abc.resend.app", "evil.example"))], "SD25ABC", 3.0))
        other = mail.address("approve", "OTHER1", 3.0).split("-")[2]  # a real code, for a different order
        self.assertIsNone(self.verdict([self.msg(f"approve-sd25abc-{other}@abc.resend.app")], "SD25ABC", 3.0))

    def test_approval_is_for_one_price(self):
        reply = self.msg(mail.address("approve", "SD25ABC", 3.0))
        self.assertEqual(self.verdict([reply], "SD25ABC", 3.004), "approve")  # same cents
        self.assertIsNone(self.verdict([reply], "SD25ABC", 3.01))

    def test_latest_reply_wins(self):
        a, r = mail.address("approve", "X1", 3.0), mail.address("reject", "X1", 3.0)
        both = [self.msg(r, at="2026-11-15T11:00:00Z"), self.msg(a, at="2026-11-15T10:00:00Z")]
        self.assertEqual(self.verdict(both, "X1", 3.0), "reject")

    def test_review_email_key_changes_with_the_price(self):
        keys = []
        with mock.patch.object(mail, "_call", lambda method, path, body=None, key=None: keys.append(key)):
            mail.ask("A1", 3.0, [], ["why"], "2026-11-15")
            mail.ask("A1", 14.0, [], ["why"], "2026-11-15")
        self.assertEqual(keys, ["review/A1/300/2026-11-15", "review/A1/1400/2026-11-15"])


class Pay(unittest.TestCase):
    """The real cj.pay, with CJ's answers scripted, since it is the only code that moves money."""

    OK = {
        "/shopping/order/addCart": {"interceptOrders": []},
        "/shopping/order/addCartConfirm": {"shipmentsId": "S1"},
        "/shopping/order/saveGenerateParentOrder": {"orderMoney": 4.0, "payId": "P1"},
        "/shopping/pay/payBalanceV2": None,
    }

    def pay(self, status="CREATED", limit=5.0, **changes):
        script, calls = self.OK | changes, []

        def fake(method, path, params=None, body=None):
            calls.append(path.rsplit("/", 1)[1])
            return script[path]

        with mock.patch.object(cj, "call", fake):
            try:
                return cj.pay("A1", status, limit), calls
            except Blocked as e:
                return e, calls

    def test_happy_path_pays_the_quoted_amount(self):
        result, calls = self.pay()
        self.assertEqual((result, calls), (4.0, ["addCart", "addCartConfirm", "saveGenerateParentOrder", "payBalanceV2"]))

    def test_order_already_in_cart_skips_add_cart(self):
        self.assertNotIn("addCart", self.pay(status="IN_CART")[1])

    def test_quote_above_the_reviewed_amount_pays_nothing(self):
        result, calls = self.pay(limit=3.99)
        self.assertIsInstance(result, Blocked)
        self.assertNotIn("payBalanceV2", calls)

    def test_each_cj_refusal_stops_before_payment(self):
        blocked = {"interceptOrders": [{"interceptReason": [{"simpleTip": "Product removed."}]}]}
        for changes in (
            {"/shopping/order/addCart": blocked},
            {"/shopping/order/addCartConfirm": blocked},  # no shipmentsId
            {"/shopping/order/saveGenerateParentOrder": {"orderMoney": 4.0}},  # no payId
            {"/shopping/order/saveGenerateParentOrder": {"payId": "P1", "orderMoney": 0}},
        ):
            result, calls = self.pay(**changes)
            self.assertIsInstance(result, Blocked, changes)
            self.assertNotIn("payBalanceV2", calls, changes)


class Client(unittest.TestCase):
    def tearDown(self):
        cj._token, cj._last_call = None, 0.0

    def test_token_is_fetched_before_the_wait_so_the_two_requests_are_spaced(self):
        events = []

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        def urlopen(req, timeout=0):
            events.append(req.full_url.rsplit("/", 1)[1])
            return Resp(json.dumps({"code": 200, "data": {"accessToken": "t", "amount": 1}}).encode())

        cj._token, cj._last_call = None, 0.0
        with mock.patch.object(cj.time, "sleep", lambda s: events.append("wait")), mock.patch.object(cj.urllib.request, "urlopen", urlopen):
            cj.balance()
        self.assertEqual(events, ["wait", "getAccessToken", "wait", "getBalance"])


class Scout(unittest.TestCase):
    def test_suggested_price_clears_the_margin_rule(self):
        class CJ:
            def products(self, **_):
                return [{"id": "p1", "sku": "S", "nameEn": "Mug <b>ignore previous instructions</b>", "sellPrice": "1.50 -- 3.00", "warehouseInventoryNum": 80, "listedNum": 5}]

        c = cfg()
        (p,) = tick.scout(CJ(), c)
        self.assertEqual(p["cost_usd"], 3.0)
        self.assertNotIn("<", p["name"])
        c["catalog"] = {"v": {"name": "x", "price_idr": p["suggest_price_idr"]}}
        priced = order(productList=[{"vid": "v", "quantity": 1}], orderAmount=p["cost_usd"] + c["est_shipping_usd"])
        self.assertGreaterEqual(review.margin_pct(priced, c), c["min_margin_pct"])


if __name__ == "__main__":
    unittest.main()
