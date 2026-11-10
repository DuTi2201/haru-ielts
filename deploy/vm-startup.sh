#!/bin/bash
# Runs once, as root, the first time the VM boots (GCE "startup-script" metadata).
# Installs Docker + the compose plugin, adds 2 GB of swap, turns on security updates.
# Safe to run again: it stops at once when /var/lib/haru/ready exists.
set -euo pipefail
exec > >(tee -a /var/log/haru-startup.log) 2>&1

READY=/var/lib/haru/ready
mkdir -p /var/lib/haru
if [ -f "$READY" ]; then
  echo "[haru-startup] already done"
  exit 0
fi
echo "[haru-startup] start $(date -u +%FT%TZ)"
export DEBIAN_FRONTEND=noninteractive

# --- swap: the VM has 2 GB of RAM, Postgres + the worker + ffmpeg can touch it ----------------
if ! swapon --show=NAME --noheadings | grep -q '^/swapfile$'; then
  if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
  fi
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
cat > /etc/sysctl.d/99-haru.conf <<'SYSCTL'
vm.swappiness = 20
vm.overcommit_memory = 1
SYSCTL
sysctl --system >/dev/null

# --- Docker (official apt repository) ---------------------------------------------------------
apt-get update
apt-get install -y ca-certificates curl gnupg unattended-upgrades
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'JSON'
{ "log-driver": "json-file", "log-opts": { "max-size": "10m", "max-file": "3" } }
JSON
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

# --- security updates by themselves ------------------------------------------------------------
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'APT'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT

mkdir -p /opt/haru
docker --version
docker compose version
touch "$READY"
echo "[haru-startup] done $(date -u +%FT%TZ)"
