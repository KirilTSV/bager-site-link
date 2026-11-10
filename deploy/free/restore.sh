#!/bin/sh
# DESTRUCTIVE: replaces the database. Only use on a stopped app and after verification.
set -eu
if [ "$#" -ne 1 ] || [ ! -s "$1" ]; then echo "Usage: sh restore.sh /path/to/verified.dump" >&2; exit 2; fi
cd "$(dirname "$0")"
echo "This will REPLACE the bager database. Stop app first: docker compose --env-file .env stop app" >&2
printf 'Type RESTORE-BAGER to proceed: ' >&2
IFS= read -r answer
[ "$answer" = "RESTORE-BAGER" ] || { echo "Cancelled" >&2; exit 1; }
docker compose --env-file .env exec -T db sh -c 'dropdb -U bager --if-exists bager && createdb -U bager -O bager bager'
docker compose --env-file .env exec -T db sh -c 'exec pg_restore -U bager -d bager --no-owner --no-acl' < "$1"
echo "Restore finished. Start app and verify /health and business records." 
