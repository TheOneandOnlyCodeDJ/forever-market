import argparse
import sys

from fm import db, report, sync_items, sync_prices


def main(argv=None):
    p = argparse.ArgumentParser(prog="fm")
    sub = p.add_subparsers(dest="cmd", required=True)
    sync = sub.add_parser("sync").add_subparsers(dest="what", required=True)
    prices = sync.add_parser("prices")
    prices.add_argument("--fixtures", action="store_true", help="read tests/fixtures CSVs, no network")
    sync.add_parser("items")
    sub.add_parser("report")
    args = p.parse_args(argv)

    conn = db.connect()
    if args.cmd == "sync":
        if args.what == "prices":
            sync_prices.run(conn, fixtures=args.fixtures)
        else:
            sync_items.run(conn)
        return 0  # failures are printed and logged in sync_log; keep `&&` chains running
    report.run(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
