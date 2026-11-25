# -*- coding: utf-8 -*-
"""排一张 A3 展板：贴素图 + 标题 + 右栏文字 + KPI + 底部图例。

    python examples/compose_example.py

先跑 qgis/render_map.py 出素图（out/map_example.png + .json），这张板才有料可贴；
没跑过也能排，只是中间留白。要改的全部集中在下面的 CONFIG / 正文里。
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'board'))

from board_lib import *            # noqa: F401,F403  new_board / paste_fit / section / para / kpi ...

# ================================================================ CONFIG 改这里
MAP_PNG = os.path.join(ROOT, 'out', 'map_example.png')
TAG, TITLE, HL = '规划分析', '某某镇绿地系统规划图', (5, 8)    # HL = 标题里高亮的起止字（1 起）
MAPBOX = (160, 600, 3060, 2900)                                # 地图贴图区（A3 300dpi 像素）
RXV, RXW = 3200, 1520                                          # 右栏左边界 / 文字宽

SECTIONS = [
    ('现状判断', [
        '① 绿地总量 ……（写结论，写数字，不写形容词）',
        '② 分布问题 ……',
        '③ 机会与约束 ……',
    ]),
    ('规划策略', [
        '一轴：……',
        '两带：……',
    ]),
]
KPIS = [('21.0', '公里 · 主廊长度'), ('96.2%', '居住用地 500 m 覆盖')]
LEGEND = [
    ('box', '公园绿地', '#C9E4C5'), ('box', '水域', '#BFD8E5'),
    ('line', '规划廊道', '#0B5E45'), ('dot', '主要节点', '#E4724A'),
]
NOTE = '数据来源：镇域用地分类调查、路网与公园点位；坐标为 CGCS2000。'


# ================================================================ 排
def panel_ns(board, d, img_path, box, meta):
    """贴图 + 指北针 + 比例尺（比例尺用素图元数据里的 mpp，别硬编码）。"""
    if not os.path.exists(img_path):
        d.rectangle(box, outline=(200, 200, 200), width=4)
        d.text((box[0] + 40, box[1] + 40), 'Run qgis/render_map.py first → %s' % img_path,
               font=f(YH, 44), fill=GRAY)
        return None
    placed = paste_fit(board, img_path, box)
    mx, my, dw, dh = placed
    mpp = meta.get('mpp') or 3.0
    north(board, mx + dw - 210, my + 26, 0.62)
    scalebar(d, mpp, mx + 260, my + dh - 96, fs=36)   # bar_m 不传，按 mpp 自动选档
    return placed


def main():
    meta = {}
    meta_path = os.path.splitext(MAP_PNG)[0] + '.json'
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding='utf-8'))

    board, d = new_board(TAG, TITLE, hl=HL)
    panel_ns(board, d, MAP_PNG, MAPBOX, meta)

    y = 600
    for head, lines in SECTIONS:
        y = section(d, RXV, y, head, fs=72)
        for ln in lines:
            y = para(d, RXV, y + 12, ln, fs=42, maxw=RXW, lh=62)
        y += 40

    for i, (num, cap) in enumerate(KPIS):
        x = RXV + i * 560
        d.text((x, 2520), num, font=f(DEYI, 104), fill=RED)
        d.text((x, 2520 + 122), cap, font=f(YH, 40), fill=GRAY)

    foot(board, d, NOTE, LEGEND, rows=1)
    save(board, '001_示例展板.png')


if __name__ == '__main__':
    main()