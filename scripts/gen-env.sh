#!/usr/bin/env sh
# Create a local .env with random secrets (never committed). Usage: scripts/gen-env.sh [path]
set -eu
OUT="${1:-.env}"
if [ -f "$OUT" ]; then echo "$OUT already exists, not overwriting"; exit 0; fi
hex() { openssl rand -hex "$1"; }
cat > "$OUT" <<ENV
SECRET_KEY=$(hex 32)
POSTGRES_PASSWORD=$(hex 16)
GARAGE_RPC_SECRET=$(hex 32)
GARAGE_ADMIN_TOKEN=$(hex 24)
S3_ACCESS_KEY=GK$(hex 12)
S3_SECRET_KEY=$(hex 32)
REVALIDATE_SECRET=$(hex 24)
ENV
echo "wrote $OUT"
