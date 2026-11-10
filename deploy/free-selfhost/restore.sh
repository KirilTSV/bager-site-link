#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
if [[ $# -ne 1 || ! -f "$1" ]]; then echo "Usage: bash restore.sh backups/bager-YYYYMMDDTHHMMSSZ.dump" >&2; exit 2; fi
file="$(realpath "$1")"
echo "WARNING: Restore REPLACES existing application data in this deployment."
echo "Stop application access and create a verified current backup first."
read -r -p "Type RESTORE to proceed: " confirm
[[ "$confirm" == RESTORE ]] || { echo "Cancelled"; exit 1; }
docker compose stop app
echo "Restoring while app is stopped..."
if docker compose exec -T db pg_restore -U bager -d bager --clean --if-exists --no-owner --no-acl --exit-on-error < "$file"; then
  docker compose start app
  echo "Restore finished; verify /health and business data."
else
  echo "Restore failed; app remains stopped. Investigate before restarting." >&2
  exit 1
fi
