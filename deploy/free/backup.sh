#!/bin/sh
# Host-side consistent PostgreSQL backup. Store an additional copy OFF this server.
set -eu
cd "$(dirname "$0")"
umask 077
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
tmp="$BACKUP_DIR/bager-$stamp.dump.partial"
out="$BACKUP_DIR/bager-$stamp.dump"
trap 'rm -f "$tmp"' EXIT HUP INT TERM
docker compose --env-file .env exec -T db sh -c 'exec pg_dump -U bager -d bager -Fc --no-owner --no-acl' > "$tmp"
test -s "$tmp"
mv "$tmp" "$out"
trap - EXIT HUP INT TERM
echo "Backup created: $out"
echo "IMPORTANT: copy this backup to independent encrypted storage; same-disk backup is not disaster recovery."
