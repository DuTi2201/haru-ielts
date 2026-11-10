#!/usr/bin/env bash
# Haru -> one GCP VM, one command.   Run it from the repo root (a Mac/Linux terminal or Cloud Shell).
#
#   ./deploy/haru-gcp.sh up            create the VM (first time) and put the source + data in
#   ./deploy/haru-gcp.sh ship          after a code change: send the new source, rebuild, restart
#   ./deploy/haru-gcp.sh restore       replace the data with a backup from the bucket  (--day YYYY-MM-DD)
#   ./deploy/haru-gcp.sh backup-now    back up to the bucket right now
#   ./deploy/haru-gcp.sh status | logs [service] [-f] | ssh | url | destroy
#
# Options: --yes (no questions)  --fresh (start with an EMPTY database)  --day YYYY-MM-DD  --dry-run
# Settings, as environment variables (all optional):
#   HARU_PROJECT  GCP project            (default: the one `gcloud config` points at)
#   HARU_ZONE     us-central1-a          HARU_MACHINE  e2-small   (e2-medium = 4 GB RAM, ~US$12 more)
#   HARU_VM       haru-vm                HARU_DISK_GB  30
#   HARU_DOMAIN   your own domain whose A record points at the VM's IP (default: <ip>.sslip.io)
#   HARU_ENV_FILE path of the secrets file (default: ./.env.prod, see deploy/env.prod.example)
#
# Your secrets never touch git or this script: they sit in .env.prod on YOUR machine and travel
# over ssh to the VM (mode 600). Data comes from the private bucket's newest nightly backup.
# bash 3.2 compatible (macOS).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

VM_NAME="${HARU_VM:-haru-vm}"
ZONE="${HARU_ZONE:-us-central1-a}"
REGION="${ZONE%-*}"
MACHINE="${HARU_MACHINE:-e2-small}"
DISK_GB="${HARU_DISK_GB:-30}"
IP_NAME="${HARU_IP_NAME:-haru-ip}"
NETWORK="${HARU_NETWORK:-default}"
SSH_RANGES="${HARU_SSH_SOURCE_RANGES:-0.0.0.0/0}"
TAG="haru-web"
ENV_FILE="${HARU_ENV_FILE:-$ROOT/.env.prod}"
PROJECT="${HARU_PROJECT:-}"
DRY_RUN="${DRY_RUN:-0}"
YES="${HARU_YES:-0}"
FRESH=0
DAY=""

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33m!! %s\033[0m\n' "$*" >&2; }
die() { printf '\033[31mLỗi: %s\033[0m\n' "$*" >&2; exit 1; }

# --- running gcloud (or only printing what would run) ----------------------------------------
g() {
  if [ "$DRY_RUN" = 1 ]; then
    printf '  + gcloud --project %s %s\n' "$PROJECT" "$*"
    return 0
  fi
  gcloud --project "$PROJECT" "$@"
}

# Reads: in --dry-run they answer "nothing exists yet" so the whole plan is shown.
vm_status() {
  [ "$DRY_RUN" = 1 ] && return 0
  gcloud --project "$PROJECT" compute instances describe "$VM_NAME" --zone "$ZONE" \
    --format='value(status)' 2>/dev/null || true
}
exists() { # exists <firewall-rules|addresses> <name> [extra gcloud args]
  [ "$DRY_RUN" = 1 ] && return 1
  gcloud --project "$PROJECT" compute "$1" describe "$2" "${@:3}" >/dev/null 2>&1
}
vm_ip() {
  [ "$DRY_RUN" = 1 ] && { echo "203.0.113.10"; return 0; }
  gcloud --project "$PROJECT" compute addresses describe "$IP_NAME" --region "$REGION" \
    --format='value(address)'
}

ssh_run() { # run a command on the VM
  g compute ssh "$VM_NAME" --zone "$ZONE" --quiet --command "$*" -- -o ServerAliveInterval=30
}

confirm() {
  [ "$YES" = 1 ] && return 0
  local ans
  printf '%s [y/N] ' "$1"
  read -r ans || ans=""
  case "$ans" in y|Y|yes|YES) return 0 ;; *) return 1 ;; esac
}

# --- the secrets file: checked here, before anything costs money; values are never printed ---
env_raw() { # raw value of KEY (last occurrence), "" if missing
  [ -f "$ENV_FILE" ] || return 0
  grep -Ei "^[[:space:]]*(export[[:space:]]+)?$1[[:space:]]*=" "$ENV_FILE" | tail -n 1 \
    | sed -E "s/^[[:space:]]*(export[[:space:]]+)?$1[[:space:]]*=[[:space:]]*//" || true
}
env_clean() { # value without surrounding quotes/blanks
  local v
  v="$(env_raw "$1")"
  v="${v%"${v##*[![:space:]]}"}"
  v="${v#[\'\"]}"
  v="${v%[\'\"]}"
  printf '%s' "$v"
}

check_env_file() {
  [ -f "$ENV_FILE" ] || die "không thấy file bí mật $ENV_FILE. Tạo nó từ deploy/env.prod.example (dán các biến từ Railway > Raw Editor), rồi chạy lại."
  chmod 600 "$ENV_FILE" 2>/dev/null || true
  local bad=0 k v
  for k in JWT_SECRET GEMINI_API_KEY; do
    [ -n "$(env_clean "$k")" ] || { warn "$k trống hoặc thiếu trong $ENV_FILE"; bad=1; }
  done
  v="$(env_clean JWT_SECRET)"
  case "$v" in
    *change-me*|dev-secret*) warn "JWT_SECRET vẫn là giá trị mẫu"; bad=1 ;;
  esac
  if [ -n "$v" ] && [ "${#v}" -lt 24 ]; then warn "JWT_SECRET quá ngắn (dưới 24 ký tự)"; bad=1; fi
  if [ "$FRESH" = 0 ]; then
    [ "$(env_clean AUDIO_STORAGE)" = "gcs" ] || { warn "AUDIO_STORAGE phải là gcs (dữ liệu nằm ở bucket)"; bad=1; }
    for k in AUDIO_GCS_BUCKET AUDIO_GCS_CREDENTIALS; do
      [ -n "$(env_clean "$k")" ] || { warn "$k trống hoặc thiếu trong $ENV_FILE"; bad=1; }
    done
  fi
  # The service-account JSON must sit on ONE line in single quotes, or docker passes it on garbled.
  v="$(env_raw AUDIO_GCS_CREDENTIALS)"
  if [ -n "$v" ]; then
    case "$v" in
      \'*\') : ;;
      *) warn "AUDIO_GCS_CREDENTIALS phải nằm trên MỘT dòng, bọc bằng dấu nháy đơn '...'. Tự sửa: dán giá trị vào  python3 deploy/gcs-key-line.py  (xem deploy/README.md)"; bad=1 ;;
    esac
    if command -v python3 >/dev/null 2>&1; then
      if ! printf '%s' "$v" | python3 -c '
import json, sys
raw = sys.stdin.read().strip()
if raw[:1] == raw[-1:] == chr(39):
    raw = raw[1:-1]
d = json.loads(raw)
assert d.get("type") == "service_account" and d.get("private_key") and d.get("client_email")
' >/dev/null 2>&1; then
        warn "AUDIO_GCS_CREDENTIALS không phải JSON service-account hợp lệ trên một dòng"; bad=1
      fi
    fi
  fi
  [ -n "$(env_clean CORS_ORIGINS)" ] || warn "CORS_ORIGINS trống: chỉ tên miền *.lovable.app (CORS_ORIGIN_REGEX) được phép gọi API"
  if grep -Eqi '^[[:space:]]*(DATABASE_URL|REDIS_URL)[[:space:]]*=' "$ENV_FILE"; then
    warn "DATABASE_URL / REDIS_URL trong .env.prod sẽ bị bỏ qua (VM dùng Postgres và Redis của chính nó)"
  fi
  [ "$bad" = 0 ] || die "sửa $ENV_FILE rồi chạy lại (chưa tạo gì trên GCP)."
}

# --- preflight --------------------------------------------------------------------------------
preflight() {
  command -v tar >/dev/null 2>&1 || die "thiếu tar"
  if [ "$DRY_RUN" = 1 ]; then
    [ -n "$PROJECT" ] || PROJECT="(dự-án-gcloud-hiện-tại)"
    return 0
  fi
  command -v gcloud >/dev/null 2>&1 || die "chưa cài gcloud. Mở Cloud Shell (console.cloud.google.com, biểu tượng >_ ) hoặc cài Google Cloud CLI rồi chạy 'gcloud auth login'."
  [ -n "$PROJECT" ] || PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
  [ -n "$PROJECT" ] && [ "$PROJECT" != "(unset)" ] || die "chưa chọn dự án GCP: gcloud config set project <ID> (hoặc HARU_PROJECT=<ID>)"
  [ -n "$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null)" ] \
    || die "chưa đăng nhập gcloud: chạy 'gcloud auth login'"
}

ensure_infra() {
  say "Bật Compute Engine API"
  g services enable compute.googleapis.com

  if exists firewall-rules "$TAG"; then
    say "Firewall $TAG đã có"
  else
    say "Mở cổng 80/443 (HTTPS) cho VM"
    g compute firewall-rules create "$TAG" --network "$NETWORK" --direction INGRESS --action allow \
      --rules tcp:80,tcp:443 --target-tags "$TAG" --source-ranges 0.0.0.0/0
  fi
  if exists firewall-rules haru-ssh; then
    :
  else
    say "Mở cổng ssh (22) cho VM"
    g compute firewall-rules create haru-ssh --network "$NETWORK" --direction INGRESS --action allow \
      --rules tcp:22 --target-tags "$TAG" --source-ranges "$SSH_RANGES"
  fi

  if exists addresses "$IP_NAME" --region "$REGION"; then
    say "IP tĩnh $IP_NAME đã có"
  else
    say "Giữ một IP tĩnh ($IP_NAME)"
    g compute addresses create "$IP_NAME" --region "$REGION"
  fi

  if [ -n "$(vm_status)" ]; then
    say "VM $VM_NAME đã có (trạng thái $(vm_status))"
    [ "$(vm_status)" = "TERMINATED" ] && { say "Bật VM lại"; g compute instances start "$VM_NAME" --zone "$ZONE"; }
  else
    say "Tạo VM $VM_NAME ($MACHINE, đĩa ${DISK_GB} GB, Debian 12)"
    # No service account on the VM: it needs no GCP access (the bucket key comes from .env.prod),
    # so a break-in there cannot reach your project.
    g compute instances create "$VM_NAME" --zone "$ZONE" --machine-type "$MACHINE" \
      --network "$NETWORK" --address "$IP_NAME" --tags "$TAG" \
      --image-family debian-12 --image-project debian-cloud \
      --boot-disk-size "${DISK_GB}GB" --boot-disk-type pd-balanced \
      --no-service-account --no-scopes \
      --metadata-from-file "startup-script=$HERE/vm-startup.sh"
  fi
}

wait_for_vm() {
  say "Đợi VM cài xong Docker (lần đầu mất 2-4 phút)"
  [ "$DRY_RUN" = 1 ] && { ssh_run "test -f /var/lib/haru/ready"; return 0; }
  for _ in $(seq 1 60); do
    if ssh_run "test -f /var/lib/haru/ready" >/dev/null 2>&1; then
      return 0
    fi
    sleep 10
  done
  die "VM chưa sẵn sàng sau 10 phút. Xem: ./deploy/haru-gcp.sh ssh  rồi  sudo tail /var/log/haru-startup.log"
}

make_tarball() { # make_tarball <dir>   -> <dir>/haru-src.tgz and <dir>/env.prod
  local d="$1"
  export COPYFILE_DISABLE=1   # macOS tar: no ._* files
  tar -czf "$d/haru-src.tgz" -C "$ROOT" \
    --exclude='./.git' --exclude='./.venv' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.env' --exclude='.env.*' --exclude='./.pytest_cache' --exclude='*.egg-info' \
    --exclude='./node_modules' --exclude='.DS_Store' .
  # List first, grep after: "tar | grep -q" under pipefail reports a match as a failure (SIGPIPE).
  local listing
  listing="$(tar -tzf "$d/haru-src.tgz")"
  if grep -Eq '(^|/)\.env($|\.)' <<<"$listing"; then
    die "một file .env lọt vào gói mã nguồn - dừng lại, không gửi gì cả."
  fi
  grep -q 'deploy/docker-compose.prod.yml' <<<"$listing" || die "gói mã nguồn thiếu deploy/docker-compose.prod.yml (chạy script từ thư mục mã nguồn backend?)"
  ( umask 077; cp "$ENV_FILE" "$d/env.prod" )
  cp "$HERE/remote-up.sh" "$d/remote-up.sh"
}

ship() { # ship <domain-or-empty>
  local domain="$1" tmp opts
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/haru-ship.XXXXXX")"
  trap 'rm -rf "$tmp"' EXIT
  say "Đóng gói mã nguồn (không có .git / .env) và đọc file bí mật"
  make_tarball "$tmp"
  say "Gửi lên VM (mã nguồn + .env.prod qua ssh)"
  ssh_run "rm -rf haru-incoming && mkdir -m 700 haru-incoming"
  g compute scp --zone "$ZONE" --quiet "$tmp/haru-src.tgz" "$tmp/env.prod" "$tmp/remote-up.sh" "$VM_NAME:haru-incoming/"
  opts=""
  [ -n "$domain" ] && opts="$opts --domain $domain"
  [ "$FRESH" = 1 ] && opts="$opts --fresh"
  [ -n "$DAY" ] && opts="$opts --day $DAY"
  say "Build + chạy trên VM (build lần đầu mất vài phút)"
  ssh_run "sudo bash haru-incoming/remote-up.sh deploy$opts"
  rm -rf "$tmp"
  trap - EXIT
}

default_domain() {
  if [ -n "${HARU_DOMAIN:-}" ]; then printf '%s' "$HARU_DOMAIN"; else printf '%s.sslip.io' "$(vm_ip | tr '.' '-')"; fi
}

need_vm() {
  [ -n "$(vm_status)" ] || [ "$DRY_RUN" = 1 ] || die "chưa có VM $VM_NAME - chạy './deploy/haru-gcp.sh up' trước"
}

# --- commands ---------------------------------------------------------------------------------
cmd_up() {
  preflight
  check_env_file
  local what bucket
  bucket="$(env_clean AUDIO_GCS_BUCKET)"
  what="khôi phục từ bản sao lưu mới nhất trong bucket '$bucket'"
  if [ "$FRESH" = 1 ]; then what="BẮT ĐẦU VỚI DATABASE TRỐNG (--fresh)"; fi
  if [ -n "$DAY" ]; then what="khôi phục bản sao lưu ngày $DAY trong bucket '$bucket'"; fi
  cat <<EOF

  Dự án GCP : $PROJECT
  VM        : $VM_NAME  ($MACHINE, $ZONE, đĩa $DISK_GB GB)  + IP tĩnh $IP_NAME
  Dữ liệu   : $what
  Chi phí   : ~US\$18/tháng với e2-small (ước tính: VM + đĩa + IP; xem bảng giá GCP)

EOF
  confirm "Tiếp tục?" || die "đã hủy, chưa tạo gì."
  ensure_infra
  wait_for_vm
  local domain
  domain="$(default_domain)"
  ship "$domain"
  say "Xong."
  cat <<EOF

  API       : https://$domain
  Kiểm tra  : ./deploy/haru-gcp.sh status
  Frontend  : đặt VITE_API_BASE_URL = https://$domain  (Lovable > Settings), rồi Publish.
  Đẩy code mới sau này chỉ cần: ./deploy/haru-gcp.sh ship

EOF
}

cmd_ship() {
  preflight
  need_vm
  check_env_file
  ship "${HARU_DOMAIN:-}"
}

cmd_restore() {
  preflight
  need_vm
  say "Khôi phục sẽ XÓA dữ liệu hiện có trên VM và thay bằng bản sao lưu ${DAY:-mới nhất} trong bucket."
  confirm "Chắc chắn?" || die "đã hủy."
  ssh_run "sudo /opt/haru/src/deploy/remote-up.sh restore${DAY:+ --day $DAY}"
}

cmd_backup() { preflight; need_vm; ssh_run "sudo /opt/haru/src/deploy/remote-up.sh backup"; }
cmd_status() {
  preflight
  need_vm
  say "VM: $(vm_status)   IP: $(vm_ip)   URL: https://$(default_domain)"
  ssh_run "sudo /opt/haru/src/deploy/remote-up.sh status"
}
cmd_logs() {
  preflight
  need_vm
  ssh_run "sudo haru logs --tail 150 $*"
}
cmd_ssh() { preflight; need_vm; g compute ssh "$VM_NAME" --zone "$ZONE"; }
cmd_url() { preflight; echo "https://$(default_domain)"; }

cmd_destroy() {
  preflight
  need_vm
  warn "Xóa VM $VM_NAME, đĩa của nó (cả database trên VM), IP tĩnh và firewall. Bản sao lưu trong bucket KHÔNG bị đụng tới."
  if [ "$YES" != 1 ]; then
    local typed
    printf 'Gõ tên VM (%s) để xác nhận: ' "$VM_NAME"
    read -r typed || typed=""
    [ "$typed" = "$VM_NAME" ] || die "đã hủy."
  fi
  g compute instances delete "$VM_NAME" --zone "$ZONE" --delete-disks all --quiet
  exists addresses "$IP_NAME" --region "$REGION" && g compute addresses delete "$IP_NAME" --region "$REGION" --quiet
  exists firewall-rules "$TAG" && g compute firewall-rules delete "$TAG" --quiet
  exists firewall-rules haru-ssh && g compute firewall-rules delete haru-ssh --quiet
  say "Đã xóa."
}

usage() { awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; }

CMD="${1:-}"
[ $# -gt 0 ] && shift
REST=""
while [ $# -gt 0 ]; do
  case "$1" in
    --yes|-y) YES=1 ;;
    --fresh) FRESH=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --day) [ $# -ge 2 ] || die "--day cần YYYY-MM-DD"; DAY="$2"; shift ;;
    *) REST="$REST $1" ;;
  esac
  shift
done
case "$DAY" in ""|[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) : ;; *) die "--day phải có dạng YYYY-MM-DD" ;; esac

case "$CMD" in
  up) cmd_up ;;
  ship) cmd_ship ;;
  restore) cmd_restore ;;
  backup-now) cmd_backup ;;
  status) cmd_status ;;
  logs) cmd_logs $REST ;;
  ssh) cmd_ssh ;;
  url) cmd_url ;;
  destroy) cmd_destroy ;;
  ""|-h|--help|help) usage ;;
  *) usage; die "lệnh lạ: $CMD" ;;
esac
