#!/bin/sh
# DESTRUCTIVE: replaces the database. Only use on a stopped app and after verification.
set -eu
if [ "$#" -ne 1 ] || [ ! -s "$1" ]; then echo "Usage: sh restore.sh /path/to/verified.dump" >&2; exit 2; fi
backup_file="$(cd "$(dirname "$1")" && pwd -P)/$(basename "$1")"
cd "$(dirname "$0")"
echo "This will REPLACE the bager database. The application will be stopped first." >&2
printf 'Type RESTORE-BAGER to proceed: ' >&2
IFS= read -r answer
[ "$answer" = "RESTORE-BAGER" ] || { echo "Cancelled" >&2; exit 1; }
docker compose --env-file .env stop app
docker compose --env-file .env exec -T db sh -c 'dropdb -U bager --if-exists bager && createdb -U bager -O bager bager'
docker compose --env-file .env exec -T db sh -c 'exec pg_restore -U bager -d bager --no-owner --no-acl' < "$backup_file"
echo "Restore finished. Start app and verify /health and business records." 
