#!/bin/sh
# Publish a built site (the journey repo's .output/public) on the VM, as root:
#     sh /opt/haru-ielts/src/deploy/site-deploy.sh /opt/build/journey/.output/public
# Copies the files, rewrites the Caddy site block (the page's CSP lists the inline scripts of THIS
# build by hash, see make_site_caddy.py), checks the configuration and reloads Caddy. A step that
# fails stops the script; the site that was live stays live until the copy.
set -eu
SRC="${1:?path of the built site}"
MCP=/opt/haru/mcp
DOMAIN="${HARU_IELTS_DOMAIN:-ielts.34-9-216-231.sslip.io}"
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SRC/index.html" ] || { echo "no index.html in $SRC" >&2; exit 1; }

mkdir -p "$MCP/caddy"
python3 "$HERE/make_site_caddy.py" "$SRC" "$DOMAIN" > "$MCP/caddy/ielts.caddy.new"
cp "$MCP/caddy/ielts.caddy" "$MCP/caddy/ielts.caddy.prev" 2>/dev/null || true
mv "$MCP/caddy/ielts.caddy.new" "$MCP/caddy/ielts.caddy"
# Caddy reads the main file from a copy next to the site blocks: the container's own
# /etc/caddy/Caddyfile is a bind mount of a single file, which goes stale when that file is replaced.
cp /opt/haru/src/deploy/Caddyfile "$MCP/caddy/Caddyfile.main"
# The Haru Korean Caddyfile does not import this site; add the import here, or a reload drops the site.
grep -q 'import /run/haru-mcp/caddy/ielts.caddy' "$MCP/caddy/Caddyfile.main" || \
  printf '\n# Haru English (IELTS) site block, written by haru-ielts/deploy/site-deploy.sh\nimport /run/haru-mcp/caddy/ielts.caddy\n' >> "$MCP/caddy/Caddyfile.main"
if ! grep -q 'import /run/haru-mcp/caddy/ielts.caddy' "$MCP/caddy/Caddyfile.main"; then echo "no import line for the site" >&2; exit 1; fi
if ! docker exec haru-caddy-1 caddy validate --config /run/haru-mcp/caddy/Caddyfile.main --adapter caddyfile >/dev/null 2>&1; then
  echo "Caddy refused the new configuration; keeping the previous one" >&2
  [ -f "$MCP/caddy/ielts.caddy.prev" ] && cp "$MCP/caddy/ielts.caddy.prev" "$MCP/caddy/ielts.caddy"
  exit 1
fi
rm -rf "$MCP/ielts-site.prev" && cp -a "$MCP/ielts-site" "$MCP/ielts-site.prev"
rm -rf "$MCP/ielts-site"/* && cp -a "$SRC"/. "$MCP/ielts-site"/
docker exec haru-caddy-1 caddy reload --config /run/haru-mcp/caddy/Caddyfile.main --adapter caddyfile
echo "site published; Caddy reloaded"
