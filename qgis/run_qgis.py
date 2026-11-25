# -*- coding: utf-8 -*-
"""把一段 PyQGIS 代码送进「正在运行的 QGIS」里执行（经 QGIS MCP 插件的 socket）。

用法：
    python qgis/run_qgis.py qgis/render_map.py --spec examples/spec_example.json
    python qgis/run_qgis.py my_script.py          # 随便一段 PyQGIS，print 能回传

--spec 会把路径以 `SPEC_PATH = r"..."` 注入脚本开头，脚本里用 globals() 取。
脚本里可以 `import render_map / scale_styles` 之类同目录模块（这里已把 qgis/ 加进 sys.path）。

退出码：0 = 执行成功；1 = QGIS 侧报错或连不上。
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from mcp_client import call  # noqa: E402


def run(code: str, timeout: float = 240.0) -> dict:
    return call("execute_code", {"code": code, "timeout": timeout}, timeout=timeout + 30)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = argv[1]
    spec = None
    if '--spec' in argv:
        spec = os.path.abspath(argv[argv.index('--spec') + 1])
    with open(path, 'r', encoding='utf-8-sig') as fh:     # utf-8-sig：容忍 BOM
        body = fh.read()

    prelude = "import sys\nsys.path.insert(0, %r)\n" % HERE
    if spec:
        prelude += "SPEC_PATH = %r\n" % spec
    res = run(prelude + body)

    payload = res.get('result') or {}
    if payload.get('stdout'):
        print(payload['stdout'].rstrip())
    if payload.get('stderr'):
        print('--- QGIS stderr ---\n' + payload['stderr'].rstrip(), file=sys.stderr)
    if res.get('status') != 'success' or not payload.get('executed', True):
        print(json.dumps(res, ensure_ascii=False, indent=1)[:4000], file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except Exception as exc:                              # noqa: BLE001 - CLI
        print('RUN ERROR: %r' % (exc,), file=sys.stderr)
        print('端口通不通？先在 QGIS 里把 MCP 插件打开（默认 9877）。', file=sys.stderr)
        sys.exit(1)