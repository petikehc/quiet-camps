#!/usr/bin/env bash
# The public database: a trimmed copy of the local one, loaded into Neon (ADR 0006).
#
#   deploy/aws/publish-db.sh build   # local: quiet_camps_public, and its size
#   deploy/aws/publish-db.sh load    # quiet_camps_public into NEON_DATABASE_URL (deploy/aws/.env)
#
# Trimmed: camp_night (a row per site per night, 1.7 GB in all) keeps only the nights the API
# still reads, from KEEP_FROM: lead times read the 3 years before the history ends (30 Sep
# 2026), and /trips/latest the 12 months before it plus a 31-day look-back. Everything else is
# copied whole, and the derived tables are frozen from the full data (freeze_derived), so
# search, calendars and typical nights keep their history since 2011; only /trips/{year}
# before 2024 comes back thin.
#
# The public database is a snapshot: never migrate it or run `qc` against it. The API writes
# only ask_count (/ask's limits), which starts empty and empties again on every load.
# Change and refresh the local database, then build and load again.
set -euo pipefail
cd "$(dirname "$0")/../.."

KEEP_FROM=${KEEP_FROM:-2023-10-01}
SOURCE=quiet_camps
PUBLIC=quiet_camps_public
MAX_MB=800 # Neon's free plan holds 0.5–1 GB per project; leave room

# The commands run in the compose Postgres 18 container, so the client tools match the server.
in_db() { docker compose exec -T db "$@"; }
psql_local() { in_db psql -U quiet_camps -v ON_ERROR_STOP=1 -q "$@"; }

build() {
  echo "Building $PUBLIC from $SOURCE, keeping camp_night from $KEEP_FROM"
  psql_local -d postgres -c "DROP DATABASE IF EXISTS $PUBLIC WITH (FORCE)" -c "CREATE DATABASE $PUBLIC"
  in_db pg_dump -U quiet_camps -Fc --exclude-table-data=camp_night \
    --exclude-table-data=ask_count -f /tmp/public.dump "$SOURCE"
  # Tables first, then the data, then camp_night's rows, then indexes and keys: building an
  # index once over the copied rows is faster than keeping it up to date row by row.
  in_db pg_restore -U quiet_camps -d "$PUBLIC" --section=pre-data /tmp/public.dump
  in_db pg_restore -U quiet_camps -d "$PUBLIC" --section=data /tmp/public.dump
  psql_local -d "$SOURCE" -c "\copy (SELECT * FROM camp_night WHERE night >= '$KEEP_FROM') TO STDOUT" |
    psql_local -d "$PUBLIC" -c "\copy camp_night FROM STDIN"
  in_db pg_restore -U quiet_camps -d "$PUBLIC" --section=post-data /tmp/public.dump
  in_db rm /tmp/public.dump
  freeze_derived
  psql_local -d "$PUBLIC" -c "VACUUM ANALYZE"

  local mb
  mb=$(psql_local -d "$PUBLIC" -At -c "SELECT pg_database_size(current_database()) / 1000000")
  echo "$PUBLIC: $mb MB, $(psql_local -d "$PUBLIC" -At -c "SELECT count(*) FROM camp_night") camp_night rows"
  if ((mb > MAX_MB)); then
    echo "Over $MAX_MB MB: raise KEEP_FROM" >&2
    exit 1
  fi
}

# area_night and campground_typical are materialized views over camp_night. A restore doesn't
# copy their rows: it refreshes them, here from the trimmed rows, which would lose every year
# before KEEP_FROM. So in the public copy they become plain tables of the same name, columns
# and indexes, filled from the full local database: a snapshot that no refresh can change.
freeze_derived() {
  local views="area_night campground_typical" view indexes
  indexes=$(psql_local -d "$SOURCE" -At -c \
    "SELECT indexdef || ';' FROM pg_indexes WHERE tablename IN ('area_night', 'campground_typical')")
  for view in $views; do
    psql_local -d "$PUBLIC" -c "CREATE TABLE ${view}_frozen (LIKE $view)"
  done
  psql_local -d "$PUBLIC" -c "DROP MATERIALIZED VIEW campground_typical, area_night"
  for view in $views; do
    psql_local -d "$PUBLIC" -c "ALTER TABLE ${view}_frozen RENAME TO $view"
    psql_local -d "$SOURCE" -c "\copy $view TO STDOUT" | psql_local -d "$PUBLIC" -c "\copy $view FROM STDIN"
  done
  psql_local -d "$PUBLIC" -c "$indexes"
}

load() {
  # shellcheck source=/dev/null
  source deploy/aws/.env
  : "${NEON_DATABASE_URL:?set it in deploy/aws/.env: the direct (not pooled) connection string from Neon}"
  echo "Loading $PUBLIC into Neon (replacing what's there)"
  in_db pg_dump -U quiet_camps -Fc -f /tmp/public.dump "$PUBLIC"
  # --no-owner --no-acl: Neon's role isn't quiet_camps. --clean: a reload replaces the tables.
  in_db pg_restore --no-owner --no-acl --clean --if-exists -d "$NEON_DATABASE_URL" /tmp/public.dump
  in_db rm /tmp/public.dump
  in_db psql -v ON_ERROR_STOP=1 -At "$NEON_DATABASE_URL" -c "ANALYZE" \
    -c "SELECT pg_size_pretty(pg_database_size(current_database())) AS size, (SELECT version_num FROM alembic_version) AS migration"
}

case "${1:-}" in
  build) build ;;
  load) load ;;
  *)
    echo "usage: $0 build|load" >&2
    exit 2
    ;;
esac
