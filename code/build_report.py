# -*- coding: utf-8 -*-
"""生成 Word 报告（IMMC 2027）。"""
import json
import os
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figures")
DATA = json.load(open(os.path.join(ROOT, "output", "results.json"), encoding="utf-8"))

BLACK = RGBColor(0, 0, 0)
DARK = RGBColor(31, 56, 100)
GRAY = RGBColor(90, 90, 90)
SONG, HEI, KAI, TIMES = "宋体", "黑体", "楷体", "Times New Roman"


# ------------------------------------------------------------------ 基础工具
def set_run(run, size=10.5, bold=False, italic=False, color=None, east=SONG, ascii_font=TIMES):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = ascii_font
    run.font.color.rgb = color if color is not None else BLACK
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:eastAsia"), east)
    rFonts.set(qn("w:ascii"), ascii_font)
    rFonts.set(qn("w:hAnsi"), ascii_font)


def add_rich(p, text, size=10.5, bold=False, east=SONG, color=None, ascii_font=TIMES):
    """把 _{...} / ^{...} 解析为下标 / 上标。"""
    pos = 0
    for m in re.finditer(r"(_\{[^}]*\}|\^\{[^}]*\})", text):
        if m.start() > pos:
            r = p.add_run(text[pos:m.start()])
            set_run(r, size, bold, color=color, east=east, ascii_font=ascii_font)
        tok = m.group(0)
        body = tok[2:-1]
        r = p.add_run(body)
        set_run(r, size, bold, color=color, east=east, ascii_font=ascii_font)
        if tok[0] == "_":
            r.font.subscript = True
        else:
            r.font.superscript = True
        pos = m.end()
    if pos < len(text):
        r = p.add_run(text[pos:])
        set_run(r, size, bold, color=color, east=east, ascii_font=ascii_font)


def para(text="", size=10.5, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True,
         before=0, after=4, line=1.5, east=SONG, color=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = align
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if indent:
        pf.first_line_indent = Pt(size * 2)
    if text:
        add_rich(p, text, size, bold, east=east, color=color)
    return p


def heading(text, level=1):
    sizes = {0: 20, 1: 15, 2: 12.5, 3: 11}
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(16 if level <= 1 else 10)
    pf.space_after = Pt(8 if level <= 1 else 5)
    pf.line_spacing = 1.2
    pf.keep_with_next = True
    r = p.add_run(text)
    set_run(r, sizes.get(level, 11), True, color=DARK if level <= 1 else BLACK, east=HEI)
    # 大纲级别，便于生成书签/导航
    pPr = p._p.get_or_add_pPr()
    outline = OxmlElement("w:outlineLvl")
    outline.set(qn("w:val"), str(max(0, level - 1)))
    pPr.append(outline)
    return p


def math(text, size=11):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.2
    pos = 0
    for m in re.finditer(r"(_\{[^}]*\}|\^\{[^}]*\})", text):
        if m.start() > pos:
            r = p.add_run(text[pos:m.start()])
            set_run(r, size, ascii_font="Cambria Math", east=SONG)
        tok = m.group(0)
        body = tok[2:-1]
        r = p.add_run(body)
        if tok[0] == "_":
            r.font.subscript = True
        else:
            r.font.superscript = True
        set_run(r, size, ascii_font="Cambria Math", east=SONG)
        pos = m.end()
    if pos < len(text):
        r = p.add_run(text[pos:])
        set_run(r, size, ascii_font="Cambria Math", east=SONG)
    return p


def caption(text, kind="table"):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2 if kind == "table" else 3)
    p.paragraph_format.space_after = Pt(4 if kind == "table" else 10)
    p.paragraph_format.line_spacing = 1.15
    if kind == "table":
        p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_run(r, 9, True, east=HEI)
    return p


def _borders(table, top=12, bottom=12, header=6):
    tblPr = table._tbl.tblPr
    for old in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for edge, sz in (("top", top), ("bottom", bottom)):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    for edge in ("left", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "auto")
        borders.append(el)
    tblPr.insert_element_before(borders, "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook")
    for cell in table.rows[0].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        for old in tcPr.findall(qn("w:tcBorders")):
            tcPr.remove(old)
        b = OxmlElement("w:tcBorders")
        bot = OxmlElement("w:bottom")
        bot.set(qn("w:val"), "single")
        bot.set(qn("w:sz"), str(header))
        bot.set(qn("w:space"), "0")
        bot.set(qn("w:color"), "000000")
        b.append(bot)
        tcPr.insert_element_before(b, "w:shd", "w:noWrap", "w:tcMar", "w:textDirection",
                                   "w:tcFitText", "w:vAlign", "w:hideMark")


def table(headers, rows, widths=None, font=9, align_first_left=True):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(h)
        set_run(r, font, True, east=HEI)
        hdr[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if (i == 0 and align_first_left) else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.05
            add_rich(p, str(v), font)
            cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
        grid = t._tbl.tblGrid
        for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(int(Cm(w).twips)))
        tblW = t._tbl.tblPr.find(qn("w:tblW"))
        if tblW is not None:
            tblW.set(qn("w:type"), "dxa")
            tblW.set(qn("w:w"), str(int(sum(widths) * 566.93)))
    _borders(t)
    rows_all = t.rows
    for idx, row in enumerate(rows_all):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        if idx == 0:
            trPr.append(OxmlElement("w:tblHeader"))
        if idx < len(rows_all) - 1:
            for cell in row.cells:
                for pp in cell.paragraphs:
                    pp.paragraph_format.keep_with_next = True
    return t


def figure(name, cap, width=12.8):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_with_next = True
    shape = p.add_run().add_picture(os.path.join(FIG, name), width=Cm(width))
    try:
        spPr = shape._inline.graphic.graphicData.pic.spPr
        ln = OxmlElement("a:ln")
        ln.set("w", "19050")
        fill = OxmlElement("a:solidFill")
        clr = OxmlElement("a:srgbClr")
        clr.set("val", "FFFFFF")
        fill.append(clr)
        ln.append(fill)
        spPr.append(ln)
    except Exception:
        pass
    caption(cap, "figure")


def bullet(text, size=10.5):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Pt(21)
    pf.first_line_indent = Pt(0)
    pf.space_before = Pt(0)
    pf.space_after = Pt(3)
    pf.line_spacing = 1.45
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run("· ")
    set_run(r, size)
    add_rich(p, text, size)
    return p


# ------------------------------------------------------------------ 文档骨架
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.4)
sec.top_margin = Cm(2.5)
sec.bottom_margin = Cm(2.3)

normal = doc.styles["Normal"]
normal.font.name = TIMES
normal.font.size = Pt(10.5)
normal.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), SONG)

# 页眉页脚
hp = sec.header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
hr = hp.add_run("IMMC 2027  ·  智能时代的服务交付：人机协作与有限资源配置")
set_run(hr, 8, color=GRAY, east=SONG)

fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r1 = fp.add_run("— ")
set_run(r1, 9, color=GRAY)
run = fp.add_run()
set_run(run, 9, color=GRAY)
fld1 = OxmlElement("w:fldChar"); fld1.set(qn("w:fldCharType"), "begin")
instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = " PAGE "
fld2 = OxmlElement("w:fldChar"); fld2.set(qn("w:fldCharType"), "end")
run._r.append(fld1); run._r.append(instr); run._r.append(fld2)
r2 = fp.add_run(" —")
set_run(r2, 9, color=GRAY)

# ------------------------------------------------------------------ 封面
for _ in range(3):
    para("", indent=False, after=0)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("IMMC 2027  国际数学建模挑战赛")
set_run(r, 13, True, color=DARK, east=HEI)

para("", indent=False, after=0)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(30)
r = p.add_run("智能时代的服务交付")
set_run(r, 30, True, east=HEI)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("人机协作与有限资源配置")
set_run(r, 30, True, east=HEI)

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(18)
r = p.add_run("—— 三路径整数规划、边际分析与情景验证")
set_run(r, 15, False, east=KAI)

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(60)
r = p.add_run("本文完整求解任务 1、任务 2，并完成任务 3")
set_run(r, 11, color=GRAY, east=SONG)

for _ in range(6):
    para("", indent=False, after=0)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("2026 年 11 月")
set_run(r, 12, east=SONG)

# 封面底部横线
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(6)
pPr = p._p.get_or_add_pPr()
pbdr = OxmlElement("w:pBdr")
bottom = OxmlElement("w:bottom")
bottom.set(qn("w:val"), "single"); bottom.set(qn("w:sz"), "8")
bottom.set(qn("w:space"), "1"); bottom.set(qn("w:color"), "1F3864")
pbdr.append(bottom); pPr.append(pbdr)

doc.add_page_break()

# ------------------------------------------------------------------ 摘要
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(0)
r = p.add_run("摘    要")
set_run(r, 18, True, east=HEI)
para("", indent=False, after=2)

abs_texts = [
    "本文研究智能时代服务交付中“AI 快速处理—AI 升级处理—人工复核”三条路径的有限资源配置问题。"
    "每日共有 200 条请求，分为单项信息查询、多条件判断、跨资料综合、例外情况处理四类；"
    "三条路径的单次成本分别为 1、5、13 个成本单位，每日总预算不超过 600，人工复核不超过 20 条。"
    "目标是在预算与人工双重约束下最大化期望成功回答数。",

    "针对任务 1，全部直接发布的基准为 155.0 条成功回答（整体成功率 77.5%），总成本仅 200,"
    "存在 400 单位可用额外预算。边际分析表明：跨资料综合升级的边际性价比最高（7.50%/单位成本），"
    "例外情况处理转人工次之（5.00%/单位）；人工相对于升级的增量在例外情况上达到 5.625%/单位，"
    "而在其余三类上均低于 0.9%/单位，说明人工名额应优先投向例外情况。",

    "针对任务 2，建立以期望成功数为目标的整数线性规划，并给出“人工向量完全枚举 + 升级贪心”的精确算法："
    "枚举 9 911 个人工分配向量，每个向量下按升级增益降序贪心填充，可覆盖全部可行解。"
    "最优方案为：单项信息查询 80 条全部直接发布，多条件判断 40 条直接发布、20 条升级，"
    "跨资料综合 50 条全部升级，例外情况处理 10 条全部人工复核；总成本恰为 600,"
    "人工使用 10 条，期望成功回答数 178.0 条（整体成功率 89.0%），较基准提高 23.0 条，"
    "较“无人工最优”提高 2.5 条。该解经 40 组随机小算例与暴力枚举交叉验证，全部一致。",

    "针对任务 3，从预算、人工容量、需求冲击、参数扰动四个方面开展情景分析与验证。"
    "预算曲线呈五段边际递减，边际收益由 7.5%/单位依次降至 5.0%、2.5%、0.875%、0.5%/单位；"
    "成功率要达到 90% 需预算 680。人工名额在预算 600 时的边际价值为 0.25 条/个（仅前 10 个有效），"
    "预算达到 840 后才成为紧约束。例外情况请求由 10 条增至 40 条时，总成功数升至 188.9 条，"
    "但整体成功率由 89.0% 降至 82.1%。当升级成功率整体下调 5 个百分点时，最优解会自动把部分"
    "跨资料综合请求转交人工，总成功数降至 174.7 条；方案对人工成功率的小幅变化则不敏感。"
    "4 万次蒙特卡洛模拟显示，最优方案的期望值为 178.00 条（与解析值一致），"
    "5%–95% 分位为 171–185 条，P(≥175)=79.3%，显著优于其他方案。",
]
for t in abs_texts:
    para(t, after=4)

p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(10)
p.paragraph_format.line_spacing = 1.4
r = p.add_run("关键词：")
set_run(r, 10.5, True, east=HEI)
r = p.add_run("人机协作；整数线性规划；边际分析；敏感性分析；蒙特卡洛模拟")
set_run(r, 10.5)

doc.add_page_break()

# ------------------------------------------------------------------ 1 问题重述
heading("1  问题重述", 1)
heading("1.1  背景", 2)
para("随着人工智能与自动化技术快速普及，AI 已逐步参与服务交付。但人力、算力、时间等资源始终存在上限："
     "完全依赖人工，单位成本高、简单任务会挤占宝贵的人力；完全依赖 AI，则边界案例缺乏兜底，"
     "错误无法被修正。因此，人机协作的核心不只是“AI 与人一起工作”，而是“有限资源如何在两条能力曲线之间分配”。"
     "在给定的服务交付场景中，经费可直接对应 AI 算力额度与人工审核工时，总预算固定为 600 个成本单位。")

heading("1.2  基础算例与数据", 2)
para("每日共有 N = 200 条服务请求，按难度分为四类。每条请求必须且只能选择三条处理路径之一：直接发布（成本 1）、"
     "升级处理（成本 5，由更强的智能体完成）、人工复核（成本 13）。各类请求在不同路径下的成功率如表 1 所示，"
     "预算上限 B = 600，人工复核上限 H = 20 条/日。")
caption("表 1  基础算例参数")
rows = []
for i, m in enumerate(DATA["task1"]["marginal"]):
    rows.append([m["name"], m["n"], "1 / 5 / 13", f"{m['p1']:.0%}", f"{m['p2']:.0%}", f"{m['p3']:.0%}"])
table(["请求类型", "每日数量", "路径成本", "直接发布成功率", "升级处理成功率", "人工复核成功率"],
      rows, widths=[3.2, 1.9, 2.4, 2.8, 2.9, 2.9])
para("注：路径成本依次为直接发布、升级处理、人工复核的单次成本。", size=9, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER,
     after=8, color=GRAY)

heading("1.3  需要解决的问题", 2)
para("任务 1（基础比较）：计算全部直接发布时的总成本与期望成功回答数；比较升级处理与人工复核相对直接发布的"
     "边际收益，给出“什么样的请求更值得升级、更值得人工”的判据。")
para("任务 2（优化分配）：建立人机资源分配的数学规划模型，求出预算 600、人工 20 条件下的最优分配方案，"
     "并与全部直接发布、无人工参与等方案对比，回答“是否应把 20 个人工名额全部用尽”。")
para("任务 3（情景与验证）：设计预算紧缩/放宽、人工容量变化、高难度咨询潮、成功率参数扰动等情景，"
     "检验最优方案的稳定性与适用边界，并用随机模拟验证模型结论。")

# ------------------------------------------------------------------ 2 假设与符号
heading("2  模型假设与符号", 1)
heading("2.1  模型假设", 2)
assumptions = [
    ("H1  独立性", "各请求的处理结果相互独立，同一路径对同类请求的成功概率相同，不因当日处理总量而变化。"),
    ("H2  成功率外生", "三类路径的成功率由历史数据给出，视为已知常数；不考虑人工复核反馈带来的学习效应。"),
    ("H3  成本线性", "总成本为各路径处理条数的线性加总，不存在规模折扣或固定启动成本。"),
    ("H4  人工同质", "人工复核能力同质，单条请求占用 1 个“人工名额”，对应 13 个成本单位。"),
    ("H5  单期决策", "以单日为一个决策周期，预算与人工名额当日结算，不可跨日结转。"),
    ("H6  风险中性", "决策目标是最大化期望成功回答数，不额外考虑成功数的方差或最坏情形（第 6 节将单独检验）。"),
]
for k, v in assumptions:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(21)
    p.paragraph_format.first_line_indent = Pt(-0)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.45
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(k + "：")
    set_run(r, 10.5, True, east=HEI)
    r = p.add_run(v)
    set_run(r, 10.5)

heading("2.2  符号说明", 2)
caption("表 2  主要符号")
sym = [
    ["i", "请求类型，i = 1,2,3,4", "j", "处理路径，j = 1,2,3（直发/升级/人工）"],
    ["n_{i}", "第 i 类请求的每日数量", "x_{ij}", "第 i 类请求分配到路径 j 的条数"],
    ["p_{ij}", "第 i 类请求走路径 j 的成功率", "c_{j}", "路径 j 的单次成本，c = (1,5,13)"],
    ["B", "每日总预算上限（600）", "H", "每日人工复核上限（20）"],
    ["N", "每日请求总数（200）", "Z", "期望成功回答数"],
]
table(["符号", "含义", "符号", "含义"], sym, widths=[1.6, 5.6, 1.8, 6.2], font=9)
para("", indent=False, after=4)

# ------------------------------------------------------------------ 3 模型
heading("3  人机资源分配的整数规划模型", 1)
para("令 x_{ij} 表示第 i 类请求中分配到路径 j 的条数（i = 1,2,3,4；j = 1,2,3）。以期望成功回答数最大为目标，"
     "可建立如下整数线性规划：")
math("max  Z = Σ_{i=1}^{4} Σ_{j=1}^{3} p_{ij} x_{ij}")
math("s.t.  Σ_{j=1}^{3} x_{ij} = n_{i} ,   i = 1,2,3,4")
math("      Σ_{i=1}^{4} (c_{1} x_{i1} + c_{2} x_{i2} + c_3 x_{i3}) ≤ B")
math("      Σ_{i=1}^{4} x_{i3} ≤ H")
math("      x_{ij} ∈ Z_{≥0}")
para("其中目标函数是四类请求、三条路径的期望成功数之和；第一组约束为数量守恒，保证每条请求恰好被处理一次；"
     "第二组为预算约束；第三组为人工容量约束；最后一组为整数约束。")
para("模型具有两个值得注意的结构特征。第一，所有请求至少要走直接发布，因此基础成本 fixed = Σn_{i} = 200 是不可避免的，"
     "真正可自由分配的是额外预算 E = B − 200 = 400。第二，把 x_{i1} 视作基准后，升级处理的单位增量为"
     " Δc = c_{2} − c_{1} = 4、增益为 g_{i} = p_{i2} − p_{i1}；人工复核相对直接发布的增量为 Δc = 12、增益为"
     " h_{i} = p_{i3} − p_{i1}。这一“基准 + 增量”的写法使模型等价于一个带优先级的二维背包问题，也是后文精确算法的基础。")

# ------------------------------------------------------------------ 4 任务1
heading("4  任务 1：基础比较与边际性价比", 1)
heading("4.1  全部直接发布的结果", 2)
para("若 200 条请求全部直接发布，总成本为 200 × 1 = 200，远低于预算上限 600，可剩余 400 单位额外预算。"
     "期望成功回答数为")
math("Z_A = 80×0.95 + 60×0.80 + 50×0.55 + 10×0.35 = 76 + 48 + 27.5 + 3.5 = 155.0（条）")
para("整体成功率为 155/200 = 77.5%，平均每条成功回答的成本为 200/155 ≈ 1.29 个成本单位。"
     "这一基准说明：预算并不是瓶颈，真正的瓶颈是“钱花在哪里”——若不升级、不用人工，400 单位预算被完全闲置。")

heading("4.2  升级与人工复核的边际收益", 2)
para("判断一条请求是否值得升级或转人工，应看单位额外成本带来的成功率增量，即边际性价比 Δp/Δc。"
     "对每类请求分别计算三种比较（升级对直发、人工对直发、人工对升级），结果见表 3。")
caption("表 3  各请求类型的边际收益与边际性价比")
rows = []
for m in DATA["task1"]["marginal"]:
    rows.append([m["name"],
                 f"+{m['d_up']*100:.0f}%", f"{m['r_up']*100:.2f}",
                 f"+{m['d_man']*100:.0f}%", f"{m['r_man']*100:.2f}",
                 f"+{m['d_man_up']*100:.0f}%", f"{m['r_man_up']*100:.2f}"])
table(["请求类型", "升级 Δp", "升级性价比\n(%/单位)", "人工 Δp\n(对直发)", "人工性价比\n(%/单位)",
       "人工 Δp\n(对升级)", "人工升级\n边际性价比"], rows,
      widths=[3.0, 1.9, 2.4, 2.1, 2.4, 2.1, 2.3], font=8.5)
para("注：升级的额外成本为 4，人工相对直发的额外成本为 12，人工相对升级的额外成本为 8。", size=9, indent=False,
     align=WD_ALIGN_PARAGRAPH.CENTER, after=8, color=GRAY)
para("表 3 给出三条清晰的排序。其一，升级路径中，跨资料综合的性价比高达 7.50%/单位，多条件判断为 2.50%/单位，"
     "例外情况为 3.75%/单位，单项查询仅 0.50%/单位。其二，人工相对直发的性价比以例外情况最高（5.00%/单位），"
     "跨资料综合次之（3.08%/单位）。其三，若已经升级、再决定是否转人工，则只有例外情况值得"
     "（+45 个百分点，5.625%/单位），其余三类均低于 0.9%/单位，其中跨资料综合仅为 0.875%/单位。")

heading("4.3  资源该给谁的判据", 2)
para("综合上述结果，可归纳出三条判据。")
para("（1）预算充裕度决定阈值。基准成本 200 之上还有 400 单位额外预算，而把 200 条全部升级需额外 800"
     "（总成本 1 000）、全部转人工需额外 2 400（总成本 2 600），因此预算相对于“全升级”是紧缺的、"
     "相对于“全人工”是极度紧缺的。"
     "在预算受限时，应按“每增加 1 单位成本能提升多少成功率”从高到低依次分配，直到预算用尽。")
para("（2）人工名额应当留给“升级也救不回来”的请求。人工相对升级的增量收益在例外情况上为 45 个百分点，"
     "是跨资料综合（7 个百分点）的 6 倍以上；而人工名额只有 20 个，因此人工应优先覆盖例外情况。")
para("（3）双约束下存在“先升级、后人工”的优先级。升级的额外成本只有 4，是人工的 1/3；"
     "先升级可以把有限的预算铺到更多请求上，再用人工对少数“硬骨头”做兜底，这构成了任务 2 最优解的直观逻辑。")

# ------------------------------------------------------------------ 5 任务2
heading("5  任务 2：最优分配模型与求解", 1)
heading("5.1  精确求解算法", 2)
para("模型只有 4 类请求、3 条路径，但整数变量有 12 个，直接枚举的计算量约为 ∏(n_{i}+2)(n_{i}+1)/2 ≈ 10^{7}，"
     "可以接受但不经济。利用模型结构可把问题降维：")
bullet("第一步，枚举人工分配向量 b = (b_1,b_2,b_3,b_{4})，满足 Σb_{i} ≤ H 且 12Σb_{i} ≤ E。"
       "在 B = 600、H = 20 时共有 9 911 个可行向量（Σb_{i} ≤ 20，且 b_{4} ≤ 10）。")
bullet("第二步，固定 b 后，剩余预算只能用于升级；每条升级的成本恒为 4、增益为常数 g_{i}，"
       "因此按 g_{i} 从大到小贪心填充即为该子问题的最优解（等权背包的贪心最优性）。")
bullet("第三步，对所有 b 取目标值最大者。由于第一步覆盖了全部可行的人工分配，第二步在每种分配下精确最优，"
       "所得即为全局整数最优解。")
para("为验证算法正确性，另编写了完全暴力枚举程序，在 40 组随机小算例（每类 1–3 条、随机成功率）上对比，"
     "40 组结果全部一致，说明求解器没有遗漏更优解。")

heading("5.2  最优分配方案", 2)
para("把上述算法用于基础算例，得到最优解如表 4。额外预算 400 的去向为：跨资料综合 50 条全部升级，"
     "耗用 50×4 = 200；例外情况 10 条全部人工，耗用 10×12 = 120；剩余 80 用于多条件判断升级 20 条。"
     "单项信息查询的升级性价比过低（0.50%/单位），不分配任何额外资源。")
caption("表 4  最优分配方案（B = 600，H = 20）")
opt = DATA["task2"]["opt"]
rows = []
for i, (d, a, b) in enumerate(opt["alloc"]):
    m = DATA["task1"]["marginal"][i]
    succ = d * m["p1"] + a * m["p2"] + b * m["p3"]
    rows.append([m["name"], m["n"], d, a, b, f"{succ:.1f}"])
rows.append(["合计", 200, 120, 70, 10, "178.0"])
table(["请求类型", "总数", "直接发布", "升级处理", "人工复核", "期望成功数"], rows,
      widths=[3.6, 1.8, 2.4, 2.4, 2.4, 2.8])
para("该方案总成本为 200 + 4×70 + 12×10 = 600，恰好用尽预算；人工使用 10 条，仅占上限的一半；"
     "期望成功回答数为 178.0 条，整体成功率 89.0%，平均每条成功回答的成本为 600/178 ≈ 3.37 个成本单位。"
     "与全部直接发布相比，多投入 400 单位成本换回 23.0 条成功回答，平均每 17.4 单位成本换 1 条。")

heading("5.3  方案横向对比", 2)
para("为说明“优化”与“堆资源”的差别，表 5 对比了五种方案：A 全直发；B 无人工参与下的最优；"
     "C 本文全局最优；D 强制用满 20 个人工名额；以及“全部升级”的参考方案。")
caption("表 5  五种方案的对比")
plans = DATA["task2"]["plans"]
rows = [
    ["A 全部直接发布", "全部走快速智能体", 0, 200, "155.0", "77.5%", "—"],
    ["B 无人工最优", "跨资料 50 升级、例外 10 升级、多条件 40 升级", 0, 600, "175.5", "87.8%", "+20.5"],
    ["C 全局最优", "跨资料 50 升级、例外 10 人工、多条件 20 升级", 10, 600, "178.0", "89.0%", "+23.0"],
    ["D 强制满人工", "例外 10 人工、跨资料 10 转人工、40 升级", 20, 600, "176.7", "88.4%", "+21.7"],
    ["全升级（参考）", "200 条全部升级，不使用人工", 0, 1000, "179.1", "89.6%", "+24.1"],
]
table(["方案", "分配特征", "人工", "总成本", "期望成功数", "成功率", "较 A 提升"], rows,
      widths=[2.8, 5.3, 1.2, 1.5, 1.9, 1.5, 1.9], font=8.5)
figure("fig4_plans.png", "图 1  五种方案的期望成功数与总成本对比")

para("对比可见：B 方案把 600 预算全部投给升级（跨资料 50 条、例外 10 条、多条件 40 条），得到 175.5 条；"
     "C 方案把 10 条例外从升级改为人工，并把省出的预算重新配置给多条件，反而提高到 178.0 条。"
     "D 方案虽然用满 20 个人工名额，却因把 10 条跨资料综合从升级改为人工（每条多花 8、仅多 7 个百分点），"
     "挤占了原本可用于多条件升级的预算，结果降到 176.7 条，反而低于 C。"
     "“全升级”方案需要 1 000 预算，才达到 179.1 条，其边际成本远高于 C。")

heading("5.4  两个关键结论", 2)
para("第一，最值得交给人工的是例外情况处理。该类请求升级后成功率也仅 50%，而人工可达 95%，"
     "人工相对升级的增量为 45 个百分点，是其余三类的 6–45 倍；在本算例中把 10 条例外全部转人工，"
     "仅多花 120 单位预算，就换来 4.5 条成功回答。")
para("第二，不应当用尽全部 20 个人工名额。预算 600 时，第 1–10 个人工名额每个价值 0.25 条，"
     "第 11–20 个名额的边际价值为 0：它们只能替换已经升级的跨资料或多条件请求，每条最多提升 0.05–0.07 条，"
     "却要挤占 8 单位预算，反而拉低总成功数。更严格地说，人工上限 H = 20 在 B = 600 时并不是紧约束；"
     "只有预算超过 840 后，20 个名额才会被全部使用（见 6.2 节）。")

# ------------------------------------------------------------------ 6 任务3
heading("6  任务 3：情景变化与验证", 1)
para("任务 2 的最优解建立在“预算 600、人工 20、成功率不变”的假设上。现实中这些条件都会变化。"
     "本节从预算、人工容量、需求结构、成功率参数四个维度做敏感性分析，并用蒙特卡洛模拟验证结论的可靠性。")

heading("6.1  预算敏感性：五段边际递减", 2)
para("令预算 B 在 200–1 100 之间变化，其余参数不变，重新求解得到图 2 的预算—成功数曲线。"
     "曲线呈明显的分段线性，共五个阶段，每阶段的斜率就是该阶段“每 1 单位预算换来的成功数”。")
figure("fig1_budget.png", "图 2  预算—期望成功数曲线（H = 20）")
caption("表 6  预算敏感性的关键节点")
rows = [
    ["200–400", "跨资料综合全部升级", "7.50", "400", "170.0"],
    ["400–520", "例外情况升级并逐步转人工", "5.00", "520", "176.0"],
    ["520–760", "多条件判断逐步升级", "2.50", "760", "182.0"],
    ["760–840", "跨资料综合逐步转人工", "0.875", "840", "182.7"],
    ["840–1 160", "单项信息查询逐步升级", "0.50", "1 160", "184.3"],
]
table(["预算区间", "资金去向", "边际收益\n(%/单位)", "区间末预算", "区间末成功数"], rows,
      widths=[2.4, 6.0, 2.7, 2.5, 2.6], font=9)
para("曲线给出三点管理含义。其一，预算从 600 削减到 500（−16.7%），成功数只从 178.0 降到 175.0（−1.7%），"
     "因为被削减的正是性价比最低的多条件升级；但若继续削减到 450，例外情况的人工就要被迫减少，"
     "成功数降至 172.4。其二，预算从 600 增加到 680（+13.3%）即可把整体成功率推到 90%，"
     "这是“性价比最高的一段追加投入”。其三，预算超过 840 后边际收益只剩 0.50%/单位，"
     "继续加预算已不经济，应转向扩充人工或提升成功率。")

heading("6.2  人工容量敏感性", 2)
para("图 3 给出预算 600 与 900 两种情形下，人工上限 H 从 0 增加到 30 时的最优成功数。")
figure("fig2_human.png", "图 3  人工容量—期望成功数曲线")
para("预算 600 时，H 从 0 增至 10，成功数由 175.5 线性升至 178.0，每个名额价值 0.25 条；H 超过 10 后曲线完全水平，"
     "说明第 11–20 个名额在预算 600 下没有价值。预算 900 时，前 10 个名额每个价值 0.41 条（把例外从升级改为人工，"
     "节省的预算可转投单项升级），第 11–20 个名额每个价值约 0.03 条，H ≈ 28 后饱和。"
     "因此“人工上限是否值钱”取决于预算水平：低预算时人工名额是“够用即可”，高预算时人工才是瓶颈。"
     "这也解释了为什么在 B = 600 时不应强求用满 20 个名额，而在 B ≥ 840 时应尽量用满。")

heading("6.3  需求冲击：高难度咨询潮", 2)
para("假设例外情况处理请求由 10 条增至 40 条（总请求数由 200 增至 230，预算仍为 600），重新求解，结果见图 4。")
figure("fig3_surge.png", "图 4  高难度咨询潮下的成功数与成功率")
para("随着 n_{4} 增加，总成功数由 178.0 升至 188.9（因为总请求数增加），但整体成功率由 89.0% 降至 82.1%。"
     "原因在于预算固定：新增加的例外请求只能靠“压缩其他类型的升级”来腾挪预算。具体而言，"
     "多条件判断的升级条数由 20 条逐步降到 0（n_{4} = 16 时）；跨资料综合始终全部升级；"
     "而新增的例外请求只能部分转人工（n_{4} = 40 时 14 条人工、26 条直发）。"
     "若总请求数不变、仅把 20 条单项查询替换为例外情况（结构冲击），成功数由 178.0 降至 167.9（−10.1 条），"
     "整体成功率降至 84.0%。")
para("这提示：高难度占比上升时，“按固定比例分配资源”会迅速失效。更稳健的做法是为例外类请求设置"
     "“预算保护线”或预留应急人工工时；若高难度潮可能持续，应优先扩充人工容量而非继续加预算。")

heading("6.4  成功率参数扰动", 2)
para("现实中成功率估计存在误差。令所有升级成功率统一下调/上调 5 个百分点，或所有人工成功率统一下调/上调 5 个百分点，"
     "重新求解，结果见表 7。")
caption("表 7  成功率参数扰动下的最优解")
rows = []
for p in DATA["perturb"]:
    alloc = p["alloc"]
    a = alloc[2][1] + alloc[2][2]
    rows.append([p["tag"], f"{p['success']:.2f}", f"{alloc[1][1]}", f"{a}",
                 f"{alloc[3][2]}"])
table(["情景", "最优成功数", "多条件升级", "跨资料升级+人工", "例外人工"], rows,
      widths=[4.0, 3.2, 2.8, 3.4, 2.8], font=9)
para("结果显示：方案对人工成功率的小幅变化不敏感（人工只覆盖例外情况，即使人工成功率下降 5 个百分点，"
     "仍显著高于升级的 50%），对升级成功率更敏感。当升级成功率整体下调 5 个百分点时，"
     "最优解发生结构性调整——跨资料综合由 50 条全升级改为 40 条升级 + 10 条人工，"
     "同时放弃全部多条件升级；这说明“升级—人工”的相对性价比一旦变化，资源应重新向人工倾斜。"
     "在“双升 5 个百分点”情景下成功数可达 182.0，在“双降”情景下降到 174.0，波动约 ±4 条，"
     "但“例外必须人工、跨资料优先升级、单项基本不升级”的排序始终不变。")

heading("6.5  蒙特卡洛模拟验证", 2)
para("前述结果均为期望值。为检验实际单日表现的波动，对四种方案各做 40 000 次模拟：按各路径的条数与成功率"
     "抽取二项分布随机数并加总，统计均值、标准差与分位数，结果见图 5 与表 8。")
figure("fig5_mc.png", "图 5  四种方案的蒙特卡洛分布")
caption("表 8  蒙特卡洛模拟结果（40 000 次）")
rows = []
for k, lab in [("A", "A 全部直发"), ("B", "B 无人工最优"), ("C", "C 全局最优"), ("D", "D 强制满人工")]:
    m = DATA["mc"][k]
    rows.append([lab, f"{m['mean']:.2f}", f"{m['sd']:.2f}", f"{m['p5']:.0f}–{m['p95']:.0f}",
                 f"{m['p_ge_170']:.1%}", f"{m['p_ge_175']:.1%}"])
table(["方案", "均值", "标准差", "5%–95% 分位", "P(≥170)", "P(≥175)"], rows,
      widths=[3.6, 2.0, 2.0, 3.2, 2.5, 2.5], font=9)
para("模拟得到的均值与解析期望完全一致（178.00 对 178.0），说明模型没有系统性偏差。C 方案的标准差为 4.33，"
     "低于 A 方案的 5.29，说明“把资源集中到高成功率路径”不仅提高均值，也降低了波动；"
     "C 有 79.3% 的概率达到 175 条以上，而 B 只有 59.8%，A 几乎不可能达到 170 条（0.2%）。"
     "D 的均值（176.7）与分位均低于 C，再次说明“用满人工”不是好策略。")

heading("6.6  稳健性结论与管理建议", 2)
para("把四类情景放在一起，可以得到以下稳健结论与建议。")
bullet("人工优先给例外情况，且只需 10 条/日。无论在哪种情景下，例外情况都是“升级救不回来、人工显著更好”的类型；"
       "在预算 600 下多配人工反而挤占升级预算。")
bullet("预算 600 时，跨资料综合全部升级、多条件判断升级约 1/3、单项查询不升级。这一结构与边际性价比排序一致，"
       "在 ±5 个百分点的参数扰动下保持稳定。")
bullet("把 90% 成功率作为目标时，预算门槛为 680；95% 已接近本算例的理论上限（全人工 190.9 条），需要约 2 600 预算，性价比明显下降。")
bullet("预算低于 520 时，应优先保住跨资料综合的升级；预算高于 760 后，可逐步把跨资料综合转人工；"
       "预算高于 840 后，人工才应用满 20 条。")
bullet("面对高难度咨询潮，固定比例的资源分配会失效，应设置例外类预算保护线、预留人工机动工时，"
       "或按“当前难度结构”滚动重算配额。")

# ------------------------------------------------------------------ 7 评价
heading("7  模型评价与推广", 1)
heading("7.1  优点", 2)
para("（1）精确性：利用“人工向量枚举 + 升级贪心”的结构把 12 维整数规划降为 9 911 次枚举，"
     "既保证全局最优，又可在毫秒级完成，便于滚动重算。（2）可解释性：边际性价比、影子价格式的分段斜率"
     "直接对应“钱该花在哪”，便于管理者理解和执行。（3）可验证性：与暴力枚举、蒙特卡洛两套独立方法交叉验证，"
     "结论稳健。")
heading("7.2  局限", 2)
para("（1）假设各请求独立、成功率外生，未考虑人工复核反馈带来的学习效应与成功率漂移；"
     "（2）目标是风险中性的期望值，未内嵌服务等级协议（SLA）或最坏情形约束；"
     "（3）单期静态模型，未考虑积压、时延与跨日结转；（4）人工同质假设忽略了不同审核员的技能差异。")
heading("7.3  推广", 2)
para("模型可直接推广到三条以上路径、多类请求、多人技能等级的配置问题；若引入需求不确定性，"
     "可写成两阶段随机规划或鲁棒优化；若考虑学习效应，可把 p_{ij} 设为历史人工复核量的递增函数，"
     "形成“投入—学习—成功率提升”的动态闭环。这些方向都保留了本文“基准 + 增量、按边际性价比排序”的核心思想。")

# ------------------------------------------------------------------ 参考文献
heading("参考文献", 1)
refs = [
    "[1] 姜启源, 谢金星, 叶俊. 数学模型（第五版）[M]. 北京: 高等教育出版社, 2018.",
    "[2] 《运筹学》教材编写组. 运筹学（第四版）[M]. 北京: 清华大学出版社, 2012.",
    "[3] Hillier F S, Lieberman G J. Introduction to Operations Research (10th ed.)[M]. McGraw-Hill, 2015.",
]
for ref in refs:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.3
    r = p.add_run(ref)
    set_run(r, 9.5)

# ------------------------------------------------------------------ 附录
heading("附录 A  核心求解代码", 1)
para("以下为精确求解器的主体代码（Python）。完整工程见随附文件 code/model.py、code/analysis.py、code/figures.py。", after=6)
code = """def solve(B=600, H=20):
    n = [80, 60, 50, 10]; c = [1, 5, 13]
    p = [[.95,.97,.98],[.80,.90,.95],[.55,.85,.92],[.35,.50,.95]]
    base = sum(n[i]*p[i][0] for i in range(4))
    E = B - sum(n)                      # 额外预算
    g = [p[i][1]-p[i][0] for i in range(4)]   # 升级增益
    h = [p[i][2]-p[i][0] for i in range(4)]   # 人工增益
    order = sorted(range(4), key=lambda i: -g[i])
    best = None
    for b in product(*[range(min(n[i], H)+1) for i in range(4)]):
        if sum(b) > H or 12*sum(b) > E:
            continue
        gain = sum(h[i]*b[i] for i in range(4))
        rem = E - 12*sum(b)
        a = [0]*4
        for i in order:                 # 等权背包：贪心即最优
            a[i] = min(n[i]-b[i], rem//4)
            gain += g[i]*a[i]; rem -= 4*a[i]
        if best is None or gain > best[0]:
            best = (gain, a, b)
    gain, a, b = best
    return base + gain, a, b
"""
for line in code.split("\n"):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(0); pf.space_after = Pt(0)
    pf.line_spacing = 1.05
    pf.left_indent = Pt(6)
    r = p.add_run(line if line else " ")
    set_run(r, 8.6, ascii_font="Consolas", east=SONG)
para("", indent=False, after=6)
para("复现方式：在工作目录依次运行 code/model.py（含 40 组暴力枚举校验）、code/analysis.py（生成全部情景数据）、"
     "code/figures.py（生成 5 张插图）、code/build_xlsx.py 与 code/build_report.py（生成本文与数据附件）。"
     "全部结果数据见 output/服务交付_结果数据.xlsx。", size=9.5, after=4)

out = os.path.join(ROOT, "output", "智能时代的服务交付_建模报告.docx")
doc.save(out)
print("saved", out)
