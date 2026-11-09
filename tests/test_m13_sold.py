import datetime as dt

from fm import auction_life, db, report, trades

T0 = dt.datetime(2026, 11, 10, 8, 0, tzinfo=dt.timezone.utc)
T1 = dt.datetime(2026, 11, 10, 9, 0, tzinfo=dt.timezone.utc)


def _row(aid, item, qty, buyout, left):
    return (113, aid, item, qty, buyout, None, None, left, T0.strftime("%Y-%m-%d %H:%M:%S"))


def test_long_auction_vanishing_is_a_sale_and_short_one_is_not(tmp_path):
    conn = db.connect(tmp_path / "a.db")
    auction_life.track(conn, 113, [_row(1, 10, 1, 5000, "LONG"),
                                  _row(2, 10, 1, 9000, "SHORT"),
                                  _row(3, 11, 2, 4000, "MEDIUM")], now=T0)
    # next hour, only auction 2 is still listed
    stats = auction_life.track(conn, 113, [_row(2, 10, 1, 9000, "SHORT")], now=T1)
    assert stats["gone"] == 2
    # LONG has a 4h floor so an hour gap cannot be an expiry; MEDIUM's 1h floor can
    sold = {r["auction_id"]: r["sold"] for r in conn.execute("SELECT auction_id, sold FROM auction_life")}
    assert sold[1] == 1 and sold[3] == 0  # LONG vanished early, MEDIUM could have expired
    assert stats["sold"] == 1


def test_auction_still_listed_is_not_counted(tmp_path):
    conn = db.connect(tmp_path / "a.db")
    auction_life.track(conn, 113, [_row(1, 10, 1, 5000, "VERY_LONG")], now=T0)
    stats = auction_life.track(conn, 113, [_row(1, 10, 1, 5000, "VERY_LONG")], now=T1)
    assert stats == {"new": 0, "seen": 1, "gone": 0, "sold": 0}
    assert conn.execute("SELECT sold FROM auction_life").fetchone()[0] == 0


def test_trade_csv_parses_sales_and_buys():
    text = '''
TradeSkillMasterDB = {
["r@PvP@internalData@csvSales"] = "itemString,stackSize,quantity,price,otherPlayer,player,time,source\\ni:2589,20,20,1500,Buyer,Lain,1793837072,Auction\\ni:2840,1,1,40,Merchant,Lain,1793837080,Vendor",
["r@PvP@internalData@csvBuys"] = "itemString,stackSize,quantity,price,otherPlayer,player,time,source\\ni:7005,1,1,10,Merchant,Lain,1793837083,Vendor",
}
'''
    rows = trades.parse(text)
    assert len(rows) == 3
    sale = [r for r in rows if r[1] == "sale"]
    assert (sale[0][2], sale[0][4], sale[0][5], sale[0][6]) == (2589, 20, 1500, 75)  # unit = 1500/20
    assert [r[1] for r in rows].count("buy") == 1


def test_sold_section_joins_api_tsm_and_my_trades(tmp_path):
    conn = db.connect(tmp_path / "a.db")
    conn.execute("INSERT INTO item (id, name) VALUES (10, 'Linen Cloth'), (11, 'Copper Bar')")
    conn.execute("INSERT INTO price_region (item_id, sale_rate, sold_per_day) VALUES (10, 0.75, 120)")
    conn.execute("INSERT INTO trade VALUES (1793837072, 'sale', 10, 20, 20, 1500, 75, 'Buyer', 'Lain', 'Auction')")
    auction_life.track(conn, 113, [_row(1, 10, 20, 1500, "LONG")], now=T0)
    auction_life.track(conn, 113, [], now=T1)
    rows, totals, mine = report.sold(conn)
    assert rows[0]["item"] == "Linen Cloth"
    assert rows[0]["api sold"] == 1 and rows[0]["api qty"] == 20
    assert rows[0]["my sales"] == 1 and rows[0]["my avg unit"] == 75
    assert rows[0]["tsm rate"] == 0.75
    assert totals == {"tracked": 1, "gone": 1, "sold": 1}
    assert mine["sales"] == 1 and mine["sold_copper"] == 1500


def test_sold_section_is_empty_without_data(tmp_path):
    conn = db.connect(tmp_path / "a.db")
    rows, totals, mine = report.sold(conn)
    assert rows == [] and totals["tracked"] == 0
    assert mine["sales"] == 0
