"""Object storage for the recordings made from a text (see models.TextAudio): a PRIVATE Google
Cloud Storage bucket, reached through its JSON API with a service account.

Why this and not the repository: audio files are binary, large and endless — in git they bloat
the repo for good and a published history is never rewritten. Why not Google Drive: a service
account has no Drive quota of its own. A bucket is the Google-side place meant for this.

Nothing here is secret except `AUDIO_GCS_CREDENTIALS` (the service-account JSON), which is read
from the environment only — a Railway variable — and never logged. Unset, `backend()` is "db" and
the bytes stay in the Postgres row, exactly as the other recordings do."""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import urllib.parse
from collections import OrderedDict
from datetime import datetime, timezone

import httpx

from app.core.config import settings

GCS_SCOPE = "https://www.googleapis.com/auth/devstorage.read_write"
_UPLOAD_URL = "https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"
_OBJECT_URL = "https://storage.googleapis.com/storage/v1/b/{bucket}/o/{name}"
# a lesson podcast is tens of megabytes: allow time to move it, but fail fast if the bucket is unreachable
_TIMEOUT = httpx.Timeout(120.0, connect=10.0)

log = logging.getLogger(__name__)

_lock = threading.Lock()
_credentials = None
_credentials_raw = ""


class StoreError(RuntimeError):
    """The object store refused or could not be reached. The caller keeps the bytes in the row."""


def gcs_configured() -> bool:
    return bool(settings.AUDIO_GCS_BUCKET.strip() and settings.AUDIO_GCS_CREDENTIALS.strip())


def backend() -> str:
    """"gcs" only when it is asked for AND its bucket and credential are both set; otherwise "db"."""
    return "gcs" if settings.AUDIO_STORAGE.strip().lower() == "gcs" and gcs_configured() else "db"


def object_key(cache_key: str, ext: str, prefix: str = "tts") -> str:
    """Name of the object: the recording's own key, so a file can always be traced to its row.
    `prefix` keeps the kinds apart: "tts" for a text's recording, "lecture" for a lesson's."""
    return f"{prefix}/{cache_key.replace(':', '/')}.{ext}"


def _token() -> str:
    global _credentials, _credentials_raw
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except ImportError as exc:  # pragma: no cover - google-auth ships with google-genai
        raise StoreError("google-auth is not installed") from exc
    raw = settings.AUDIO_GCS_CREDENTIALS
    with _lock:
        if _credentials is None or raw != _credentials_raw:
            try:
                _credentials = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=[GCS_SCOPE])
            except Exception as exc:  # noqa: BLE001 - bad JSON (ValueError), missing fields (google-auth's own error)
                raise StoreError("AUDIO_GCS_CREDENTIALS is not a valid service-account JSON") from exc
            _credentials_raw = raw
        if not _credentials.valid:
            try:
                _credentials.refresh(Request())
            except Exception as exc:  # noqa: BLE001 - google-auth raises its own hierarchy
                raise StoreError("could not get an access token for the storage service account") from exc
        return _credentials.token


def _message(resp: httpx.Response) -> str:
    try:
        err = resp.json().get("error", {})
        return f"{err.get('status') or ''}: {err.get('message') or ''}".strip(": ")[:200]
    except Exception:  # noqa: BLE001 - a non-JSON error body
        return (resp.text or "")[:120]


def gcs_put(key: str, data: bytes, content_type: str) -> None:
    """Write one object (replacing one of the same name)."""
    headers = {"Authorization": f"Bearer {_token()}", "Content-Type": content_type}
    try:
        resp = httpx.post(
            _UPLOAD_URL.format(bucket=urllib.parse.quote(settings.AUDIO_GCS_BUCKET.strip(), safe="")),
            params={"uploadType": "media", "name": key},
            content=data,
            headers=headers,
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise StoreError(f"storage upload failed ({type(exc).__name__})") from exc
    if resp.status_code != 200:
        raise StoreError(f"storage upload HTTP {resp.status_code} — {_message(resp)}")


def gcs_get(key: str) -> bytes | None:
    """Read one object; None when there is no such object."""
    headers = {"Authorization": f"Bearer {_token()}"}
    url = _OBJECT_URL.format(
        bucket=urllib.parse.quote(settings.AUDIO_GCS_BUCKET.strip(), safe=""), name=urllib.parse.quote(key, safe="")
    )
    try:
        resp = httpx.get(url, params={"alt": "media"}, headers=headers, timeout=_TIMEOUT)
    except httpx.HTTPError as exc:
        raise StoreError(f"storage download failed ({type(exc).__name__})") from exc
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise StoreError(f"storage download HTTP {resp.status_code} — {_message(resp)}")
    return resp.content


def gcs_list(prefix: str) -> list[str]:
    """Names of every object whose name starts with `prefix` (all pages)."""
    bucket = urllib.parse.quote(settings.AUDIO_GCS_BUCKET.strip(), safe="")
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o"
    names: list[str] = []
    token = None
    while True:
        params = {"prefix": prefix, "fields": "items(name),nextPageToken"}
        if token:
            params["pageToken"] = token
        try:
            resp = httpx.get(url, params=params, headers={"Authorization": f"Bearer {_token()}"}, timeout=_TIMEOUT)
        except httpx.HTTPError as exc:
            raise StoreError(f"storage list failed ({type(exc).__name__})") from exc
        if resp.status_code != 200:
            raise StoreError(f"storage list HTTP {resp.status_code} — {_message(resp)}")
        body = resp.json()
        names += [item["name"] for item in body.get("items", [])]
        token = body.get("nextPageToken")
        if not token:
            return names


def gcs_delete(key: str) -> None:
    """Delete one object (already gone is fine)."""
    url = _OBJECT_URL.format(
        bucket=urllib.parse.quote(settings.AUDIO_GCS_BUCKET.strip(), safe=""), name=urllib.parse.quote(key, safe="")
    )
    try:
        resp = httpx.delete(url, headers={"Authorization": f"Bearer {_token()}"}, timeout=_TIMEOUT)
    except httpx.HTTPError as exc:
        raise StoreError(f"storage delete failed ({type(exc).__name__})") from exc
    if resp.status_code not in (200, 204, 404):
        raise StoreError(f"storage delete HTTP {resp.status_code} — {_message(resp)}")


# ---- recordings of a whole lesson (audio.lecture_audio): podcast and narration ---------------
# They are the big ones (a 35-minute podcast is ~40 MB in both formats) and filled the 500 MB
# Postgres volume, so they go to the bucket whenever AUDIO_STORAGE=gcs.


def file_away(prefix: str, cache_key: str, opus: bytes, aac: bytes) -> dict:
    """The column values for a new recording (storage, opus_key, aac_key, opus_data, aac_data):
    objects in the bucket when it is switched on; otherwise — or when an upload fails, so audio is
    never lost — the bytes in the row."""
    if backend() == "gcs":
        opus_key, aac_key = object_key(cache_key, "opus", prefix), object_key(cache_key, "aac", prefix)
        try:
            gcs_put(opus_key, opus, "audio/ogg")
            gcs_put(aac_key, aac, "audio/aac")
            return {"storage": "gcs", "opus_key": opus_key, "aac_key": aac_key, "opus_data": None, "aac_data": None}
        except StoreError as exc:
            log.warning("[audio_store] bucket write failed (%s); keeping %s in the database", exc, cache_key)
    return {"storage": "db", "opus_key": None, "aac_key": None, "opus_data": opus, "aac_data": aac}


# A player asks for the same file in several byte ranges (start, then each seek). Fetching the whole
# object from the bucket for every range would be slow, so the last few are kept in memory.
_CACHE_MAX_BYTES = 48 * 1024 * 1024
_CACHE_MAX_OBJECT = 24 * 1024 * 1024
_cache: OrderedDict[str, bytes] = OrderedDict()
_cache_size = 0
_cache_lock = threading.Lock()


def gcs_get_cached(key: str) -> bytes | None:
    global _cache_size
    with _cache_lock:
        hit = _cache.get(key)
        if hit is not None:
            _cache.move_to_end(key)
            return hit
    data = gcs_get(key)
    if data is None or len(data) > _CACHE_MAX_OBJECT:
        return data
    with _cache_lock:
        if key not in _cache:
            _cache[key] = data
            _cache_size += len(data)
            while _cache_size > _CACHE_MAX_BYTES and _cache:
                _, old = _cache.popitem(last=False)
                _cache_size -= len(old)
    return data


# ---- long recordings: hand the player a time-limited link to the bucket instead of the bytes -------
# A lecture is 10-25 MB. Read through this process it sits in RAM (and a cache miss fetches all of it
# again) and every byte leaves through the VM. A V4 signed link lets the player take the file, and ask
# for ranges, straight from the bucket. Signing is local (the service account's private key); the
# bucket stays private. The link is made for a half-hour-aligned moment, so everyone asking within
# the same half hour gets the same URL.
_SIGN_ALIGN_S = 30 * 60
_SIGN_TTL_S = 2 * 60 * 60
_CHECK_OK_FOR_S = 15 * 60
_CHECK_RETRY_S = 2 * 60
_sign_lock = threading.Lock()
_sign_credentials = None
_sign_credentials_raw = ""
_check_lock = threading.Lock()
_check = {"ok": False, "at": -1e9}


def _signing_credentials():
    """The service account, loaded without any network call, for signing only."""
    global _sign_credentials, _sign_credentials_raw
    try:
        from google.oauth2 import service_account
    except ImportError as exc:  # pragma: no cover - google-auth ships with google-genai
        raise StoreError("google-auth is not installed") from exc
    raw = settings.AUDIO_GCS_CREDENTIALS
    with _sign_lock:
        if _sign_credentials is None or raw != _sign_credentials_raw:
            try:
                _sign_credentials = service_account.Credentials.from_service_account_info(json.loads(raw))
            except Exception as exc:  # noqa: BLE001 - bad JSON, missing fields, unusable key
                raise StoreError("AUDIO_GCS_CREDENTIALS is not a valid service-account JSON") from exc
            _sign_credentials_raw = raw
        return _sign_credentials


def gcs_signed_url(key: str, *, now: datetime | None = None) -> str:
    """A V4 signed GET link to one object of the bucket (path style, so no bucket-name DNS rules)."""
    creds = _signing_credentials()
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    moment = datetime.fromtimestamp(int(moment.timestamp()) // _SIGN_ALIGN_S * _SIGN_ALIGN_S, timezone.utc)
    stamp = moment.strftime("%Y%m%dT%H%M%SZ")
    scope = f"{stamp[:8]}/auto/storage/goog4_request"
    host = "storage.googleapis.com"
    path = f"/{settings.AUDIO_GCS_BUCKET.strip()}/{urllib.parse.quote(key, safe='/~')}"
    params = {
        "X-Goog-Algorithm": "GOOG4-RSA-SHA256",
        "X-Goog-Credential": f"{creds.service_account_email}/{scope}",
        "X-Goog-Date": stamp,
        "X-Goog-Expires": str(_SIGN_TTL_S),
        "X-Goog-SignedHeaders": "host",
    }
    query = "&".join(f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}" for k, v in sorted(params.items()))
    canonical = f"GET\n{path}\n{query}\nhost:{host}\n\nhost\nUNSIGNED-PAYLOAD"
    to_sign = f"GOOG4-RSA-SHA256\n{stamp}\n{scope}\n{hashlib.sha256(canonical.encode()).hexdigest()}"
    try:
        signature = creds.signer.sign(to_sign.encode()).hex()
    except Exception as exc:  # noqa: BLE001 - google-auth's own error types
        raise StoreError("could not sign a storage link") from exc
    return f"https://{host}{path}?{query}&X-Goog-Signature={signature}"


def _signed_links_work(url: str) -> bool:
    """Asks the bucket for the first byte of `url`, at most once every 15 minutes (2 after a failure).
    200 / 206 (served) and 404 (signature accepted, that object is gone) prove the signing is right;
    anything else (403 SignatureDoesNotMatch, a refused key, a network error) means: keep serving the
    bytes through the API, as before. So a mistake in the signing, or a key that lost its access,
    costs RAM again but never a silent player."""
    with _check_lock:
        age = time.monotonic() - _check["at"]
        if age < (_CHECK_OK_FOR_S if _check["ok"] else _CHECK_RETRY_S):
            return bool(_check["ok"])
        try:
            resp = httpx.get(url, headers={"Range": "bytes=0-0"}, timeout=httpx.Timeout(6.0, connect=4.0))
            ok = resp.status_code in (200, 206, 404)
            if not ok:
                log.warning("[audio] signed bucket links are refused (HTTP %s): audio goes through the API", resp.status_code)
        except httpx.HTTPError as exc:
            ok = False
            log.warning("[audio] could not test a signed bucket link (%s): audio goes through the API", type(exc).__name__)
        _check.update(ok=ok, at=time.monotonic())
        return ok


def signed_redirect_url(row, ext: str) -> str | None:
    """Where to send the player for a recording kept in the bucket, or None to serve the bytes here
    (a recording still in its row, a bucket without a usable key, links switched off, or links that
    the bucket does not accept)."""
    if not settings.AUDIO_REDIRECT_TO_GCS or getattr(row, "storage", "db") != "gcs" or not gcs_configured():
        return None
    key = row.opus_key if ext == "opus" else row.aac_key
    if not key:
        return None
    try:
        url = gcs_signed_url(key)
    except StoreError:
        return None
    return url if _signed_links_work(url) else None


def read_row(row, ext: str) -> bytes | None:
    """The bytes of one container ("opus" | "aac") of a lecture recording, from wherever it is kept."""
    if getattr(row, "storage", "db") == "gcs":
        key = row.opus_key if ext == "opus" else row.aac_key
        return gcs_get_cached(key) if key else None
    return row.opus_data if ext == "opus" else row.aac_data


# ---- lesson pictures (content.scene_image): one small object each -------------------------------
# They were also bytea in the 500 MB volume. Unlike a recording, a picture can be DRAWN AGAIN under
# the same name (an editor's "vẽ lại"), so they are not kept in the memory cache: another process
# could still hold the old bytes.

_IMAGE_EXT = {"image/webp": "webp", "image/png": "png", "image/jpeg": "jpg", "image/gif": "gif"}


def image_object_key(cache_key: str, mime_type: str) -> str:
    return f"img/{cache_key}.{_IMAGE_EXT.get((mime_type or '').lower(), 'bin')}"


def file_image(cache_key: str, data: bytes, mime_type: str) -> dict:
    """The column values for a picture (storage, object_key, data): an object in the bucket when it
    is switched on; otherwise — or when the upload fails, so a drawing paid for is never lost — the
    bytes in the row."""
    if backend() == "gcs":
        key = image_object_key(cache_key, mime_type)
        try:
            gcs_put(key, data, mime_type or "application/octet-stream")
            return {"storage": "gcs", "object_key": key, "data": None}
        except StoreError as exc:
            log.warning("[audio_store] bucket write failed (%s); keeping picture %s in the database", exc, cache_key)
    return {"storage": "db", "object_key": None, "data": data}


def read_image(row) -> bytes | None:
    """The bytes of a picture, from wherever it is kept (None when there are none)."""
    if getattr(row, "storage", "db") == "gcs":
        return gcs_get(row.object_key) if row.object_key else None
    return row.data


def offload_image(row, prefix: str = "img") -> int:  # noqa: ARG001 - same call shape as offload_row
    """Move a picture that is still in its row to the bucket (upload first, then let go of the bytes).
    Returns the bytes moved; a StoreError leaves the row untouched."""
    if getattr(row, "storage", "db") == "gcs" or not row.data:
        return 0
    key = image_object_key(row.cache_key, row.mime_type)
    gcs_put(key, row.data, row.mime_type or "application/octet-stream")
    moved = len(row.data)
    row.storage, row.object_key, row.data = "gcs", key, None
    return moved


def offload_row(row, prefix: str) -> int:
    """Move a recording that is still in its row to the bucket: upload the bytes, then — only after
    both uploads succeeded — point the row at the objects and empty its data columns. Returns the
    bytes moved (0 when there was nothing to move). A StoreError leaves the row untouched."""
    if getattr(row, "storage", "db") == "gcs" or not (row.opus_data or row.aac_data):
        return 0
    opus_key = aac_key = None
    moved = 0
    if row.opus_data:
        opus_key = object_key(row.cache_key, "opus", prefix)
        gcs_put(opus_key, row.opus_data, "audio/ogg")
        moved += len(row.opus_data)
    if row.aac_data:
        aac_key = object_key(row.cache_key, "aac", prefix)
        gcs_put(aac_key, row.aac_data, "audio/aac")
        moved += len(row.aac_data)
    row.storage, row.opus_key, row.aac_key = "gcs", opus_key, aac_key
    row.opus_data = row.aac_data = None
    return moved
