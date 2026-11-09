#!/bin/sh
# Restore the database (and missing/changed files) from a nightly backup.
# Usage: scripts/restore.sh                 → lists the days you can restore
#        scripts/restore.sh 2026-11-08      → restores that day (asks for confirmation)
# Stops api + workers so nothing writes while restoring, and starts them again at the end.
set -eu
if [ $# -eq 0 ]; then
  docker compose exec -T worker-heavy crayonlark backup-list
  exit 0
fi
printf "Replace the WHOLE database with the backup from %s? Type yes: " "$1"
read -r answer
[ "$answer" = "yes" ] || { echo "aborted"; exit 1; }
docker compose stop api worker scheduler bot
docker compose exec -T worker-heavy crayonlark restore --day "$1" --yes
docker compose start api worker scheduler bot
echo "Restored $1. Check the admin dashboard."
