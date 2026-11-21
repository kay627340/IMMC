# -*- coding: utf-8 -*-
"""导出结果数据到 Excel。"""
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = json.load(open(os.path.join(ROOT, "output", "results.json"), encoding="utf-8"))
NAMES = ["单项信息查询", "多条件判断", "跨资料综合", "例外情况处理"]

HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
BODY_FONT = Font(name="微软雅黑", size=10)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)


def sheet(wb, title, headers, rows, widths=None, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill, cell.font, cell.alignment, cell.border = HDR_FILL, HDR_FONT, CENTER, BORDER
    for r in rows:
        ws.append(r)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=len(headers)):
        for cell in row:
            cell.font, cell.alignment, cell.border = BODY_FONT, CENTER, BORDER
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 30
    for i in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(i)].width = (widths or [14] * len(headers))[i - 1]
    return ws


wb = Workbook()

# 基础参数
rows = []
for i, name in enumerate(NAMES):
    rows.append([name, DATA["task1"]["marginal"][i]["n"], 1, 5, 13,
                 DATA["task1"]["marginal"][i]["p1"], DATA["task1"]["marginal"][i]["p2"],
                 DATA["task1"]["marginal"][i]["p3"]])
sheet(wb, "基础参数", ["请求类型", "每日数量", "直接成本", "升级成本", "人工成本", "直接成功率", "升级成功率", "人工成功率"],
      rows, [16, 10, 10, 10, 10, 12, 12, 12], first=True)

# 任务1 边际
rows = []
for m in DATA["task1"]["marginal"]:
    rows.append([m["name"], m["d_up"], m["r_up"], m["d_man"], m["r_man"], m["d_man_up"], m["r_man_up"]])
sheet(wb, "任务1_边际分析", ["请求类型", "升级增益", "升级性价比(%/单位)", "人工(对直发)增益",
                          "人工性价比(%/单位)", "人工(对升级)增益", "人工升级边际性价比(%/单位)"],
      rows, [16, 11, 16, 15, 16, 15, 18])

# 任务2 方案
rows = [["全部直接发布", 200, 0, 155.0, 0.775, 200 / 155]]
for k, lab in [("B", "无人工最优"), ("C", "全局最优"), ("D", "强制满人工")]:
    p = DATA["task2"]["plans"][k]
    rows.append([lab, p["cost"], p["human"], round(p["success"], 2), round(p["rate"], 4),
                 round(p["cost_per_success"], 3)])
p = DATA["task2"]["plans"]["ALLUP"]
rows.append(["全部升级（参考）", p["cost"], 0, p["success"], p["rate"], p["cost_per_success"]])
p = DATA["task2"]["plans"]["ALLMAN"]
rows.append(["全部人工（参考）", p["cost"], 200, p["success"], p["rate"], p["cost_per_success"]])
ws = sheet(wb, "任务2_方案对比", ["方案", "总成本", "人工条数", "期望成功数", "整体成功率",
                               "单条成功成本"], rows, [18, 10, 10, 12, 11, 14])
for r in range(2, ws.max_row + 1):
    ws.cell(row=r, column=5).number_format = "0.0%"
    ws.cell(row=r, column=6).number_format = "0.000"

# 任务2 分配明细
rows = []
for i, (d, a, b) in enumerate(DATA["task2"]["opt"]["alloc"]):
    p1, p2, p3 = (DATA["task1"]["marginal"][i][k] for k in ("p1", "p2", "p3"))
    rows.append([NAMES[i], DATA["task1"]["marginal"][i]["n"], d, a, b,
                 round(d * p1 + a * p2 + b * p3, 2)])
rows.append(["合计", 200, sum(r[2] for r in rows), sum(r[3] for r in rows), sum(r[4] for r in rows),
             round(sum(r[5] for r in rows), 2)])
sheet(wb, "任务2_最优分配", ["请求类型", "总数", "直接发布", "升级处理", "人工复核", "期望成功数"],
      rows, [16, 8, 10, 10, 10, 12])

# 预算敏感
rows = []
for p in DATA["budget_curve"]:
    if p["B"] % 25 == 0 or p["B"] in (520, 680, 760, 840):
        rows.append([p["B"], round(p["success"], 2), round(p["success"] / 200, 4), p["cost"], p["human"],
                     "/".join(f"{a}-{b}-{c}" for a, b, c in p["alloc"])])
sheet(wb, "情景_预算", ["预算B", "期望成功数", "成功率", "总成本", "人工条数", "分配(直发-升级-人工)"],
      rows, [10, 12, 10, 10, 10, 44])

# 人工容量
rows = []
for H in range(0, 31):
    r = [H] + [DATA["human_curve"][B][H]["success"] for B in ("600", "700", "800", "900")]
    rows.append(r)
sheet(wb, "情景_人工容量", ["人工上限H", "B=600", "B=700", "B=800", "B=900"], rows, [12, 12, 12, 12, 12])

# 冲击
rows = [[p["n4"], p["N"], round(p["success"], 2), round(p["rate"], 4)] for p in DATA["surge_type4"]]
sheet(wb, "情景_高难度潮", ["n4", "总请求数N", "期望成功数", "成功率"], rows, [8, 12, 12, 10])
rows = [[p["shift"], p["n"][0], p["n"][3], round(p["success"], 2), round(p["rate"], 4)]
        for p in DATA["surge_struct"]]
sheet(wb, "情景_结构变化", ["类型1减少/类型4增加", "n1", "n4", "期望成功数", "成功率"], rows, [18, 8, 8, 12, 10])

# 参数扰动
rows = [[p["tag"], round(p["success"], 2), "/".join(f"{a}-{b}-{c}" for a, b, c in p["alloc"])]
        for p in DATA["perturb"]]
sheet(wb, "情景_参数扰动", ["情景", "期望成功数", "分配(直发-升级-人工)"], rows, [16, 12, 46])

# 蒙特卡洛
rows = []
for k, lab in [("A", "全部直发"), ("B", "无人工最优"), ("C", "全局最优"), ("D", "强制满人工")]:
    m = DATA["mc"][k]
    rows.append([lab, round(m["mean"], 2), round(m["sd"], 2), m["p5"], m["p95"],
                 round(m["p_ge_170"], 4), round(m["p_ge_175"], 4)])
sheet(wb, "验证_蒙特卡洛", ["方案", "均值", "标准差", "5%分位", "95%分位", "P(≥170)", "P(≥175)"],
      rows, [14, 10, 10, 9, 9, 11, 11])
for r in range(2, 6):
    wb["验证_蒙特卡洛"].cell(row=r, column=6).number_format = "0.0%"
    wb["验证_蒙特卡洛"].cell(row=r, column=7).number_format = "0.0%"

out = os.path.join(ROOT, "output", "服务交付_结果数据.xlsx")
wb.save(out)
print("saved", out)
