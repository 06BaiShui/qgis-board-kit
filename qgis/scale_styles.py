# -*- coding: utf-8 -*-
"""把图层样式（线宽 / 符号大小 / 字号 / 描边 / 白晕）整体乘一个系数 k。

为什么需要：屏幕上 1 mm 的线看着刚好，出 300dpi 素图再缩到 A3 版心就细成发丝。
反过来，先按「出图尺度」把线宽字号放大，再整幅缩小，视觉粗细才稳定。
经验值：素图宽 2900 px 缩到版心 2900 px（1:1）时 k = 2.4–3.0。

用法（在 QGIS 里）：
    import scale_styles
    scale_styles.scale_layers(2.6)                    # 全部图层
    scale_styles.scale_layers(2.6, ['廊道', '节点'])   # 指定图层

注意：只改内存里的渲染对象，不写回数据源；想保留就 layer.saveStyleToDatabase / 另存 qml。
被 run_qgis.py 注入执行时不能有 `from __future__` 开头（见 render_map.py 注释）。
"""
from qgis.core import (
    QgsProject, QgsSymbolLayer, QgsLineSymbolLayer, QgsMarkerSymbolLayer, QgsFillSymbolLayer,
    QgsTextFormat,
)


def _scale_symbol(sym, k):
    if sym is None:
        return
    for i in range(sym.symbolLayerCount()):
        sl = sym.symbolLayer(i)
        if isinstance(sl, QgsLineSymbolLayer):
            sl.setWidth(sl.width() * k)
        if isinstance(sl, QgsMarkerSymbolLayer):
            sl.setSize(sl.size() * k)
            if hasattr(sl, 'setStrokeWidth') and sl.strokeWidth() > 0:
                sl.setStrokeWidth(sl.strokeWidth() * k)
        if isinstance(sl, QgsFillSymbolLayer):
            if hasattr(sl, 'setStrokeWidth') and sl.strokeWidth() > 0:
                sl.setStrokeWidth(sl.strokeWidth() * k)
        # 子符号（白晕、端点圆、多符号渲染器）
        sub = getattr(sl, 'subSymbol', None)
        if callable(sub):
            _scale_symbol(sub(), k)
        if sl.symbolLayerCount() if hasattr(sl, 'symbolLayerCount') else 0:
            for j in range(sl.symbolLayerCount()):
                _scale_symbol_inner = sl.symbolLayer(j)
                if isinstance(_scale_symbol_inner, QgsLineSymbolLayer):
                    _scale_symbol_inner.setWidth(_scale_symbol_inner.width() * k)
                if isinstance(_scale_symbol_inner, QgsMarkerSymbolLayer):
                    _scale_symbol_inner.setSize(_scale_symbol_inner.size() * k)


def _scale_text(tf: QgsTextFormat, k):
    tf.setSize(tf.size() * k)
    tf.setSizeUnit(tf.sizeUnit())
    buf = tf.buffer()
    if buf.size() > 0:
        buf.setSize(buf.size() * k)
        tf.setBuffer(buf)


def scale_layers(k, names=None):
    """把指定（缺省：全部）图层的符号线宽/大小、标注字号与白晕乘 k。"""
    prj = QgsProject.instance()
    todo = []
    for lay in prj.mapLayers().values():
        if names and lay.name() not in names:
            continue
        r = lay.renderer()
        if r is None:
            continue
        if r.type() == 'singleSymbol':
            _scale_symbol(r.symbol(), k)
        elif r.type() == 'categorizedSymbol':
            for cat in r.categories():
                _scale_symbol(cat.symbol(), k)
        elif r.type() == 'graduatedSymbol':
            for rng in r.ranges():
                _scale_symbol(rng.symbol(), k)
        elif r.type() == 'ruleRender':
            pass
        r = None
        lay.triggerRepaint()

        lab = lay.labeling()
        if lab is not None and lab.type() == 'simple':
            s = lab.settings()
            fmt = s.format()
            _scale_text(fmt, k)
            s.setFormat(fmt)
            if s.dist > 0:
                s.dist = s.dist * k
            lay.setLabeling(type(lab)(s))
            lay.triggerRepaint()
        todo.append(lay.name())
    print('scaled by %.2f: %s' % (k, todo))
    return todo