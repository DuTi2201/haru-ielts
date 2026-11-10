#!/usr/bin/env python3
"""Turn a Google service-account key into the ONE line .env.prod needs.

Why: docker reads a double-quoted value and turns every \\n in it into a real line break, which
breaks the key's JSON. Inside single quotes it stays intact. Feed this the key however you have it
(the downloaded .json file, or the value copied from Railway, quoted or not, one line or many):

    python3 deploy/gcs-key-line.py key.json  >> .env.prod
    pbpaste | python3 deploy/gcs-key-line.py >> .env.prod        # macOS clipboard

It prints only the AUDIO_GCS_CREDENTIALS=... line; nothing is written anywhere else."""
import json
import sys


def load(text: str) -> dict:
    text = text.strip()
    if text.upper().startswith("AUDIO_GCS_CREDENTIALS="):
        text = text.split("=", 1)[1].strip()
    if len(text) >= 2 and text[0] == text[-1] == "'":
        text = text[1:-1]
    # the value may itself be a JSON string holding the JSON (\"type\": ...)
    candidates = [text]
    if len(text) >= 2 and text[0] == text[-1] == '"':
        candidates.append(text[1:-1].replace('\\"', '"').replace("\\\\", "\\"))
    for cand in candidates:
        for strict in (True, False):
            try:
                value = json.loads(cand, strict=strict)
            except ValueError:
                continue
            if isinstance(value, str):  # JSON inside a JSON string
                try:
                    value = json.loads(value, strict=False)
                except ValueError:
                    continue
            if isinstance(value, dict):
                return value
    raise SystemExit("this does not look like a service-account key (JSON)")


def main() -> int:
    raw = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
    key = load(raw)
    for field in ("type", "private_key", "client_email"):
        if not key.get(field):
            raise SystemExit(f"the key has no '{field}': wrong file?")
    if key["type"] != "service_account":
        raise SystemExit("type is not service_account")
    # compact, and private_key's line breaks stay as the two characters \n
    print("AUDIO_GCS_CREDENTIALS='" + json.dumps(key, separators=(",", ":")) + "'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
