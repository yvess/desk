-- gsqlite3 schema upgrade, PowerDNS 4.x -> 5.0.
--
-- An existing zone database keeps working across a pdns package upgrade only if
-- its schema is upgraded too. Without this, pdns 5.0 refuses to start:
--
--   PDNSException while filling the zone cache: Database error trying to
--   retrieve all domains: ... no such column: domains.catalog
--
-- Run once, with pdns stopped, in place after backing the database up
-- (docs/runbook-powerdns-4.x-to-5.0.md has the full procedure):
--   cp /var/services/powerdns/pdns_<host>.sqlite3{,.bak}
--   sqlite3 /var/services/powerdns/pdns_<host>.sqlite3 < powerdns-upgrade-4.x-to-5.0.sql
--
-- Run it once. SQLite has no ADD COLUMN IF NOT EXISTS, so a second run reports
--   duplicate column name: options
-- and carries on through the rest, which is harmless -- that message is how you
-- can tell the database was already upgraded.
--
-- Not touched: records.change_date, which 5.0 no longer reads. An extra column
-- costs nothing, and dropping it would rewrite the whole table.

ALTER TABLE domains ADD COLUMN options VARCHAR(65535) DEFAULT NULL;
ALTER TABLE domains ADD COLUMN catalog VARCHAR(255) DEFAULT NULL;
ALTER TABLE cryptokeys ADD COLUMN published BOOL DEFAULT 1;

-- 5.0 renamed the record and comment indexes and made them multi-column
DROP INDEX IF EXISTS rec_name_index;
DROP INDEX IF EXISTS nametype_index;
DROP INDEX IF EXISTS domain_id;
DROP INDEX IF EXISTS orderindex;
DROP INDEX IF EXISTS comments_domain_id_index;
DROP INDEX IF EXISTS comments_nametype_index;

CREATE INDEX IF NOT EXISTS catalog_idx ON domains(catalog);
CREATE INDEX IF NOT EXISTS records_lookup_idx ON records(name, type);
CREATE INDEX IF NOT EXISTS records_lookup_id_idx ON records(domain_id, name, type);
CREATE INDEX IF NOT EXISTS records_order_idx ON records(domain_id, ordername);
CREATE INDEX IF NOT EXISTS comments_idx ON comments(domain_id, name, type);

-- Zones the HTTP API creates are given SOA-EDIT-API=DEFAULT, which is what
-- makes PowerDNS bump the serial on every change. Zones that predate the API
-- carry no metadata at all, so their serial would stay frozen and secondaries
-- would never see an update -- the worker stopped maintaining serials itself
-- when it moved off direct database access.
INSERT INTO domainmetadata (domain_id, kind, content)
  SELECT id, 'SOA-EDIT-API', 'DEFAULT' FROM domains
  WHERE id NOT IN (
    SELECT domain_id FROM domainmetadata WHERE kind = 'SOA-EDIT-API'
  );
