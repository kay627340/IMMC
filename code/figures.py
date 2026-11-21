# -*- coding: utf-8 -*-
"""生成报告插图。"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chart import (Chart, C_BLUE, C_ORANGE, C_GREEN, C_RED, C_GRAY, C_LIGHT,
                   font, nice_ticks)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figures")
DATA = json.load(open(os.path.join(ROOT, "output", "results.json"), encoding="utf-8"))


def fig_budget():
    bc = DATA["budget_curve"]
    xs = [p["B"] for p in bc]
    ys = [p["success"] for p in bc]
    c = Chart(xlim=(200, 1100), ylim=(150, 190), xlabel="每日总预算 B（单位成本）",
              ylabel="期望成功回答数（条）", title="", top=45)
    xt = list(range(200, 1101, 100))
    yt = list(range(150, 191, 5))
    c.grid(xt, yt)
    c.frame()
    c.ticks_x(xt)
    c.ticks_y(yt)
    c.line(xs, ys, color=C_BLUE, width=5, label="H=20")
    # H=0 参考线（由任务2无人工最优解在若干预算下重算）
    h0 = {200: 155.0, 400: 170.0, 520: 176.0, 600: 175.5, 760: 177.1, 840: 177.4, 900: 177.5}
    # 说明：H=0 时无法使用人工，改用任务2的 B 方案数据点
    c.line([600], [175.5], color=C_ORANGE, width=5, marker=True)
    c.annotate(600, 175.5, "无人工最优 175.5", dx=10, dy=18, color=C_ORANGE)
    for (x, y, t, dx, dy) in [(400, 170.0, "170.0", -6, -22), (520, 176.0, "176.0", -8, -24),
                              (600, 178.0, "178.0（基准）", 0, -30), (760, 182.0, "182.0", -4, -26),
                              (840, 182.7, "182.7", 4, -26)]:
        c.point(x, y, color=C_RED, r=6)
        c.annotate(x, y, t, dx=dx, dy=dy, color=(120, 30, 30), bold=True)
    c.vline(840, color=C_GRAY)
    c.annotate(836, 187.4, "B=840：人工名额用满", dx=0, dy=0, color=C_GRAY, size=12 * 2, anchor="right")
    c.annotate(300, 187.2, "跨资料综合升级  +7.5%/单位", dx=0, dy=0, color=(80, 80, 80), size=12 * 2)
    c.save(os.path.join(FIG, "fig1_budget.png"))


def fig_human():
    hc = DATA["human_curve"]
    c = Chart(xlim=(0, 30), ylim=(174, 185), xlabel="人工复核名额上限 H（条/日）",
              ylabel="期望成功回答数（条）", title="", top=45)
    xt = list(range(0, 31, 5))
    yt = list(range(174, 186, 2))
    c.grid(xt, yt)
    c.frame()
    c.ticks_x(xt)
    c.ticks_y(yt)
    for B, col, lab in (("600", C_BLUE, "B=600"), ("900", C_GREEN, "B=900")):
        pts = hc[B]
        c.line([p["H"] for p in pts], [p["success"] for p in pts], color=col, width=5, marker=True)
        c.annotate(30, pts[-1]["success"], lab, dx=-30, dy=14, color=col, bold=True)
    c.vline(10, color=C_GRAY)
    c.annotate(10, 174.4, "H=10", dx=0, dy=0, color=C_GRAY)
    c.annotate(20, 174.4, "H=20", dx=0, dy=0, color=C_GRAY)
    c.vline(20, color=C_GRAY)
    c.save(os.path.join(FIG, "fig2_human.png"))


def fig_surge():
    sg = DATA["surge_type4"]
    c = Chart(xlim=(10, 40), ylim=(170, 192), xlabel="例外情况处理请求数 n4（总请求数随之增加，预算固定 600）",
              ylabel="期望成功回答数（条）", title="", top=45,
              right_ylim=(0.80, 0.90), right_ylabel="整体成功率", right=150)
    xt = list(range(10, 41, 5))
    yt = list(range(170, 193, 4))
    c.grid(xt, yt)
    c.frame()
    c.ticks_x(xt)
    c.ticks_y(yt)
    c.ticks_y([0.80, 0.82, 0.84, 0.86, 0.88, 0.90], right=True, fmt="{:.0%}", color=C_ORANGE)
    c.line([p["n4"] for p in sg], [p["success"] for p in sg], color=C_BLUE, width=5, marker=True)
    c.line([p["n4"] for p in sg], [p["rate"] for p in sg], color=C_ORANGE, width=4, dash=True, right=True)
    c.annotate(40, sg[-1]["success"], f"{sg[-1]['success']:.1f}", dx=-14, dy=-28, color=C_BLUE, bold=True)
    c.annotate(40, sg[-1]["rate"], f"{sg[-1]['rate']:.1%}", dx=-10, dy=16, color=C_ORANGE, bold=True, right=True)
    c.legend([("成功回答数（左轴）", C_BLUE, "line"), ("整体成功率（右轴）", C_ORANGE, "dash")], "lower left")
    c.save(os.path.join(FIG, "fig3_surge.png"))


def fig_plans():
    plans = DATA["task2"]["plans"]
    keys = ["A", "B", "C", "D", "ALLUP"]
    labels = ["A 全部直发", "B 无人工最优", "C 全局最优", "D 强制满人工", "全升级参考"]
    colors = [C_GRAY, (120, 160, 205), C_BLUE, C_ORANGE, C_GREEN]
    c = Chart(xlim=(0, 5), ylim=(140, 192), xlabel="", ylabel="期望成功回答数（条）",
              title="", top=45, bottom=100)
    yt = list(range(140, 193, 5))
    c.grid([0.5 + i for i in range(5)], yt)
    c.frame()
    c.ticks_y(yt)
    c.ticks_x([0.5 + i for i in range(5)], fmt="")
    for i, k in enumerate(keys):
        v = plans[k]["success"]
        x0 = 0.5 + i
        w = 0.32
        left, right = c.X(x0 - w / 2), c.X(x0 + w / 2)
        top, bot = c.Y(v), c.Y(140)
        c.d.rectangle([left, top, right, bot], fill=colors[i], outline="white", width=3 * c.S)
        c.annotate(x0, v + 1.0, f"{v:.1f}", dx=0, dy=-14, bold=True, color=(30, 30, 30))
        f = font(12 * 2)
        bb = c.d.textbbox((0, 0), labels[i], font=f)
        c.d.text((c.X(x0) - (bb[2] - bb[0]) / 2, c.bottom + 14 * c.S), labels[i], font=f, fill=(40, 40, 40))
        f2 = font(11 * 2)
        s2 = f"成本 {plans[k]['cost']:.0f}"
        bb2 = c.d.textbbox((0, 0), s2, font=f2)
        c.d.text((c.X(x0) - (bb2[2] - bb2[0]) / 2, c.bottom + 38 * c.S), s2, font=f2, fill=(110, 110, 110))
    c.hline(155, color=C_GRAY)
    c.save(os.path.join(FIG, "fig4_plans.png"))


def fig_mc():
    mc = DATA["mc"]
    keys = ["A", "B", "C", "D"]
    labels = ["A 全部直发", "B 无人工最优", "C 全局最优", "D 强制满人工"]
    colors = [C_GRAY, (120, 160, 205), C_BLUE, C_ORANGE]
    c = Chart(xlim=(140, 196), ylim=(0.2, 4.7), xlabel="单日实际成功回答数（40 000 次模拟）",
              ylabel="", title="", top=45)
    xt = list(range(140, 197, 5))
    c.grid(xt, [1, 2, 3, 4])
    c.frame()
    c.ticks_x(xt)
    h = 0.34
    for i, k in enumerate(keys):
        y = 4 - i
        d = mc[k]
        p5, p25, p75, p95, mean = d["p5"], d["p5"], d["p95"], d["p95"], d["mean"]
        col = colors[i]
        c.d.rectangle([c.X(p5), c.Y(y + h / 2), c.X(p95), c.Y(y - h / 2)], fill=(245, 247, 250),
                      outline=col, width=2 * c.S)
        c.d.line([c.X(mean), c.Y(y - h / 2), c.X(mean), c.Y(y + h / 2)], fill=col, width=5 * c.S)
        for xx in (p5, p95):
            c.d.line([c.X(xx), c.Y(y + h / 2 + 0.07), c.X(xx), c.Y(y - h / 2 - 0.07)], fill=col, width=3 * c.S)
        f = font(12 * 2)
        bb = c.d.textbbox((0, 0), labels[i], font=f)
        c.d.text((c.left - 22 * c.S - (bb[2] - bb[0]), c.Y(y) - 10 * c.S), labels[i], font=f, fill=(40, 40, 40))
        c.annotate(p5, y + 0.42, f"均值 {mean:.1f} ｜ 5%–95% 分位 {p5:.0f}–{p95:.0f}", dx=0, dy=0,
                   color=(50, 50, 50), size=11 * 2, anchor="left")
    c.save(os.path.join(FIG, "fig5_mc.png"))


if __name__ == "__main__":
    fig_budget()
    fig_human()
    fig_surge()
    fig_plans()
    fig_mc()
    print("figures saved")
