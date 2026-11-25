# 第三方组件与许可

本仓库自己的代码是 MIT（见 `LICENSE`）。下面这些东西不是我的，各自的许可也各不相同。

## 字体

| 文件 | 名称 | 许可 | 来源 |
|---|---|---|---|
| `fonts/SmileySans-Oblique.ttf` | 得意黑 Smiley Sans | SIL Open Font License 1.1 | <https://github.com/atelier-anchor/smiley-sans> |

得意黑随仓库分发（OFL 允许再分发，须保留许可、不得单独售卖字体本身）。用它排版出的图片可以自由使用、商用。

正文用的**微软雅黑**是 Windows 系统字体，**不在**本仓库内，也不能随仓库分发 —— 换机器时若没有雅黑，`board_lib` 会退回其他无衬线字体，版式不会散。

## QGIS 与插件

| 组件 | 许可 | 说明 |
|---|---|---|
| QGIS | GPLv2+ | 本仓库只通过 socket 与运行中的 QGIS 通信，不包含也不链接 QGIS 代码 |
| QGIS MCP 插件 | GPLv2+ | <https://github.com/nkarasiak/qgis-mcp>。**未包含**在本仓库，请从 QGIS 插件市场安装 |

> 说明：本 kit 的脚本跑在**系统 Python**里，通过 TCP 协议请求 QGIS 里那个插件执行 PyQGIS。这种「进程间通信、不链接、不分发」的用法不触发 GPL 的传染性，所以本仓库可以安心用 MIT。插件本身按其 GPLv2+ 分发。

## Python 依赖

| 包 | 许可 |
|---|---|
| Pillow | MIT-CMU (HPND) |

## 数据

`examples/` 里只放了参数模板，**不含**任何实际地理数据。你的 `.qgz` / `.gpkg` 数据按你自己的来源和授权使用；发布图件时在图上写清数据来源。