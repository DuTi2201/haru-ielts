import json
import os
import socket
import tempfile
import threading
import time

from deploy import haru_vm_mcp


def _unix_http_request(sock_path: str, method: str, path: str, body: dict | list | None = None, headers: dict | None = None) -> tuple[int, dict[str, str], bytes]:
    raw_body = json.dumps(body).encode("utf-8") if body is not None else b""
    req_headers = {
        "Host": "localhost",
        "Connection": "close",
    }
    if body is not None:
        req_headers["Content-Type"] = "application/json"
        req_headers["Content-Length"] = str(len(raw_body))
    if headers:
        req_headers.update(headers)

    head = f"{method} {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in req_headers.items()) + "\r\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect(sock_path)
        s.sendall(head.encode("utf-8") + raw_body)
        chunks = []
        while True:
            data = s.recv(4096)
            if not data:
                break
            chunks.append(data)
    raw_resp = b"".join(chunks)
    header_part, _, resp_body = raw_resp.partition(b"\r\n\r\n")
    lines = header_part.decode("utf-8").split("\r\n")
    status_code = int(lines[0].split(" ")[1])
    resp_headers = {}
    for ln in lines[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            resp_headers[k.strip().lower()] = v.strip()
    return status_code, resp_headers, resp_body


def test_mcp_unix_socket_end_to_end(monkeypatch):
    secret = "test_secret_token_123456"
    monkeypatch.setattr(haru_vm_mcp, "MCP_SECRET", secret)

    # Use /tmp directly because macOS AF_UNIX path limit is 104 bytes
    sock_path = f"/tmp/haru_mcp_test_{os.getpid()}.sock"
    if os.path.exists(sock_path):
        os.unlink(sock_path)

    server = haru_vm_mcp.ThreadingUnixHTTPServer(sock_path, haru_vm_mcp.MCPRequestHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        # 1. Wrong secret -> 404
        code, _, _ = _unix_http_request(sock_path, "POST", "/mcp/wrong_token", {"jsonrpc": "2.0", "id": 1, "method": "ping"})
        assert code == 404

        # 2. Initialize -> 200 + Mcp-Session-Id
        code, hdrs, body = _unix_http_request(
            sock_path,
            "POST",
            f"/mcp/{secret}",
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
        )
        assert code == 200
        assert "mcp-session-id" in hdrs
        data = json.loads(body)
        assert data["result"]["protocolVersion"] == "2025-03-26"
        assert data["result"]["serverInfo"]["name"] == "haru-vm-mcp"

        # 3. Initialized notification -> 202 empty body
        code, _, body = _unix_http_request(
            sock_path,
            "POST",
            f"/mcp/{secret}",
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        assert code == 202
        assert body == b""

        # 4. tools/list -> 6 tools
        code, _, body = _unix_http_request(
            sock_path,
            "POST",
            f"/mcp/{secret}",
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        )
        assert code == 200
        tools = json.loads(body)["result"]["tools"]
        names = {tool["name"] for tool in tools}
        assert names == {"vm_status", "haru_logs", "haru_service_action", "db_query", "haru_exec_python", "vm_shell"}

        # 5. tools/call vm_shell -> runs command
        code, _, body = _unix_http_request(
            sock_path,
            "POST",
            f"/mcp/{secret}",
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "vm_shell", "arguments": {"command": "echo hello_haru_mcp"}},
            },
        )
        assert code == 200
        res = json.loads(body)["result"]
        assert res["isError"] is False
        assert "hello_haru_mcp" in res["content"][0]["text"]
    finally:
        server.shutdown()
        server.server_close()
        if os.path.exists(sock_path):
            os.unlink(sock_path)
