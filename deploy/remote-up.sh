#!/bin/bash
# Runs ON THE VM, as root. haru-gcp.sh copies it (with the source tarball and your .env.prod) to the VM
# and calls it; you can also call it by hand:
#
#   sudo bash remote-up.sh deploy  [--domain D] [--fresh] [--day YYYY-MM-DD]
#   sudo /opt/haru/src/deploy/remote-up.sh restore [--day YYYY-MM-DD]   # replace the data with a backup
#   sudo /opt/haru/src/deploy/remote-up.sh backup                       # back up to the bucket now
#   sudo /opt/haru/src/deploy/remote-up.sh status
#
# deploy, in this order, and it stops at the first thing that goes wrong:
#   1. put the new source in /opt/haru/src and your secrets in /opt/haru/.env.prod (mode 600)
#   2. build the image                 (the old containers keep running if the build fails)
#   3. start Postgres + Redis
#   4. FIRST deploy only: load the newest backup from the bucket (into a scratch database that
#      replaces the empty one only once it is complete). This happens BEFORE the worker exists,
#      because a worker that starts on an empty database writes today's backup of that emptiness
#      over the good one.
#   5. alembic upgrade head, start api + worker + Caddy, check https://<domain>/healthz
set -euo pipefail

BASE="${HARU_BASE:-/opt/haru}"   # HARU_BASE: for tests only
SRC=$BASE/src
COMPOSE_ENV=$BASE/compose.env
MARKER=$BASE/.initialized
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { printf '[haru] %s\n' "$*"; }
die() { printf '[haru] ERROR: %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" = 0 ] || die "run it with sudo"

haru() {
  docker compose --project-directory "$SRC/deploy" -f "$SRC/deploy/docker-compose.prod.yml" \
    --env-file "$COMPOSE_ENV" "$@"
}

install_wrapper() {
  local dir="${HARU_BIN_DIR:-/usr/local/bin}"
  mkdir -p "$dir"
  cat > "$dir/haru" <<WRAP
#!/bin/sh
# docker compose for the Haru stack, e.g.:  sudo haru ps | sudo haru logs -f api
exec docker compose --project-directory $BASE/src/deploy \\
  -f $BASE/src/deploy/docker-compose.prod.yml --env-file $BASE/compose.env "\$@"
WRAP
  chmod 755 "$dir/haru"
}

install_mcp_service() {
  mkdir -p "$BASE/mcp"
  chmod 755 "$BASE/mcp"
  [ -n "$(kv_get MCP_SECRET)" ] || kv_set MCP_SECRET "$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')"
  chmod 755 "$SRC/deploy/haru_vm_mcp.py"
  if command -v systemctl >/dev/null 2>&1 && [ -d /etc/systemd/system ]; then
    cat > /etc/systemd/system/haru-mcp.service <<UNIT
[Unit]
Description=Haru VM Remote MCP Server
After=network.target docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$SRC
EnvironmentFile=$COMPOSE_ENV
Environment=HARU_BASE=$BASE
Environment=MCP_SOCK_PATH=$BASE/mcp/mcp.sock
ExecStart=/usr/bin/python3 $SRC/deploy/haru_vm_mcp.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
UNIT
    systemctl daemon-reload || true
    systemctl enable haru-mcp.service >/dev/null 2>&1 || true
    systemctl restart haru-mcp.service || true
  fi
}

kv_get() { [ -f "$COMPOSE_ENV" ] && grep -E "^$1=" "$COMPOSE_ENV" | tail -n1 | cut -d= -f2- || true; }

kv_set() {
  local tmp
  tmp="$(mktemp "$BASE/.compose.env.XXXXXX")"
  { [ -f "$COMPOSE_ENV" ] && grep -v -E "^$1=" "$COMPOSE_ENV" || true; printf '%s=%s\n' "$1" "$2"; } > "$tmp"
  chmod 600 "$tmp"
  mv "$tmp" "$COMPOSE_ENV"
}

run_api() { haru run --rm -T --no-deps api "$@"; }

wait_for_db() {
  haru up -d --wait --wait-timeout 180 db redis
}

# Read the revision of the newest (or the named) backup, from the bucket named in .env.prod.
backup_revision() {
  local day="$1" out rev
  if ! out="$(run_api python -c "
import sys
from app.services.db_backup import GcsStore, read_manifest
day = None if sys.argv[1] == 'latest' else sys.argv[1]
m = read_manifest(GcsStore(), day)
print('REVISION', m['alembic_revision'])
print('DAY', m['day'])
" "${day:-latest}")"; then
    die "could not read a backup from the bucket. Check AUDIO_STORAGE / AUDIO_GCS_BUCKET / AUDIO_GCS_CREDENTIALS in .env.prod, and that a backup exists (backup/latest.json). To start with an EMPTY database instead: deploy with --fresh."
  fi
  rev="$(printf '%s\n' "$out" | sed -n 's/^REVISION //p' | tail -n1)"
  [ -n "$rev" ] && [ "$rev" != "None" ] || die "the backup has no alembic revision: $out"
  log "backup of $(printf '%s\n' "$out" | sed -n 's/^DAY //p' | tail -n1), database revision $rev"
  BACKUP_REVISION="$rev"
}

psql_admin() { # psql_admin <sql>...   one statement per -c, run in the maintenance database
  local args=() q
  for q in "$@"; do args+=(-c "$q"); done
  haru exec -T db psql -U haru -d postgres -v ON_ERROR_STOP=1 "${args[@]}"
}

# Load a backup WITHOUT touching the current database until the new one is complete:
#   scratch database "haru_restore" -> migrate to the backup's revision -> load the backup
#   -> only then rename: haru -> haru_old (kept), haru_restore -> haru.
# If anything fails before the rename, the database you had is exactly as it was.
load_backup() {
  local day="$1" args=() url
  if [ -n "$day" ]; then args=(--day "$day"); fi
  backup_revision "$day"
  url="postgresql+asyncpg://haru:$(kv_get POSTGRES_PASSWORD)@db:5432/haru_restore"
  log "preparing a scratch database"
  psql_admin "DROP DATABASE IF EXISTS haru_restore WITH (FORCE)" "CREATE DATABASE haru_restore"
  log "migrating it to $BACKUP_REVISION (the revision the backup was taken at)"
  haru run --rm -T --no-deps -e "DATABASE_URL=$url" api alembic upgrade "$BACKUP_REVISION"
  log "loading the backup into it"
  haru run --rm -T --no-deps -e "DATABASE_URL=$url" api python -m app.services.db_backup restore "${args[@]}" --force --yes \
    || die "the backup was NOT loaded; the database you had was not touched. Nothing is started."
  log "swapping it in (what was there before is kept as the database haru_old)"
  psql_admin "DROP DATABASE IF EXISTS haru_old WITH (FORCE)"
  psql_admin "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'haru' AND pid <> pg_backend_pid()" \
    "ALTER DATABASE haru RENAME TO haru_old" "ALTER DATABASE haru_restore RENAME TO haru"
  touch "$MARKER"
}

install_incoming() {
  [ -f "$HERE/haru-src.tgz" ] && [ -f "$HERE/env.prod" ] || die "haru-src.tgz / env.prod are missing next to this script"
  mkdir -p "$BASE"
  chmod 755 "$BASE"
  install -m 600 -o root -g root "$HERE/env.prod" "$BASE/.env.prod"
  rm -rf "$BASE/src.new"
  mkdir "$BASE/src.new"
  tar -xzf "$HERE/haru-src.tgz" -C "$BASE/src.new"
  [ -f "$BASE/src.new/deploy/docker-compose.prod.yml" ] || die "the tarball has no deploy/docker-compose.prod.yml"
  rm -rf "$BASE/src.prev"
  [ -d "$SRC" ] && mv "$SRC" "$BASE/src.prev"
  mv "$BASE/src.new" "$SRC"
}

https_check() {
  local domain url
  domain="$(kv_get HARU_DOMAIN)"
  url="https://$domain/healthz"
  log "waiting for $url (the first certificate takes up to a minute)"
  for _ in $(seq 1 36); do
    if curl -fsS --max-time 10 "$url" 2>/dev/null; then
      printf '\n'
      return 0
    fi
    sleep 5
  done
  return 1
}

cmd_deploy() {
  local domain="" fresh=0 day=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --domain) domain="$2"; shift 2 ;;
      --fresh) fresh=1; shift ;;
      --day) day="$2"; shift 2 ;;
      *) die "unknown option $1" ;;
    esac
  done
  install_incoming
  install_wrapper
  [ -f "$COMPOSE_ENV" ] || { umask 077; printf 'POSTGRES_PASSWORD=%s\n' "$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')" > "$COMPOSE_ENV"; }
  [ -n "$domain" ] && kv_set HARU_DOMAIN "$domain"
  [ -n "$(kv_get HARU_DOMAIN)" ] || die "no domain: pass --domain"
  install_mcp_service

  log "building the image"
  haru build api

  log "starting Postgres and Redis"
  wait_for_db

  if [ -f "$MARKER" ]; then
    log "the database already holds your data: not touching it"
  elif [ "$fresh" = 1 ]; then
    log "--fresh: starting with an empty database (lessons are loaded when the API starts)"
    run_api alembic upgrade head
    touch "$MARKER"
  else
    log "first deploy: loading the newest backup from the bucket"
    load_backup "$day"
  fi

  log "alembic upgrade head"
  run_api alembic upgrade head

  log "starting api, worker, Caddy"
  if ! haru up -d --wait --wait-timeout 420; then
    haru ps || true
    haru logs --tail 60 api worker || true
    die "the stack did not come up (logs above)"
  fi
  haru exec -T caddy caddy reload --config /etc/caddy/Caddyfile >/dev/null 2>&1 || true
  haru logs --no-log-prefix --tail 400 api 2>&1 | grep -i 'lesson_seed' | tail -n 3 || true

  if https_check; then
    log "OK  https://$(kv_get HARU_DOMAIN)"
  else
    haru ps || true
    haru logs --tail 40 caddy || true
    die "HTTPS does not answer yet. Ports 80 and 443 open? The name $(kv_get HARU_DOMAIN) points at this VM? (logs above)"
  fi

  rm -f "$HERE/haru-src.tgz" "$HERE/env.prod"
  docker image prune -f >/dev/null 2>&1 || true
}

cmd_restore() {
  local day=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --day) day="$2"; shift 2 ;;
      *) die "unknown option $1" ;;
    esac
  done
  [ -f "$MARKER" ] || die "nothing is deployed here yet"
  log "stopping api and worker"
  haru stop api worker
  wait_for_db
  load_backup "$day"
  run_api alembic upgrade head
  haru up -d --wait --wait-timeout 420
  log "restored; api and worker are running again"
}

cmd_backup() { run_api python -m app.services.db_backup backup; }

cmd_status() {
  haru ps
  echo
  df -h / | tail -n1
  free -m | sed -n '1,3p'
  echo
  curl -fsS --max-time 10 "https://$(kv_get HARU_DOMAIN)/healthz" && echo || echo "(https healthz does not answer)"
}

cmd_mcp_url() {
  printf 'https://%s/mcp/%s\n' "$(kv_get HARU_DOMAIN)" "$(kv_get MCP_SECRET)"
}

sub="${1:-}"
[ $# -gt 0 ] && shift
case "$sub" in
  deploy) cmd_deploy "$@" ;;
  restore) cmd_restore "$@" ;;
  backup) cmd_backup "$@" ;;
  status) cmd_status "$@" ;;
  mcp-url) cmd_mcp_url "$@" ;;
  *) die "usage: remote-up.sh deploy|restore|backup|status|mcp-url" ;;
esac
