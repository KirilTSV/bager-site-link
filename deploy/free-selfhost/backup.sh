#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
umask 077
mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="backups/bager-${stamp}.dump"
tmp="${file}.partial"
trap 'rm -f "$tmp"' EXIT
docker compose exec -T db pg_dump -U bager -d bager -Fc > "$tmp"
test -s "$tmp"
mv "$tmp" "$file"
trap - EXIT
echo "Backup created: $file"
# Local retention is intentionally NOT automatic. Verify an off-host copy before deletion.
