# -*- coding: utf-8 -*-
"""在 QGIS 进程内跑：按 JSON spec 渲染一张「素图」（不带标题/图例，只画图层）。

由 qgis/run_qgis.py 调用：
    python qgis/run_qgis.py qgis/render_map.py --spec examples/spec_example.json

spec 字段（只有 out 必填，其余可省）：
{
  "project":  "D:/work/工程.qgz",          # 给了就 iface.addProject 切过去
  "out":      "D:/work/map_out.png",       # 必填；同时写同名 .json 元数据
  "width":    2900,                        # 像素；与 height 决定纵横比
  "height":   2300,
  "dpi":      300,                         # 决定 mm→px，线宽/字号都是按 dpi 算的
  "crs":      "EPSG:4547",                 # 缺省用工程 CRS；extent 也按这个 CRS 解释
  "extent":   [xmin, ymin, xmax, ymax],    # 缺省按 fit 自动算
  "fit":      {"layers": ["镇界"], "pad": 0.06},   # 自动范围 + 边距（0.06=6%）
  "layers":   ["节点", "廊道", "底图"],      # 上→下顺序（第一个画在最上面）；缺省=图层树可见层
  "background": "#FFFFFF",
  "scale":    {"k": 2.6, "layers": ["廊道"]}  # 出图前把线宽/符号/字号整体放大 k 倍（可选）
}

产出：out 指定的 PNG + 同名 .json（extent / mpp / 像素尺寸），排版打比例尺时要用 mpp。

注意：本脚本是被 run_qgis.py 拼进 `execute_code` 里跑的，前面会被塞进两行 import/sys.path，
所以这里**不能**写 `from __future__ import ...`（会触发「must occur at the beginning」SyntaxError）。
"""
import json
import os
import sys

from qgis.core import (
    QgsProject, QgsMapSettings, QgsMapRendererParallelJob, QgsRectangle,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsWkbTypes,
)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor

# ---------------------------------------------------------------- spec 读取
SPEC_PATH = globals().get('SPEC_PATH') or ''
if not SPEC_PATH:
    SPEC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'examples', 'spec_example.json')
with open(SPEC_PATH, 'r', encoding='utf-8') as fh:
    SPEC = json.load(fh)

BASE = os.path.dirname(os.path.abspath(SPEC_PATH))       # spec 里的相对路径都相对 spec 所在的目录


def _abs(p):
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(BASE, p))


OUT = _abs(SPEC['out'])
WIDTH = int(SPEC.get('width', 2900))
HEIGHT = int(SPEC.get('height', 2300))
DPI = int(SPEC.get('dpi', 300))
BG = SPEC.get('background', '#FFFFFF')

prj = QgsProject.instance()

# ---------------------------------------------------------------- 工程
if SPEC.get('project'):
    opened = iface.addProject(_abs(SPEC['project']))   # noqa: F821 (QGIS 注入)
    print('project opened:', opened)

# ---------------------------------------------------------------- 图层
all_layers = {l.name(): l for l in prj.mapLayers().values()}
names = SPEC.get('layers')
if not names:
    order = prj.layerTreeRoot().layerOrder()          # 上→下
    names = [l.name() for l in order if l and prj.layerTreeRoot().findLayer(l.id()).isVisible()]
missing = [n for n in names if n not in all_layers]
if missing:
    raise KeyError('找不到图层 %s；工程里有：%s' % (missing, sorted(all_layers)))
layers = [all_layers[n] for n in names]

# ---------------------------------------------------------------- 出图前放大样式（可选）
if SPEC.get('scale'):
    import scale_styles                                  # 同目录库，run_qgis 已把它加进 sys.path
    k = float(SPEC['scale'].get('k', 1.0))
    scale_styles.scale_layers(k, SPEC['scale'].get('layers') or names)
    print('styles scaled by', k)

# ---------------------------------------------------------------- 坐标与范围
crs = QgsCoordinateReferenceSystem(SPEC.get('crs') or prj.crs().authid())
if not crs.isValid():
    raise ValueError('CRS 无效：%s' % SPEC.get('crs'))

if SPEC.get('extent'):
    ext = QgsRectangle(*[float(v) for v in SPEC['extent']])
else:
    fit = SPEC.get('fit') or {}
    fit_names = fit.get('layers') or names
    box = QgsRectangle()
    box.setNull()
    for n in fit_names:
        lay = all_layers[n]
        b = lay.extent()
        if lay.crs() != crs:                              # 不同 CRS 必须转换后再并
            b = QgsCoordinateTransform(lay.crs(), crs, prj).transformBoundingBox(b)
        box.combineExtentWith(b)
    if box.isNull() or box.isEmpty():
        raise ValueError('所有图层范围为空，无法自动取景；请在 spec 里显式给 extent')
    pad = float(fit.get('pad', 0.05))
    box = QgsRectangle(box.xMinimum() - box.width() * pad, box.yMinimum() - box.height() * pad,
                       box.xMaximum() + box.width() * pad, box.yMaximum() + box.height() * pad)
    # 按画布纵横比裁齐，避免出图被拉伸
    target = WIDTH / HEIGHT
    cur = box.width() / box.height()
    if cur < target:
        need = box.height() * target
        c = box.center().x()
        box = QgsRectangle(c - need / 2, box.yMinimum(), c + need / 2, box.yMaximum())
    elif cur > target:
        need = box.width() / target
        c = box.center().y()
        box = QgsRectangle(box.xMinimum(), c - need / 2, box.xMaximum(), c + need / 2)

ext = box if not SPEC.get('extent') else QgsRectangle(*[float(v) for v in SPEC['extent']])

# ---------------------------------------------------------------- 渲染
ms = QgsMapSettings()
ms.setLayers(layers)                   # 列表即上→下顺序
ms.setDestinationCrs(crs)
ms.setExtent(ext)
ms.setOutputSize(QSize(WIDTH, HEIGHT))
ms.setOutputDpi(DPI)
ms.setBackgroundColor(QColor(BG))

job = QgsMapRendererParallelJob(ms)
job.start()
job.waitForFinished()
img = job.renderedImage()

os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
ok = img.save(OUT)                     # 空目录会让 save 静默失败，先 makedirs
print('render', OUT, ok)

meta = {
    'out': OUT,
    'extent': [ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum()],
    'mpp': ext.width() / WIDTH,        # 每像素米数，排版算比例尺用
    'width': WIDTH, 'height': HEIGHT, 'dpi': DPI,
    'crs': crs.authid(),
    'layers': names,
}
with open(os.path.splitext(OUT)[0] + '.json', 'w', encoding='utf-8') as fh:
    json.dump(meta, fh, ensure_ascii=False, indent=1)
print('META', meta['mpp'], meta['crs'])