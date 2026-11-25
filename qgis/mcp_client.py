"""QGIS MCP 插件的最小 socket 客户端（与插件 wire.py 一致）。

用法：
    python mcp_client.py <command> ['{"json":"params"}']
    python mcp_client.py --file payload.json      # {"type":..,"params":..}
    python mcp_client.py <command> @params.json

协议：4 字节大端 uint32 长度前缀 + UTF-8 JSON 请求；响应同帧长。
端口：默认 9877，可用环境变量 QGIS_MCP_PORT 覆盖（插件工具栏里也能改）。
常用命令：ping / get_project_info / get_layers / get_layer_features /
         get_unique_values / list_layouts / export_layout / execute_code
注意：参数名是 layer_id，不是 layer。
"""

from __future__ import annotations

import json
import os
import socket
import struct
import sys

HOST = os.environ.get("QGIS_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("QGIS_MCP_PORT", "9877"))
HEADER = struct.Struct(">I")
CHUNK = 65536


def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(min(CHUNK, n - len(buf)))
        if not chunk:
            raise ConnectionError("socket closed by QGIS before full frame arrived")
        buf.extend(chunk)
    return bytes(buf)


def call(command: str, params: dict | None = None, timeout: float = 180.0) -> dict:
    payload = json.dumps({"type": command, "params": params or {}}, ensure_ascii=False)
    data = payload.encode("utf-8")
    with socket.create_connection((HOST, PORT), timeout=10) as sock:
        sock.settimeout(timeout)
        sock.sendall(HEADER.pack(len(data)) + data)
        (length,) = HEADER.unpack(recv_exact(sock, HEADER.size))
        body = recv_exact(sock, length)
    return json.loads(body.decode("utf-8"))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    command = argv[1]
    params: dict = {}
    if len(argv) > 2:
        raw = argv[2]
        if raw.startswith("@"):
            with open(raw[1:], "r", encoding="utf-8") as fh:
                params = json.load(fh)
        else:
            params = json.loads(raw)
    result = call(command, params)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception as exc:  # noqa: BLE001 - CLI
        print(f"CLIENT ERROR: {exc!r}", file=sys.stderr)
        sys.exit(1)