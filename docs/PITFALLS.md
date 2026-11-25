# 踩坑记录

每条都是我真踩过的：**现象 → 原因 → 修法**。按顺序读一遍能省掉一晚上的瞎试。

---

## 一、跟 QGIS 通信

### 1. 端口不是 9876

**现象**：`ConnectionRefusedError`，插件明明开了。
**原因**：插件默认 9876，但端口被占时会自己换（常见 9877），而且界面上不一定显眼提示。
**修法**：`python quickstart.py` 会 ping 出来；或者 `$env:QGIS_MCP_PORT=9877`。**先确认端口再查代码**。

### 2. 参数名是 `layer_id`

**现象**：`get_layer_features` 报 `missing a required argument: 'layer_id'`。
**原因**：直觉会写 `{"layer": "镇界"}`。
**修法**：所有图层相关的命令都是 `layer_id`。别按名字猜参数名，看 `qgis/mcp_client.py` 的 docstring。

### 3. `execute_code` 里的脚本带 BOM

**现象**：`SyntaxError: invalid non-printable character U+FEFF`。
**原因**：PowerShell `Set-Content -Encoding utf8` 会写 BOM；`execute_code` 把它当 Python 源码解析。
**修法**：`open(path, encoding='utf-8-sig').read()`（`run_qgis.py` 已经这么做了）。**在 Windows 上写脚本别再手搓 `Set-Content`**。

### 4. 注入执行的脚本不能有 `from __future__`

**现象**：`SyntaxError: from __future__ imports must occur at the beginning of the file`。
**原因**：`run_qgis.py` 会在你的脚本前面插一行 prelude（`sys.path.insert(...)`），于是你的 `from __future__ ...` 掉到了第二行。
**修法**：删掉那行。Python 3 现在不需要它。

### 5. 在 PowerShell 里跑中文 `python -c` 是灾难

**现象**：`python -c "print('中文')"` 各种引号被吃掉、或输出乱码。
**修法**：**不要**用 `-c` 传中文或复杂引号。要么把逻辑写成 `.py` 文件再执行，要么让结果落到 JSON 文件里再读。

### 6. `>` 重定向写出 UTF-16

**现象**：`python x.py > log.txt`，用文本编辑器/工具读 log.txt 报「二进制文件」。
**原因**：PowerShell 的 `>` 默认 UTF-16LE（带 BOM）。
**修法**：`python x.py | Out-File -Encoding utf8 log.txt`，或者脚本里自己 `open(..., encoding='utf-8')` 写。

---

## 二、工程与数据

### 7. 内存里的工程和磁盘上的不是一回事

**现象**：脚本说工程有 45 个图层，`.qgz` 里明明有 48 个；某几个图层「消失了」。
**原因**：`QgsProject.instance()` 的是当前会话状态，之前 `write()` / `read()` 出过岔子就会差几个图层。**内存态不可信**。
**修法**：`iface.addProject(r"...\工程.qgz")` 重新加载后再干活；或者用独立的 `QgsProject().read(路径)` 只读取清单来核对。

### 8. 改共享图层样式会污染其他版面

**现象**：为了让某张图淡一点，把 `用地` 透明度调到 0.3，另外 12 张同源版面全变淡了。
**原因**：一个工程里的图层对象是共享的，渲染器样式跟着图层走，不跟版面走。
**修法**：**给具体版面建专用副本层**（`绿道·底衬淡` = 用地层的另一个实例，只改副本），原层 opacity 恢复 1.0。这也是本 kit 采用「渲染时临时改样式 + 不保存工程」的根本原因。

### 9. 「镇域范围」不一定真是镇界

**现象**：拿「镇域范围」图层当边界画，满图红虚线网，像是渲染穿帮。
**原因**：那个图层其实是 **447 个用地斑块的并集**（面积 = 各大类面积之和），斑块之间有空隙，所以虚线到处断。
**修法**：看清 `area` 是否等于用地面积合计；真正的边界另找一个「行政区」图层。**任何「XX范围」先看要素数和面积再信它**。

### 10. 统计数要对得上三遍

**现象**：正文写「13 个公园 + 4 个居住组团」，图上实际是 12 + 5。
**原因**：早期版本删过重复点、又合并过邻近点，编号没同步。
**修法**：所有对外数字从图层现数（`get_layer_features` → 计数），别从文档里抄；写进正文前跑一次一致性检查。

---

## 三、地图渲染

### 11. 地图一片白 / 跑到非洲

**现象**：版面里地图区纯白，或出现完全无关的地物。
**原因**：**extent 的数值和地图 CRS 不是一套**。最典型：extent 用 EPSG:4547 的米值（`76万, 433万`），地图 CRS 却是工程默认 3857 → 那坐标跑到北非去了。
**修法**：`map.setCrs(QgsCoordinateReferenceSystem("EPSG:4547"))`，或 spec 里显式 `"crs": "EPSG:4547"`。**extent 与 CRS 必须成对出现**。

### 12. `QgsFillSymbol` 少了 color 键 → 默认纯蓝

**现象**：只想描边不填色的面，渲染成了刺眼的纯蓝实心。
**原因**：`createSimple` 的 props 缺 `color` 时取默认值 `0,0,255`，与 `style` 无关。
**修法**：显式给 `"color": "0,0,0,0"`（透明）+ `"style": "no"`。

### 13. 多边形上的标签会沿边界弯曲

**现象**：给「半径 400 m 的服务圈」加名称标注，字沿着圆弧排了一整圈。
**原因**：多边形图层 + `OrderedPositionsAroundPoint` → 引擎沿边界布点。
**修法**：**把面取质心写成点图层**再标注（`make_nodepoints.py` 就是干这个的）。面用来画符号，点用来挂标签。

### 14. 标签压住了自己的符号

**现象**：命名「运河文化旅游区」，显示成「⊙河文化旅游区」——第一个字被点盖住。
**原因**：`xOffset` 在 `OrderedPositionsAroundPoint` 模式下**不生效**（dump 里存了，渲染无视）；真正管用的是 `QgsPalLayerSettings.dist`（默认 0）。
**修法**：`s.dist = 3.8`（点直径 4.6 mm 时）；`s.distUnits = QgsUnitTypes.LayoutMillimeters`。**dist 要大于符号半径**，否则永远被压。

### 15. 复制版面会带上旧地图

**现象**：新图上隐约透出旧图的路网/红色虚线，像是图层没删干净。
**原因**：`duplicateLayout()` 把地图项一起复制了，它还在原位渲染，只是被新元素盖住。
**修法**：删除旧元素时**把 `QgsLayoutItemMap` 也删掉**（按类型 + 坐标判断），或直接改复用的那个地图项。

### 16. `img.save()` 失败不抛异常

**现象**：脚本全绿，但没有文件。
**原因**：`QImage.save()` 目录不存在时返回 `False`，不抛错。
**修法**：`os.makedirs(dirname, exist_ok=True)` 之后再存，并检查返回值。

---

## 四、字体与排版

### 17. 中文字体名要写中文

**现象**：QGIS 每次加载工程弹模态警告「字体 SimHei 未找到」，字却显示正常。
**原因**：本机 Qt 只登记了中文名「黑体」，用英文名 `SimHei` 匹配不上（字体文件其实在）。
**修法**：`QFont(); f.setFamily("黑体")`，并且**显式 `setFont` 写回**才落盘（`QgsTextFormat.font()` 拿到的是替代后的家族）。

### 18. 数字被排版切开

**现象**：「服务半径 300 米」被断成「半径 3 / 00 米」。
**原因**：逐字折行的 `wrap()` 只避开了英文单词边界，不认数字串。
**修法**：折行时若相邻两字符都是数字则不在此处断（`glue = ch.isdigit() and cur[-1:].isdigit()`）。

### 19. 中文文件名读不了

**现象**：看图/读图的工具报「binary file」或打不开 `14绿道网络规划图.png`。
**修法**：复制一份 ASCII 名（`copy 14绿道网络规划图.png p14.png`）再读。**交付时保留中文名，调试时用 ASCII 名**。

---

## 五、一句话总结

- **别信内存态**，信磁盘文件。
- **别动共享层**，建副本。
- **extent 和 CRS 成对**。
- **面用点挂标签**，`dist` 不是 `xOffset`。
- **中文路径、BOM、UTF-16、引号** —— Windows 上这四样能把人耗死，绕开而不是硬刚。