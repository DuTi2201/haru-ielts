#!/usr/bin/env python3
"""Write the Caddy site block of Haru English (IELTS), with its security headers.

    python3 make_site_caddy.py <site dir> <domain> > /opt/haru/mcp/caddy/ielts.caddy

The page's Content-Security-Policy allows scripts from the site itself plus the few inline scripts
of index.html, each by its SHA-256 hash. Those hashes change with every build of the site, so this
runs on every site deploy (deploy/site-deploy.sh does it) and Caddy is reloaded after it. A site
copied in without this step shows a blank page: the browser refuses the new inline scripts.
"""
import base64
import hashlib
import re
import sys
from pathlib import Path


def inline_script_hashes(html: str) -> list[str]:
    out = []
    for attrs, body in re.findall(r"<script([^>]*)>(.*?)</script>", html, re.S):
        if body and "src=" not in attrs:
            digest = base64.b64encode(hashlib.sha256(body.encode("utf8")).digest()).decode()
            if f"'sha256-{digest}'" not in out:
                out.append(f"'sha256-{digest}'")
    return out


def csp(html: str) -> str:
    return "; ".join(
        [
            "default-src 'self'",
            # youtube.com: the pronunciation course loads YouTube's iframe API (components/pron/YouTubePlayer)
            "script-src 'self' https://www.youtube.com " + " ".join(inline_script_hashes(html)),
            # <style> tags are added at run time by the toast and chart components
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' data: https://fonts.gstatic.com",
            "img-src 'self' data: blob: https://i.ytimg.com",
            # long recordings are played straight from the private bucket through a signed link
            "media-src 'self' blob: https://storage.googleapis.com",
            "connect-src 'self'",
            "frame-src https://www.youtube-nocookie.com https://www.youtube.com",
            "worker-src 'self'",
            "manifest-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
    )


def block(site: Path, domain: str) -> str:
    policy = csp((site / "index.html").read_text(encoding="utf8"))
    assert '"' not in policy
    return f"""# Written by haru-ielts/deploy/make_site_caddy.py on a site deploy. Do not edit by hand.
{domain} {{
	encode gzip

	header {{
		Strict-Transport-Security "max-age=31536000"
		X-Content-Type-Options "nosniff"
		X-Frame-Options "DENY"
		Referrer-Policy "strict-origin-when-cross-origin"
		Permissions-Policy "camera=(), geolocation=(), payment=(), usb=(), microphone=(self)"
		Cross-Origin-Opener-Policy "same-origin"
		-Server
	}}

	# the API's route list (/docs, /openapi.json) is not published
	@backend path /api/* /healthz
	handle @backend {{
		header Content-Security-Policy "default-src 'none'; frame-ancestors 'none'"
		reverse_proxy unix//run/haru-mcp/ielts-api.sock {{
			flush_interval -1
		}}
	}}

	handle {{
		header Content-Security-Policy "{policy}"
		root * /run/haru-mcp/ielts-site
		try_files {{path}} /index.html
		file_server
	}}
}}
"""


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.stdout.write(block(Path(sys.argv[1]), sys.argv[2]))
