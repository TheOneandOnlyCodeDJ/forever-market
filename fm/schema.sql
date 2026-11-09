-- Applied on every connect; every statement must be idempotent.
CREATE TABLE IF NOT EXISTS item (
  id INTEGER PRIMARY KEY, name TEXT, quality INTEGER, item_level INTEGER, req_level INTEGER,
  class_id INTEGER, sub_class INTEGER, bonding INTEGER, stackable INTEGER, vendor_sell INTEGER,
  source TEXT
);
CREATE TABLE IF NOT EXISTS price_realm (
  item_id INTEGER PRIMARY KEY, market_value INTEGER, min_buyout INTEGER, recent INTEGER,
  historical INTEGER, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS price_region (
  item_id INTEGER PRIMARY KEY, market_value INTEGER, historical INTEGER, avg_sale INTEGER,
  sale_rate REAL, sold_per_day REAL, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS spell (
  id INTEGER PRIMARY KEY, name TEXT, profession TEXT, min_skill INTEGER, category_id INTEGER
);
CREATE TABLE IF NOT EXISTS spell_reagent (spell_id INTEGER, item_id INTEGER, quantity INTEGER);
CREATE TABLE IF NOT EXISTS craft_output (spell_id INTEGER, item_id INTEGER, num_result INTEGER);
CREATE TABLE IF NOT EXISTS creature (
  id INTEGER PRIMARY KEY, name TEXT, min_level INTEGER, max_level INTEGER, classification INTEGER,
  creature_type INTEGER, area_id INTEGER
);
CREATE TABLE IF NOT EXISTS area (id INTEGER PRIMARY KEY, name TEXT, parent_id INTEGER, continent_id INTEGER);
CREATE TABLE IF NOT EXISTS "drop" (creature_id INTEGER, item_id INTEGER, chance REAL, source TEXT, sample_size INTEGER);
CREATE TABLE IF NOT EXISTS kill_event (id INTEGER PRIMARY KEY, creature_id INTEGER, at TEXT, duration_s REAL, source TEXT);
CREATE TABLE IF NOT EXISTS loot_event (id INTEGER PRIMARY KEY, kill_event_id INTEGER, item_id INTEGER, quantity INTEGER);
CREATE TABLE IF NOT EXISTS node_area (item_id INTEGER, area_id INTEGER, kind TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS sync_log (source TEXT, fetched_at TEXT, rows INTEGER, note TEXT);
CREATE TABLE IF NOT EXISTS loot_session (
  id TEXT PRIMARY KEY, character TEXT, started INTEGER, ended INTEGER, kills INTEGER, loots INTEGER,
  copper INTEGER, seconds INTEGER, imported_at TEXT
);
CREATE TABLE IF NOT EXISTS loot_source (session_id TEXT, name TEXT, kills INTEGER, copper INTEGER);
CREATE TABLE IF NOT EXISTS loot_item_source (session_id TEXT, source_name TEXT, item_id INTEGER, count INTEGER);
CREATE TABLE IF NOT EXISTS loot_item (
  session_id TEXT, item_id INTEGER, count INTEGER, vendor INTEGER, name TEXT, quality INTEGER
);
CREATE TABLE IF NOT EXISTS api_house (
  house_id INTEGER PRIMARY KEY, ruleset_id INTEGER, name TEXT, faction TEXT, auctions INTEGER,
  commodities INTEGER, fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS api_auction (
  house_id INTEGER, auction_id INTEGER, item_id INTEGER, quantity INTEGER, buyout INTEGER, bid INTEGER,
  unit_price INTEGER, time_left TEXT, captured_at TEXT, PRIMARY KEY (house_id, auction_id)
);
CREATE TABLE IF NOT EXISTS api_commodity (
  house_id INTEGER, item_id INTEGER, quantity INTEGER, unit_price INTEGER, captured_at TEXT
);
CREATE TABLE IF NOT EXISTS api_house_match (
  house_id INTEGER PRIMARY KEY, common INTEGER, exact INTEGER, median_diff REAL, scored_at TEXT
);
-- region is explicit: house ids repeat across regions. house_id 0 = TSM realm feed (no house).
CREATE TABLE IF NOT EXISTS price_history (
  at TEXT, source TEXT, region TEXT, house_id INTEGER, item_id INTEGER,
  min_buyout INTEGER, market INTEGER, listings INTEGER, qty INTEGER,
  PRIMARY KEY (at, source, region, house_id, item_id)
);
CREATE TABLE IF NOT EXISTS index_history (at TEXT, category TEXT, index_value REAL, PRIMARY KEY (at, category));
-- Auction lifecycle: an auction that vanishes well before its duration could expire almost certainly sold.
CREATE TABLE IF NOT EXISTS auction_life (
  house_id INTEGER, auction_id INTEGER, item_id INTEGER, quantity INTEGER, buyout INTEGER,
  time_left TEXT, first_seen TEXT, last_seen TEXT, gone_at TEXT, sold INTEGER,
  PRIMARY KEY (house_id, auction_id)
);
CREATE INDEX IF NOT EXISTS idx_auction_life_item ON auction_life (item_id, gone_at);
-- His own trades, imported from TSM Accounting (csvSales / csvBuys).
CREATE TABLE IF NOT EXISTS trade (
  at INTEGER, kind TEXT, item_id INTEGER, stack INTEGER, qty INTEGER, total INTEGER,
  unit INTEGER, other TEXT, player TEXT, source TEXT,
  PRIMARY KEY (at, kind, item_id, qty, total, player)
);
CREATE INDEX IF NOT EXISTS idx_trade_item ON trade (item_id, kind);
