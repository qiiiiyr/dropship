"""python -m dropship <command>. Prints JSON; exits 1 if anything went wrong."""
import argparse
import json
import os
import sys
import tomllib
from pathlib import Path

from . import cj, clean, mail, tick

ENV = ("CJ_API_KEY", "OWNER_EMAIL", "RESEND_INBOUND", "APPROVAL_SECRET")


def scrub(x):
    """Everything printed here is read by an agent, so free text is defanged first."""
    if isinstance(x, str):
        return clean(x)
    if isinstance(x, list):
        return [scrub(i) for i in x]
    if isinstance(x, dict):
        return {k: scrub(v) for k, v in x.items()}
    return x


def selfcheck(cfg):
    out = {"dry_run": cfg["dry_run"], "errors": []}
    missing = [name for name in ENV if not os.environ.get(name)]
    if missing:
        out["errors"].append("missing environment variables: " + ", ".join(missing))
        return out
    for name, check in (
        ("cj_balance_usd", cj.balance),
        ("mail_sent", lambda: bool(mail.send("[dropship] Self-check", "Email from the dropship AI works."))),
        ("mail_inbox_readable", lambda: mail.decisions() is not None),
    ):
        try:
            out[name] = check()
        except Exception as e:
            out["errors"].append(f"{name}: {type(e).__name__}: {e}")
    return out


def main():
    parser = argparse.ArgumentParser(prog="dropship")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("tick", help="review open orders, pay what is allowed, ask about the rest")
    sub.add_parser("report", help="today's numbers")
    sub.add_parser("scout", help="locally stocked products worth listing")
    sub.add_parser("selfcheck", help="check keys, CJ and email")
    send = sub.add_parser("mail", help="email the owner")
    send.add_argument("--subject", required=True)
    send.add_argument("--file", required=True, help="text file with the message")
    send.add_argument("--key", help="send at most once per 24 h under this key")
    args = parser.parse_args()

    cfg = tomllib.loads((Path(__file__).parent / "config.toml").read_text())
    try:
        if args.command == "tick":
            out = tick.run(cj, mail, cfg)
        elif args.command == "report":
            out = tick.report(cj, cfg)
        elif args.command == "scout":
            out = {"products": tick.scout(cj, cfg)}
        elif args.command == "selfcheck":
            out = selfcheck(cfg)
        else:
            sent = mail.send(args.subject, Path(args.file).read_text(), key=args.key)
            out = {"sent": bool(sent), "already_sent": sent is None}
    except Exception as e:
        out = {"errors": [f"{type(e).__name__}: {e}"]}
    print(json.dumps(scrub(out), indent=2))
    sys.exit(1 if out.get("errors") else 0)


main()
