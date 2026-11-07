import argparse
import sys

from fm import db, import_loot, report, sync_items, sync_prices, sync_recipes


def main(argv=None):
    p = argparse.ArgumentParser(prog="fm")
    sub = p.add_subparsers(dest="cmd", required=True)
    sync = sub.add_parser("sync").add_subparsers(dest="what", required=True)
    prices = sync.add_parser("prices")
    prices.add_argument("--fixtures", action="store_true", help="read tests/fixtures CSVs, no network")
    sync.add_parser("items")
    sync.add_parser("recipes")
    imp = sub.add_parser("import").add_subparsers(dest="what", required=True)
    imp.add_parser("loot").add_argument("--dry-run", action="store_true", help="print what would be imported, write nothing")
    sub.add_parser("report")
    sub.add_parser("status")
    args = p.parse_args(argv)

    if args.cmd == "import":
        import_loot.run(None if args.dry_run else db.connect(), dry_run=args.dry_run)
        return 0
    conn = db.connect()
    if args.cmd == "sync":
        if args.what == "prices":
            sync_prices.run(conn, fixtures=args.fixtures)
        elif args.what == "recipes":
            sync_recipes.run(conn)
        else:
            sync_items.run(conn)
        return 0  # failures are printed and logged in sync_log; keep `&&` chains running
    if args.cmd == "status":
        sources, counts = report.status(conn)
        for r in sources:
            print(f"{r['source']:<20} {r['fetched_at']}  rows {r['rows']}  {r['note']}")
        for r in counts:
            print(f"{r['table']:<20} {r['rows']}")
        return 0
    report.run(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
