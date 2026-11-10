#!/usr/bin/env python3
"""Remote MCP server for haru-vm (Streamable HTTP + SSE over Caddy HTTPS).

Runs as a lightweight host systemd service on the VM, listening on a Unix
domain socket (/opt/haru/mcp/mcp.sock) mounted into the Caddy container.
Authenticated via a 256-bit secret path segment:
    https://<HARU_DOMAIN>/mcp/<MCP_SECRET>
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import queue
import socketserver
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="[haru-mcp] %(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("haru.mcp")

HARU_BASE = os.environ.get("HARU_BASE", "/opt/haru")
HARU_SRC = os.path.join(HARU_BASE, "src")
SOCK_PATH = os.environ.get("MCP_SOCK_PATH", os.path.join(HARU_BASE, "mcp", "mcp.sock"))
MCP_SECRET = os.environ.get("MCP_SECRET", "").strip()
HARU_BIN = os.environ.get("HARU_BIN", "/usr/local/bin/haru")

SUPPORTED_PROTOCOL_VERSIONS = {"2024-11-05", "2025-03-26", "2025-06-18"}
DEFAULT_PROTOCOL_VERSION = "2025-03-26"
MAX_OUTPUT_CHARS = 48_000

_SSE_SESSIONS: dict[str, queue.Queue[str | None]] = {}
_SSE_LOCK = threading.Lock()


TOOLS: list[dict[str, Any]] = [
    {
        "name": "vm_status",
        "description": (
            "Get overall health of haru-vm: Docker containers (haru ps -a), "
            "disk space (df -h), memory/swap (free -m), current git commit in /opt/haru/src, "
            "and API /healthz check."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "haru_logs",
        "description": (
            "Read container logs from the Haru Docker stack on haru-vm "
            "(api, worker, caddy, db, or redis). Filters out noisy /healthz lines by default."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "enum": ["api", "worker", "caddy", "db", "redis"],
                    "default": "api",
                    "description": "Container service name.",
                },
                "tail": {
                    "type": "integer",
                    "default": 150,
                    "description": "Number of recent log lines to fetch (10-1000).",
                },
                "grep": {
                    "type": "string",
                    "description": "Optional case-insensitive regex pattern to filter log lines (e.g. 'podcast|ERROR|Traceback').",
                },
                "exclude_healthz": {
                    "type": "boolean",
                    "default": True,
                    "description": "Exclude 'GET /healthz' lines from api logs.",
                },
            },
        },
    },
    {
        "name": "haru_service_action",
        "description": (
            "Control Haru Docker Compose services on haru-vm: restart, up, stop, build, or ps."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["restart", "up", "stop", "build", "ps"],
                    "description": "Docker Compose action to run.",
                },
                "service": {
                    "type": "string",
                    "enum": ["", "api", "worker", "caddy", "db", "redis"],
                    "default": "",
                    "description": "Target service (leave empty for all services).",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "db_query",
        "description": (
            "Execute a SQL query against the production 'haru' PostgreSQL database. "
            "Runs inside a READ ONLY transaction by default unless read_only=false is explicitly set."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SQL query to execute.",
                },
                "read_only": {
                    "type": "boolean",
                    "default": True,
                    "description": "When true, wraps the query in BEGIN READ ONLY ... ROLLBACK.",
                },
            },
            "required": ["sql"],
        },
    },
    {
        "name": "haru_exec_python",
        "description": (
            "Run a Python snippet inside the running 'api' container on haru-vm "
            "(with full access to app.*, SQLAlchemy models, Celery tasks, and settings)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code passed to `python -c` inside the api container.",
                },
                "timeout_sec": {
                    "type": "integer",
                    "default": 120,
                    "description": "Timeout in seconds (max 600).",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "vm_shell",
        "description": (
            "Execute a bash command directly on the haru-vm host as root "
            "(working directory /opt/haru/src)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute.",
                },
                "timeout_sec": {
                    "type": "integer",
                    "default": 120,
                    "description": "Timeout in seconds (max 600).",
                },
            },
            "required": ["command"],
        },
    },
]


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    half = MAX_OUTPUT_CHARS // 2
    return (
        text[:half]
        + f"\n\n... [truncated {len(text) - MAX_OUTPUT_CHARS} chars] ...\n\n"
        + text[-half:]
    )


def _run_cmd(
    argv: list[str] | str,
    *,
    shell: bool = False,
    timeout: int = 120,
    cwd: str | None = None,
    input_text: str | None = None,
) -> tuple[int, str]:
    timeout = max(5, min(int(timeout), 600))
    work_dir = cwd if (cwd and os.path.isdir(cwd)) else (HARU_SRC if os.path.isdir(HARU_SRC) else "/")
    try:
        proc = subprocess.run(
            argv,
            shell=shell,
            cwd=work_dir,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        combined = ""
        if proc.stdout:
            combined += proc.stdout
        if proc.stderr:
            if combined and not combined.endswith("\n"):
                combined += "\n"
            combined += proc.stderr
        return proc.returncode, _truncate(combined.strip() or "(no output)")
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") + "\n" + (exc.stderr or "")
        return 124, _truncate(f"Command timed out after {timeout}s.\n{out}".strip())
    except Exception as exc:  # noqa: BLE001
        return 1, f"Failed to execute command: {exc}"


def _exec_tool(name: str, args: dict[str, Any]) -> tuple[bool, str]:
    if name == "vm_status":
        script = (
            f"{HARU_BIN} ps -a && echo '\\n=== DISK ===' && df -h / "
            "&& echo '\\n=== MEMORY ===' && free -m "
            "&& echo '\\n=== API HEALTH ===' && "
            f"{HARU_BIN} exec -T api python -c "
            "\"import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5).read().decode())\""
        )
        code, out = _run_cmd(["/bin/bash", "-lc", script], timeout=30)
        return code != 0, out

    if name == "haru_logs":
        service = str(args.get("service") or "api")
        if service not in {"api", "worker", "caddy", "db", "redis"}:
            return True, f"Invalid service: {service}"
        tail = max(10, min(int(args.get("tail") or 150), 1000))
        grep_pat = str(args.get("grep") or "").strip()
        exclude_healthz = bool(args.get("exclude_healthz", True))

        fetch_tail = min(tail * 4, 2500) if (exclude_healthz or grep_pat) else tail
        rc, raw = _run_cmd([HARU_BIN, "logs", "--tail", str(fetch_tail), service], timeout=30)
        lines = raw.splitlines()
        if exclude_healthz:
            lines = [ln for ln in lines if "GET /healthz" not in ln]
        if grep_pat:
            import re

            try:
                rx = re.compile(grep_pat, re.IGNORECASE)
                lines = [ln for ln in lines if rx.search(ln)]
            except re.error as exc:
                return True, f"Invalid regex '{grep_pat}': {exc}"
        lines = lines[-tail:]
        return rc != 0, _truncate("\n".join(lines) or "(no matching log lines)")

    if name == "haru_service_action":
        action = str(args.get("action") or "").strip()
        service = str(args.get("service") or "").strip()
        if action not in {"restart", "up", "stop", "build", "ps"}:
            return True, f"Unsupported action: {action}"
        if service and service not in {"api", "worker", "caddy", "db", "redis"}:
            return True, f"Invalid service: {service}"
        cmd = [HARU_BIN, action]
        if action == "up":
            cmd.append("-d")
        if service:
            cmd.append(service)
        rc, out = _run_cmd(cmd, timeout=300)
        return rc != 0, out

    if name == "db_query":
        sql = str(args.get("sql") or "").strip()
        if not sql:
            return True, "sql is required"
        read_only = bool(args.get("read_only", True))
        if read_only:
            wrapped_sql = f"BEGIN READ ONLY;\n{sql}\n;\nROLLBACK;\n"
        else:
            wrapped_sql = sql
        rc, out = _run_cmd(
            [HARU_BIN, "exec", "-T", "db", "psql", "-U", "haru", "-d", "haru"],
            input_text=wrapped_sql,
            timeout=60,
        )
        return rc != 0, out

    if name == "haru_exec_python":
        py_code = str(args.get("code") or "")
        if not py_code.strip():
            return True, "code is required"
        timeout = int(args.get("timeout_sec") or 120)
        rc, out = _run_cmd(
            [HARU_BIN, "exec", "-T", "api", "python", "-c", py_code],
            timeout=timeout,
        )
        return rc != 0, out

    if name == "vm_shell":
        command = str(args.get("command") or "")
        if not command.strip():
            return True, "command is required"
        timeout = int(args.get("timeout_sec") or 120)
        rc, out = _run_cmd(["/bin/bash", "-lc", command], timeout=timeout)
        return rc != 0, f"[exit_code={rc}]\n{out}"

    return True, f"Unknown tool: {name}"


def handle_jsonrpc_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Process a single JSON-RPC 2.0 message. Returns None for notifications."""
    method = msg.get("method", "")
    req_id = msg.get("id")
    params = msg.get("params") or {}

    # Notifications have no "id"
    if req_id is None:
        return None

    if method == "initialize":
        client_ver = str(params.get("protocolVersion") or "")
        proto_ver = client_ver if client_ver in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": proto_ver,
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "haru-vm-mcp",
                    "version": "1.0.0",
                },
                "instructions": (
                    "Remote MCP controller for haru-vm (Google Cloud VM running Haru Korean "
                    "backend: FastAPI api, Celery worker, PostgreSQL/pgvector db, Redis, Caddy)."
                ),
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        tool_name = str(params.get("name") or "")
        tool_args = params.get("arguments") or {}
        if not isinstance(tool_args, dict):
            tool_args = {}
        log.info("tools/call name=%s args=%s", tool_name, json.dumps(tool_args, ensure_ascii=False)[:300])
        is_error, text_out = _exec_tool(tool_name, tool_args)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": text_out}],
                "isError": is_error,
            },
        }

    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}}

    if method == "resources/templates/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resourceTemplates": []}}

    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": []}}

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}",
        },
    }


def _parse_route(raw_path: str) -> tuple[bool, str]:
    """Verify `/mcp/<secret>[/<subpath>]` and return (authorized, subpath)."""
    if not MCP_SECRET:
        return False, ""
    parsed = urlparse(raw_path)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2 or parts[0] != "mcp":
        return False, ""
    token = parts[1]
    if not hmac.compare_digest(token, MCP_SECRET):
        return False, ""
    subpath = "/" + "/".join(parts[2:]) if len(parts) > 2 else "/"
    return True, subpath


class MCPRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def address_string(self) -> str:
        return self.headers.get("X-Forwarded-For", "unix-socket")

    def log_message(self, fmt: str, *args: Any) -> None:
        # Redact the secret token from logged request lines
        msg = fmt % args
        if MCP_SECRET and MCP_SECRET in msg:
            msg = msg.replace(MCP_SECRET, "***")
        log.info("%s - %s", self.address_string(), msg)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Accept, Authorization, Mcp-Session-Id, MCP-Protocol-Version, Last-Event-ID",
        )
        self.send_header("Access-Control-Expose-Headers", "Mcp-Session-Id")

    def _send_json(self, status_code: int, payload: Any, extra_headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self._send_cors_headers()
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self, status_code: int, extra_headers: dict[str, str] | None = None) -> None:
        self.send_response(status_code)
        self._send_cors_headers()
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        ok, _ = _parse_route(self.path)
        if not ok:
            self._send_empty(404)
            return
        self._send_empty(204)

    def do_DELETE(self) -> None:  # noqa: N802
        ok, _ = _parse_route(self.path)
        if not ok:
            self._send_empty(404)
            return
        self._send_empty(200)

    def do_GET(self) -> None:  # noqa: N802
        ok, subpath = _parse_route(self.path)
        if not ok:
            self._send_json(404, {"detail": "Not Found"})
            return

        accept = (self.headers.get("Accept") or "").lower()

        # Legacy 2024-11-05 HTTP+SSE transport support on /mcp/<secret>/sse
        if subpath == "/sse":
            session_id = uuid.uuid4().hex
            q: queue.Queue[str | None] = queue.Queue()
            with _SSE_LOCK:
                _SSE_SESSIONS[session_id] = q
            try:
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()

                endpoint_url = f"/mcp/{MCP_SECRET}/messages?session_id={session_id}"
                init_event = f"event: endpoint\ndata: {endpoint_url}\n\n".encode("utf-8")
                self.wfile.write(init_event)
                self.wfile.flush()

                while True:
                    try:
                        item = q.get(timeout=15)
                        if item is None:
                            break
                        self.wfile.write(f"event: message\ndata: {item}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with _SSE_LOCK:
                    _SSE_SESSIONS.pop(session_id, None)
            return

        # Streamable HTTP (2025-03-26+): if client probes GET with Accept: text/event-stream ONLY,
        # return 405 Method Not Allowed per spec so client uses inline POST responses.
        if "text/event-stream" in accept and "application/json" not in accept and "text/html" not in accept:
            self._send_empty(405, {"Allow": "POST, DELETE, OPTIONS"})
            return

        self._send_json(
            200,
            {
                "status": "ok",
                "service": "haru-vm-mcp",
                "transport": "streamable-http",
                "tools": [t["name"] for t in TOOLS],
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        ok, subpath = _parse_route(self.path)
        if not ok:
            self._send_json(404, {"detail": "Not Found"})
            return

        content_len = int(self.headers.get("Content-Length") or 0)
        raw_body = self.rfile.read(content_len) if content_len > 0 else b""
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:  # noqa: BLE001
            self._send_json(
                400,
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
            )
            return

        session_id = self.headers.get("Mcp-Session-Id") or uuid.uuid4().hex
        extra_headers = {"Mcp-Session-Id": session_id}

        # Legacy SSE message posting support (/mcp/<secret>/messages?session_id=...)
        if subpath == "/messages":
            parsed = urlparse(self.path)
            sse_sid = ""
            for kv in parsed.query.split("&"):
                if kv.startswith("session_id="):
                    sse_sid = kv.split("=", 1)[1]
            resp = handle_jsonrpc_message(payload) if isinstance(payload, dict) else None
            if sse_sid:
                with _SSE_LOCK:
                    q = _SSE_SESSIONS.get(sse_sid)
                if q is not None and resp is not None:
                    q.put(json.dumps(resp, ensure_ascii=False))
                    self._send_empty(202)
                    return
            if resp is None:
                self._send_empty(202)
            else:
                self._send_json(200, resp, extra_headers)
            return

        # Standard Streamable HTTP (single message or batch)
        if isinstance(payload, list):
            responses = []
            for item in payload:
                if isinstance(item, dict):
                    r = handle_jsonrpc_message(item)
                    if r is not None:
                        responses.append(r)
            if not responses:
                self._send_empty(202, extra_headers)
            else:
                self._send_json(200, responses, extra_headers)
            return

        if isinstance(payload, dict):
            resp = handle_jsonrpc_message(payload)
            if resp is None:
                self._send_empty(202, extra_headers)
            else:
                self._send_json(200, resp, extra_headers)
            return

        self._send_json(
            400,
            {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}},
        )


class ThreadingUnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def serve_forever(sock_path: str = SOCK_PATH) -> None:
    if not MCP_SECRET:
        log.error("MCP_SECRET is not set; refusing to start.")
        sys.exit(1)
    sock_dir = os.path.dirname(sock_path)
    os.makedirs(sock_dir, mode=0o755, exist_ok=True)
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    server = ThreadingUnixHTTPServer(sock_path, MCPRequestHandler)
    os.chmod(sock_path, 0o666)  # Allow Caddy container to connect to the Unix socket
    log.info("Listening on unix socket %s", sock_path)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if os.path.exists(sock_path):
            os.unlink(sock_path)


if __name__ == "__main__":
    serve_forever()
