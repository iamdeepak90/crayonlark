#!/bin/sh
# Run a backup now (the scheduler also runs one every night at 03:00 IST).
# Usage: scripts/backup.sh            (on the server, from the repo/compose directory)
set -eu
docker compose exec -T worker-heavy crayonlark backup
