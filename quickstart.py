# -*- coding: utf-8 -*-
"""体检：一条命令看清「缺什么、下一步点哪里」。

    python quickstart.py

它不画图，只回答四件事：
    1. Python / Pillow / 字体 是否就位
    2. QGIS 的 MCP 插件端口通不通（不通 = 后面全废）
    3. QGIS 里当前打开的是哪个工程、有多少图层
    4. 画布与换算（4960×3507 = A3 300dpi；1 mm = 11.81 px）
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'qgis'))
sys.path.insert(0, os.path.join(HERE, 'board'))

OK, BAD, WARN = '  [OK] ', '  [X]  ', '  [!]  '
fails = []


def line(mark, msg, hint=''):
    print(mark + msg + (('\n         → ' + hint) if hint else ''))


print('\n=== 1. 本机环境 ===')
line(OK, 'Python %s' % sys.version.split()[0])

try:
    import PIL
    from PIL import ImageFont
    line(OK, 'Pillow %s' % PIL.__version__)
except Exception as exc:                                   # noqa: BLE001
    line(BAD, 'Pillow 没装：%r' % (exc,), 'pip install -r requirements.txt')
    fails.append('pillow')

import board_lib as bl                                     # noqa: E402

for tag, path in (('标题字体（得意黑）', bl.DEYI), ('正文字体', bl.YH), ('粗体', bl.YHB)):
    if os.path.exists(path):
        line(OK, '%s：%s' % (tag, path))
    else:
        line(WARN, '%s 找不到：%s' % (tag, path), '把 SmileySans-Oblique.ttf 放进 fonts/，或用 BOARD_FONT_DEYI 指定')
line(OK, '画布 %d×%d（A3 横版 300dpi），1 mm = %.2f px' % (bl.W, bl.H, bl.W / 420.0))
print('  输出目录：%s' % bl.OUT_DIR)

print('\n=== 2. QGIS 插件端口 ===')
try:
    from mcp_client import call, PORT
    pong = call('ping', {}, timeout=5)
    line(OK, '127.0.0.1:%d 有响应：%s' % (PORT, json.dumps(pong, ensure_ascii=False)[:120]))
except Exception as exc:                                   # noqa: BLE001
    line(BAD, '连不上 QGIS：%r' % (exc,),
         'QGIS 菜单 插件 → 管理并安装插件 → 搜 "QGIS MCP" → 装完在工具栏点开，'
         '端口选 9877（被占用时插件会提示换端口，这里用 QGIS_MCP_PORT 环境变量对齐）')
    fails.append('mcp')
    print('\n=== 3. 工程 ===   (跳过：端口没通)')
    print('\n结果：还有 %d 项要修。' % len(fails))
    sys.exit(1)

print('\n=== 3. 当前工程 ===')
try:
    info = call('get_project_info', {})
    prj = info.get('result') or info
    name = prj.get('project_name') or prj.get('title') or prj.get('file') or '(未命名)'
    line(OK, '工程：%s' % name)
    crs = prj.get('crs') or prj.get('authid') or ''
    if crs:
        line(OK, 'CRS：%s' % crs)
    layers = call('get_layers', {}).get('result') or []
    if isinstance(layers, dict):
        layers = layers.get('layers') or []
    line(OK, '图层 %d 个' % len(layers))
    if layers:
        names = [l.get('name') for l in layers if isinstance(l, dict)][:12]
        print('        前 12 个：' + '、'.join(n for n in names if n))
except Exception as exc:                                   # noqa: BLE001
    line(WARN, '读工程信息失败：%r' % (exc,), '先在 QGIS 里打开你的 .qgz 再跑')

print('\n=== 4. 下一步 ===')
print('  出素图：python qgis/run_qgis.py qgis/render_map.py --spec examples/spec_example.json')
print('  排展板：python examples/compose_example.py')
print('\n结果：环境就绪。' if not fails else '\n结果：还有 %d 项要修。' % len(fails))
sys.exit(1 if fails else 0)