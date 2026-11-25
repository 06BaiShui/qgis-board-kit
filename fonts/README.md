# 字体

## SmileySans-Oblique.ttf（得意黑）

- **许可**：SIL Open Font License 1.1（OFL-1.1），允许随软件再分发、允许商用，**不得单独售卖字体文件本身**。
- **来源**：<https://github.com/atelier-anchor/smiley-sans>
- **用途**：本 kit 的标题、小标题、图例表头、KPI 数字。

`board_lib.py` 的查找顺序：

1. 环境变量 `BOARD_FONT_DEYI`（换成你自己想用的标题字体时用这个）
2. `<仓库>/fonts/SmileySans-Oblique.ttf`（默认，就是这个文件）
3. `C:/Windows/Fonts/msyhbd.ttc`（微软雅黑粗体 —— 兜底）

三处都找不到时，`quickstart.py` 会报红，标题会退回 PIL 默认字体（很小、很丑），但脚本不崩。

## 正文

微软雅黑：`C:/Windows/Fonts/msyh.ttc`（正文）、`msyhbd.ttc`（粗体）。

系统字体，**不在**本仓库内。macOS / Linux 上请把 `board_lib.py` 里的 `MSYH` / `MSYHB` 改成 `PingFang.ttc` / `NotoSansCJK-Regular.ttc` 之类。

## 想换标题字体

放到 `fonts/` 里，然后：

```bash
set BOARD_FONT_DEYI=fonts/YourFont-Bold.otf     # PowerShell: $env:BOARD_FONT_DEYI="fonts/YourFont-Bold.otf"
```

换字体后**标题的像素高度会变**，`board_lib.new_board()` 里标题基线和黄块位置是按得意黑的字面调的。换了之后先出一张看标题有没有压到黄块上沿，必要时把 `new_board` 的 `ty` 调 ±10 px。