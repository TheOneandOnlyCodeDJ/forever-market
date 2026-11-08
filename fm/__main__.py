import argparse
import sys

from fm import blizzard, db, import_loot, report, sync_items, sync_prices, sync_recipes


def main(argv=None):
    p = argparse.ArgumentParser(prog="fm")
    sub = p.add_subparsers(dest="cmd", required=True)
    sync = sub.add_parser("sync").add_subparsers(dest="what", required=True)
    prices = sync.add_parser("prices")
    prices.add_argument("--fixtures", action="store_true", help="read tests/fixtures CSVs, no network")
    sync_api = sync.add_parser("api")
    sync_api.add_argument("--houses", choices=("horde", "all"), default="horde",
                          help="horde = houses named Horde or Blackwater")
    sync.add_parser("items")
    sync.add_parser("recipes")
    imp = sub.add_parser("import").add_subparsers(dest="what", required=True)
    imp.add_parser("loot").add_argument("--dry-run", action="store_true", help="print what would be imported, write nothing")
    probe = sub.add_parser("api").add_subparsers(dest="what", required=True).add_parser("probe")
    for ap in (probe, sync_api):
        ap.add_argument("--ruleset", type=int, default=1)
        ap.add_argument("--region", choices=blizzard.REGIONS, help="default BLIZZARD_REGION or us")
    sub.add_parser("report")
    sub.add_parser("status")
    srv = sub.add_parser("serve")
    srv.add_argument("--port", type=int, default=8099)
    srv.add_argument("--host", default="127.0.0.1")
    args = p.parse_args(argv)

    if args.cmd == "serve":
        from fm import web
        web.serve(args.host, args.port)
        return 0
    if args.cmd == "api" or (args.cmd == "sync" and args.what == "api"):
        try:
            blizzard.credentials()  # before touching the DB
            if args.cmd == "api":
                blizzard.probe(args.ruleset, args.region)
            else:
                blizzard.sync(db.connect(), args.ruleset, args.houses, args.region)
        except blizzard.MissingCredentials as e:
            print(e)
            return 2
        except (blizzard.BlizzardError, OSError) as e:
            print(f"blizzard api failed: {e}")
            return 1
        return 0
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
