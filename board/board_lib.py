# -*- coding: utf-8 -*-
"""board_lib —— A3 展板排版库（Pillow）。

画布固定 4960×3507 = A3 横版 300dpi。所有坐标单位都是像素，`mm → px` 换算：
1 mm = 11.81 px（300dpi）。

版式语言（照抄即可，别自己发明）：
    左上红色药丸标签 → 居中大标题（得意黑 210px）+ 黄色高亮块 + 手绘框圈住末两字
    → 主体区（地图贴 160,600–3060,2900，右栏 x=3200 宽 1520）
    → 红色竖条小标题（section）、正文（para，42px/行高 62）
    → 底部横向图例两排 + 一行灰色口径注（foot）

字体与目录可用环境变量覆盖：
    BOARD_ROOT   仓库根目录（默认按本文件位置推导）
    BOARD_OUT    成品输出目录（默认 <ROOT>/out）
    BOARD_FONT_DEYI / BOARD_FONT_BODY / BOARD_FONT_BOLD
"""
from PIL import Image, ImageDraw, ImageFont
import json
import os
import time
from pathlib import Path

ROOT = os.environ.get('BOARD_ROOT') or (str(Path(__file__).resolve().parent.parent) + os.sep)
OUT_DIR = os.environ.get('BOARD_OUT') or os.path.join(ROOT, 'out')
W, H = 4960, 3507                      # A3 横版 300dpi

_DEYI_CANDIDATES = [
    os.environ.get('BOARD_FONT_DEYI') or '',
    os.path.join(ROOT, 'fonts', 'SmileySans-Oblique.ttf'),
    'C:/Windows/Fonts/msyhbd.ttc',     # 兜底：没有得意黑时用雅黑粗体（版式不变，气质会差一点）
]
DEYI = next((p for p in _DEYI_CANDIDATES if p and os.path.exists(p)), 'C:/Windows/Fonts/msyhbd.ttc')
YH = os.environ.get('BOARD_FONT_BODY') or 'C:/Windows/Fonts/msyh.ttc'
YHB = os.environ.get('BOARD_FONT_BOLD') or 'C:/Windows/Fonts/msyhbd.ttc'

RED = (230, 0, 51)
YELLOW = (255, 230, 0)
INK = (20, 20, 20)
GRAY = (120, 120, 120)
LGRAY = (200, 200, 200)
BODY = (60, 60, 60)
PUNCT = '，。；、）”%：？！'


def f(path, size):
    return ImageFont.truetype(path, size)


def new_board(tag, title, hl=None, box_last=True):
    board = Image.new('RGB', (W, H), (255, 255, 255))
    d = ImageDraw.Draw(board, 'RGBA')
    tf = f(DEYI, 60)
    tb = d.textbbox((0, 0), tag, font=tf)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    d.rounded_rectangle((160, 140, 160 + tw + 72, 140 + th + 48), radius=24, fill=RED)
    d.text((160 + 36, 140 + 20 - tb[1]), tag, font=tf, fill=(255, 255, 255))
    tf = f(DEYI, 210)
    widths = [d.textlength(title[:i + 1], font=tf) for i in range(len(title))]
    tx = (W - widths[-1]) / 2
    ty = 300
    if hl:
        s, e = hl
        x0 = tx + (widths[s - 1] if s > 0 else 0)
        d.rounded_rectangle((x0 - 10, ty + 40, tx + widths[e] + 10, ty + 225),
                            radius=18, fill=YELLOW + (120,))
    d.text((tx, ty), title, font=tf, fill=INK)
    if box_last:
        bx0 = tx + widths[-2] - 16
        bx1 = tx + widths[-1] + 22
        d.rounded_rectangle((bx0, ty - 12, bx1, ty + 228), radius=34, outline=INK, width=10)
    return board, d


def paste_fit(board, img, box):
    """把图片按 box 等比缩放居中贴上；img 可传路径（绝对路径，或相对 ROOT）或 PIL Image。"""
    if isinstance(img, str):
        path = img if (os.path.isabs(img) or os.path.exists(img)) else ROOT + img
        img = Image.open(path).convert('RGB')
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    sc = min(bw / img.width, bh / img.height)
    dw, dh = int(img.width * sc), int(img.height * sc)
    img = img.resize((dw, dh), Image.LANCZOS)
    mx, my = x0 + (bw - dw) // 2, y0 + (bh - dh) // 2
    board.paste(img, (mx, my))
    return mx, my, dw, dh


def north(board, x, y, scale=1.0, dark=False):
    S = 4
    aw, ah = 240 * S, 320 * S
    arrow = Image.new('RGBA', (aw, ah), (0, 0, 0, 0))
    ad = ImageDraw.Draw(arrow)
    ink = (255, 255, 255, 255) if dark else INK + (255,)
    paper = INK + (255,) if dark else (255, 255, 255, 255)
    tip = (aw // 2, 10 * S)
    left = (50 * S, 300 * S)
    notch = (aw // 2, 225 * S)
    right = (190 * S, 300 * S)
    ad.polygon([tip, left, notch], fill=ink)
    ad.polygon([tip, right, notch], fill=paper, outline=ink, width=6 * S)
    w, h = int(240 * scale), int(320 * scale)
    arrow = arrow.resize((w, h), Image.LANCZOS)
    board.paste(arrow, (x, y), arrow)


# 比例尺的可选档位（米）。别随便加：要保证一半长度也是整数。
_NICE_M = (50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 50000)


def _nice_bar(mpp, px_min=220, px_max=640):
    """按 mpp 选一个「画出来 220–640 px 长」的整数档位；都不合适就取最接近区间中点的那档。"""
    for m in _NICE_M:
        if px_min <= m / mpp <= px_max:
            return m
    mid = (px_min + px_max) / 2
    return min(_NICE_M, key=lambda m: abs(m / mpp - mid))


def scalebar(d, mpp, cx, y, bar_m=None, fs=44, dark=False):
    """黑白相间比例尺。mpp = 每像素米数（素图 .json 里的 mpp）。

    bar_m 不传就自动选档（100 / 500 / 5000 …），避免「1 km 只有 50 px、三个标签糊成一团」。
    """
    col = (255, 255, 255) if dark else INK
    if not bar_m:
        bar_m = _nice_bar(mpp)
    bar_px = max(int(round(bar_m / mpp)), 16)
    half = bar_px // 2
    sx = cx - bar_px // 2
    d.rectangle((sx, y, sx + half, y + 26), fill=col)
    d.rectangle((sx + half, y, sx + bar_px, y + 26),
                fill=(0, 0, 0, 0) if dark else (255, 255, 255), outline=col, width=4)

    sf = f(YH, fs)

    def tw(t):
        bb = d.textbbox((0, 0), t, font=sf)
        return bb[2] - bb[0]

    end_txt = ('%g 公里' % (bar_m / 1000)) if bar_m >= 1000 else ('%d 米' % bar_m)
    labels = [('0', sx)]
    # 中间那条标 500 / 250 / 2.5 都会串味：只在 ≤1 km 且两侧留得下时才标
    mid_txt = str(bar_m // 2)
    if bar_m <= 1000 and bar_px >= tw(mid_txt) + tw(end_txt) * 1.15 + 40:
        labels.append((mid_txt, sx + half))
    labels.append((end_txt, sx + bar_px))

    for val, px in labels:
        w = tw(val)
        x = px - w / 2
        x = max(8, min(x, W - w - 8))            # 别冲出画布
        d.text((x, y + 34), val, font=sf, fill=col)


def wrap(d, text, font, maxw):
    lines, cur = [], ''
    for ch in text:
        glue = ch.isdigit() and cur[-1:].isdigit()   # 数字不拆行（300 米 不会被断成 3 / 00）
        if not glue and d.textlength(cur + ch, font=font) > maxw and ch not in PUNCT:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def para(d, x, y, text, fs=52, maxw=4640, lh=None, color=BODY, font=YH):
    ft = f(font, fs)
    lh = lh or int(fs * 1.62)
    for ln in wrap(d, text, ft, maxw):
        d.text((x, y), ln, font=ft, fill=color)
        y += lh
    return y


def section(d, x, y, text, fs=84):
    d.rounded_rectangle((x, y + 4, x + 16, y + fs + 6), radius=8, fill=RED)
    d.text((x + 40, y), text, font=f(DEYI, fs), fill=INK)
    return y + fs + 30


def legend(d, x, y, items, step=146, fs=54, sw=72, header='图例'):
    if header:
        d.text((x, y), header, font=f(DEYI, 96), fill=INK)
        d.rounded_rectangle((x + 4, y + 110, x + 190, y + 132), radius=11, fill=RED)
        y += 210
    lbf = f(YH, fs)
    for kind, name, c in items:
        if isinstance(c, str):
            c = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
        if kind == 'box':
            d.rounded_rectangle((x, y, x + sw, y + sw), radius=16, fill=c,
                                outline=(0, 0, 0, 60), width=2)
        elif kind == 'line':
            d.line((x, y + sw // 2, x + sw, y + sw // 2), fill=c, width=10)
        elif kind == 'dot':
            r = int(sw * 0.32)
            d.ellipse((x + sw // 2 - r, y + sw // 2 - r, x + sw // 2 + r, y + sw // 2 + r), fill=c)
        d.text((x + sw + 32, y + (sw - fs) // 2 - 4), name, font=lbf, fill=INK)
        y += step
    return y


def table(d, x, y, colw, headers, rows, fs=42, hfs=46, pad=16):
    lh = fs + 14
    hf = f(YHB, hfs)
    bf = f(YH, fs)
    hh = hfs + 2 * pad
    top = y
    cx = x
    for w, htxt in zip(colw, headers):
        d.rectangle((cx, y, cx + w, y + hh), fill=RED)
        bb = d.textbbox((0, 0), htxt, font=hf)
        d.text((cx + (w - (bb[2] - bb[0])) / 2, y + pad - bb[1] + 4), htxt, font=hf, fill=(255, 255, 255))
        cx += w
    y += hh
    for ri, row in enumerate(rows):
        cells = [wrap(d, str(c), bf, w - 2 * pad) for c, w in zip(row, colw)]
        rh = max(len(c) for c in cells) * lh + 2 * pad
        cx = x
        fill = (255, 255, 255) if ri % 2 == 0 else (248, 248, 248)
        for lines, w in zip(cells, colw):
            d.rectangle((cx, y, cx + w, y + rh), fill=fill)
            yy = y + pad
            for ln in lines:
                d.text((cx + pad, yy), ln, font=bf, fill=INK)
                yy += lh
            cx += w
        d.line((x, y, x + sum(colw), y), fill=LGRAY, width=2)
        y += rh
    cx = x
    for w in colw:
        d.line((cx, top, cx, y), fill=LGRAY, width=2)
        cx += w
    d.rectangle((x, top, x + sum(colw), y), outline=INK, width=3)
    return y


def photo(board, d, path, box, caption, fs=42, anchor='center'):
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    img = Image.open(ROOT + 'photos/' + path).convert('RGB')
    sc = max(bw / img.width, bh / img.height)
    dw, dh = int(img.width * sc), int(img.height * sc)
    img = img.resize((dw, dh), Image.LANCZOS)
    lx = (dw - bw) // 2
    ty = {'center': (dh - bh) // 2, 'bottom': dh - bh, 'top': 0}[anchor]
    board.paste(img.crop((lx, ty, lx + bw, ty + bh)), (x0, y0))
    d.rectangle((x0, y0, x1, y1), outline=INK, width=4)
    d.text((x0, y1 + 14), caption, font=f(YH, fs), fill=INK)
    return y1 + 14 + fs + 14


def photo_empty(board, d, box, theme, fs=40):
    x0, y0, x1, y1 = box
    dash, gap = 24, 16
    for xx in range(x0, x1, dash + gap):
        d.line((xx, y0, min(xx + dash, x1), y0), fill=GRAY, width=4)
        d.line((xx, y1, min(xx + dash, x1), y1), fill=GRAY, width=4)
    for yy in range(y0, y1, dash + gap):
        d.line((x0, yy, x0, min(yy + dash, y1)), fill=GRAY, width=4)
        d.line((x1, yy, x1, min(yy + dash, y1)), fill=GRAY, width=4)
    tf = f(DEYI, 64)
    bb = d.textbbox((0, 0), '待自摄', font=tf)
    d.text(((x0 + x1 - (bb[2] - bb[0])) / 2, (y0 + y1) / 2 - 60), '待自摄', font=tf, fill=GRAY)
    bf = f(YH, fs)
    bb = d.textbbox((0, 0), theme, font=bf)
    d.text(((x0 + x1 - (bb[2] - bb[0])) / 2, (y0 + y1) / 2 + 20), theme, font=bf, fill=GRAY)


def marker(d, x, y, n, color=RED, r=40):
    d.ellipse((x - r, y - r, x + r, y + r), fill=color, outline=(255, 255, 255), width=6)
    tf = f(DEYI, 52)
    s = str(n)
    bb = d.textbbox((0, 0), s, font=tf)
    d.text((x - (bb[2] - bb[0]) / 2, y - (bb[3] - bb[1]) / 2 - bb[1]), s, font=tf, fill=(255, 255, 255))


def markers_on_map(d, gmeta, placed):
    mx, my, dw, dh = placed
    e = gmeta['extent']
    for it in gmeta['items']:
        px = mx + (it['cx'] - e[0]) * dw / (e[2] - e[0])
        py = my + (e[3] - it['cy']) * dh / (e[3] - e[1])
        marker(d, px, py, it['num'])


def grad_legend(d, x, y, w=800, h=48):
    stops = [(0, (13, 13, 38)), (0.25, (0, 90, 180)), (0.5, (0, 200, 120)),
             (0.75, (255, 230, 0)), (1, (230, 0, 18))]
    for i in range(w):
        t = i / w
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                k = (t - t0) / (t1 - t0)
                c = tuple(int(a + (b - a) * k) for a, b in zip(c0, c1))
                break
        d.line((x + i, y, x + i, y + h), fill=c)
    d.rectangle((x, y, x + w, y + h), outline=INK, width=3)
    sf = f(YH, 44)
    d.text((x, y + h + 12), '低', font=sf, fill=INK)
    bb = d.textbbox((0, 0), '高', font=sf)
    d.text((x + w - (bb[2] - bb[0]), y + h + 12), '高', font=sf, fill=INK)


def panel_title(d, x, y, text, fs=72):
    d.rounded_rectangle((x, y + 6, x + 14, y + fs + 2), radius=7, fill=RED)
    d.text((x + 36, y), text, font=f(DEYI, fs), fill=INK)


def foot(board, d, note, items, rows=1, x=160, y=2940):
    """底部图例（每行 4 条，横排）+ 一行灰色口径注。items 同 legend()。"""
    for j, it in enumerate(items):
        legend(d, x + (j % 4) * 720, y + (j // 4) * 118, [it], step=0,
               fs=44, sw=56, header=None)
    d.text((x, y + rows * 118 + 24), note, font=f(YH, 38), fill=GRAY)


def save(board, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    # 大 PNG 存盘偶发瞬时 EINVAL（杀软/索引占用），重试可过
    for i in range(3):
        try:
            board.save(path)
            break
        except OSError:
            if i == 2:
                raise
            time.sleep(1)
    print('saved', path)
    return path