# -*- coding: utf-8 -*-
"""极简 PIL 绘图库（支持中文），用于报告插图。"""
import os
from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"

C_BLUE = (46, 95, 163)
C_ORANGE = (224, 123, 57)
C_GREEN = (60, 141, 90)
C_RED = (178, 60, 60)
C_GRAY = (110, 110, 110)
C_LIGHT = (210, 210, 210)
C_GRID = (225, 228, 233)


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


class Chart:
    def __init__(self, w=1000, h=620, scale=2, xlim=(0, 1), ylim=(0, 1),
                 xlabel="", ylabel="", title="", right_ylim=None, right_ylabel="",
                 left=100, right=60, top=48, bottom=85):
        self.S = scale
        self.W, self.H = w * scale, h * scale
        self.left, self.right = left * scale, w * scale - right * scale
        self.top, self.bottom = top * scale, h * scale - bottom * scale
        self.xlim, self.ylim = xlim, ylim
        self.right_ylim = right_ylim
        self.img = Image.new("RGB", (self.W, self.H), "white")
        self.d = ImageDraw.Draw(self.img)
        self.xlabel, self.ylabel, self.title = xlabel, ylabel, title
        self.right_ylabel = right_ylabel
        self.fs = 17 * scale
        self.fts = 14.5 * scale

    # ---------------------------------------------------------------- 坐标
    def X(self, x):
        a, b = self.xlim
        return self.left + (x - a) / (b - a) * (self.right - self.left)

    def Y(self, y):
        a, b = self.ylim
        return self.bottom - (y - a) / (b - a) * (self.bottom - self.top)

    def RY(self, y):
        a, b = self.right_ylim
        return self.bottom - (y - a) / (b - a) * (self.bottom - self.top)

    def frame(self):
        d = self.d
        d.rectangle([self.left, self.top, self.right, self.bottom], outline=(90, 90, 90), width=2 * self.S)
        # 标题
        if self.title:
            f = font(int(1.35 * self.fs), True)
            bb = d.textbbox((0, 0), self.title, font=f)
            d.text(((self.left + self.right) / 2 - (bb[2] - bb[0]) / 2, self.top - 62 * self.S),
                   self.title, font=f, fill=(30, 30, 30))
        if self.xlabel:
            f = font(self.fs)
            bb = d.textbbox((0, 0), self.xlabel, font=f)
            d.text(((self.left + self.right) / 2 - (bb[2] - bb[0]) / 2, self.bottom + 44 * self.S),
                   self.xlabel, font=f, fill=(40, 40, 40))
        if self.ylabel:
            f = font(self.fs)
            tmp = Image.new("RGBA", (600, 60), (255, 255, 255, 0))
            td = ImageDraw.Draw(tmp)
            bb = td.textbbox((0, 0), self.ylabel, font=f)
            td.text((0, 0), self.ylabel, font=f, fill=(40, 40, 40))
            tmp = tmp.crop((0, 0, bb[2], bb[3])).rotate(90, expand=True)
            self.img.paste(tmp, (22 * self.S, int((self.top + self.bottom) / 2 - tmp.height / 2)), tmp)
        if self.right_ylabel:
            f = font(self.fts)
            bb = d.textbbox((0, 0), self.right_ylabel, font=f)
            d.text((self.right - (bb[2] - bb[0]), self.top - 34 * self.S),
                   self.right_ylabel, font=f, fill=(40, 40, 40))

    def ticks_y(self, ticks, right=False, fmt="{:.0f}", color=(60, 60, 60)):
        d = self.d
        f = font(self.fts)
        for t in ticks:
            y = self.RY(t) if right else self.Y(t)
            d.line([self.left - 8 * self.S, y, self.left, y], fill=(90, 90, 90), width=2 * self.S)
            if right:
                d.line([self.right, y, self.right + 8 * self.S, y], fill=(90, 90, 90), width=2 * self.S)
                d.text((self.right + 14 * self.S, y - 10 * self.S), fmt.format(t), font=f, fill=color)
            else:
                s = fmt.format(t)
                bb = d.textbbox((0, 0), s, font=f)
                d.text((self.left - 16 * self.S - (bb[2] - bb[0]), y - 10 * self.S), s, font=f, fill=color)

    def ticks_x(self, ticks, fmt="{:.0f}"):
        d = self.d
        f = font(self.fts)
        for t in ticks:
            x = self.X(t)
            d.line([x, self.bottom, x, self.bottom + 8 * self.S], fill=(90, 90, 90), width=2 * self.S)
            s = fmt.format(t)
            bb = d.textbbox((0, 0), s, font=f)
            d.text((x - (bb[2] - bb[0]) / 2, self.bottom + 14 * self.S), s, font=f, fill=(60, 60, 60))

    def grid(self, xticks, yticks):
        d = self.d
        for t in yticks:
            y = self.Y(t)
            d.line([self.left, y, self.right, y], fill=C_GRID, width=1 * self.S)
        for t in xticks:
            x = self.X(t)
            d.line([x, self.top, x, self.bottom], fill=C_GRID, width=1 * self.S)

    # ---------------------------------------------------------------- 图元
    def line(self, xs, ys, color=C_BLUE, width=5, marker=None, label=None, dash=False, right=False):
        d = self.d
        pts = [(self.X(x), (self.RY(y) if right else self.Y(y))) for x, y in zip(xs, ys)]
        if dash:
            for i in range(len(pts) - 1):
                x0, y0 = pts[i]
                x1, y1 = pts[i + 1]
                n = max(2, int(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / (12 * self.S)))
                for k in range(n):
                    if k % 2 == 0:
                        d.line([x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n,
                                x0 + (x1 - x0) * (k + 1) / n, y0 + (y1 - y0) * (k + 1) / n],
                               fill=color, width=width)
        else:
            d.line(pts, fill=color, width=width, joint="curve")
        if marker:
            r = 7 * self.S
            for x, y in pts:
                d.ellipse([x - r, y - r, x + r, y + r], fill="white", outline=color, width=3 * self.S)

    def point(self, x, y, color=C_RED, r=7, right=False):
        px, py = self.X(x), (self.RY(y) if right else self.Y(y))
        r = r * self.S
        self.d.ellipse([px - r, py - r, px + r, py + r], fill=color, outline="white", width=2 * self.S)

    def annotate(self, x, y, text, dx=0, dy=-20, color=(40, 40, 40), right=False, bold=False,
                 size=None, anchor="center"):
        px, py = self.X(x), (self.RY(y) if right else self.Y(y))
        f = font(size or self.fts, bold)
        bb = self.d.textbbox((0, 0), text, font=f)
        px += dx * self.S
        py += dy * self.S
        if anchor == "center":
            px -= (bb[2] - bb[0]) / 2
        elif anchor == "right":
            px -= (bb[2] - bb[0])
        self.d.text((px, py), text, font=f, fill=color)

    def band(self, x0, x1, color=(240, 244, 250)):
        self.d.rectangle([self.X(x0), self.top, self.X(x1), self.bottom], fill=color)

    def vline(self, x, color=C_GRAY, dash=True):
        y0, y1 = self.top, self.bottom
        if not dash:
            self.d.line([self.X(x), y0, self.X(x), y1], fill=color, width=2 * self.S)
            return
        n = 40
        for k in range(n):
            if k % 2 == 0:
                ya = y0 + (y1 - y0) * k / n
                yb = y0 + (y1 - y0) * (k + 1) / n
                self.d.line([self.X(x), ya, self.X(x), yb], fill=color, width=2 * self.S)

    def hline(self, y, color=C_GRAY, dash=True):
        x0, x1 = self.left, self.right
        n = 60
        for k in range(n):
            if k % 2 == 0:
                xa = x0 + (x1 - x0) * k / n
                xb = x0 + (x1 - x0) * (k + 1) / n
                self.d.line([xa, self.Y(y), xb, self.Y(y)], fill=color, width=2 * self.S)

    # ---------------------------------------------------------------- 图例
    def legend(self, items, pos="upper left", pad=14):
        """items: [(label, color, style)] style in {'line','dash','marker'}"""
        d = self.d
        f = font(self.fts)
        w = 0
        hs = []
        for label, color, style in items:
            bb = d.textbbox((0, 0), label, font=f)
            hs.append(bb)
            w = max(w, bb[2] - bb[0])
        bw = w + 78 * self.S
        bh = len(items) * 30 * self.S + 2 * pad * self.S
        if pos == "upper left":
            x0, y0 = self.left + 22 * self.S, self.top + 20 * self.S
        elif pos == "upper right":
            x0, y0 = self.right - bw - 22 * self.S, self.top + 20 * self.S
        else:
            x0, y0 = self.left + 22 * self.S, self.bottom - bh - 20 * self.S
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=8 * self.S, fill=(255, 255, 255),
                            outline=(190, 190, 190), width=2 * self.S)
        for k, (label, color, style) in enumerate(items):
            yy = y0 + pad * self.S + k * 30 * self.S + 12 * self.S
            if style == "line":
                d.line([x0 + 14 * self.S, yy, x0 + 52 * self.S, yy], fill=color, width=5 * self.S)
            elif style == "dash":
                for j in range(3):
                    d.line([x0 + 14 * self.S + j * 14 * self.S, yy, x0 + 22 * self.S + j * 14 * self.S, yy],
                           fill=color, width=4 * self.S)
            else:
                r = 6 * self.S
                d.ellipse([x0 + 27 * self.S - r, yy - r, x0 + 27 * self.S + r, yy + r], fill=color)
            d.text((x0 + 62 * self.S, yy - 10 * self.S), label, font=f, fill=(40, 40, 40))

    def save(self, path):
        self.img = self.img.resize((self.W // self.S, self.H // self.S), Image.LANCZOS)
        self.img.save(path, dpi=(200, 200))


def nice_ticks(lo, hi, n=5):
    span = hi - lo
    raw = span / n
    mag = 10 ** int(f"{raw:e}".split("e")[1])
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            step = m * mag
            break
    start = (lo // step) * step
    ticks = []
    v = start
    while v <= hi + 1e-9:
        if v >= lo - 1e-9:
            ticks.append(round(v, 6))
        v += step
    return ticks
