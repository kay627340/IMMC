# -*- coding: utf-8 -*-
"""情景分析与蒙特卡洛验证：生成报告所需的全部数据（JSON）。"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import N, C, P, NAMES, N_TOTAL, B0, H0, solve, metrics, table_rows

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)

rng = np.random.default_rng(2027)
DATA = {}


def compact(res):
    return {
        "B": res["B"], "H": res["H"], "alloc": res["alloc"], "cost": res["cost"],
        "human": res["human"], "success": res["success"], "rate": res["rate"],
        "cost_per_success": res["cost_per_success"],
    }


# ---------------------------------------------------------------- 任务1：基准与边际
base = {"success": 155.0, "cost": 200.0, "rate": 155 / 200}
marg = []
for i in range(4):
    marg.append({
        "name": NAMES[i], "n": N[i],
        "p1": P[i][0], "p2": P[i][1], "p3": P[i][2],
        "d_up": P[i][1] - P[i][0], "r_up": (P[i][1] - P[i][0]) / 4,
        "d_man": P[i][2] - P[i][0], "r_man": (P[i][2] - P[i][0]) / 12,
        "d_man_up": P[i][2] - P[i][1], "r_man_up": (P[i][2] - P[i][1]) / 8,
    })
DATA["task1"] = {"base": base, "marginal": marg}

# ---------------------------------------------------------------- 任务2：最优
opt = solve(B=B0, H=H0)
planA = {"alloc": [(80, 0, 0), (60, 0, 0), (50, 0, 0), (10, 0, 0)]}
planB = solve(B=B0, H=0)
planD = {"alloc": [(80, 0, 0), (60, 0, 0), (0, 40, 10), (0, 0, 10)]}   # 强制用满 20 个人工名额


def plan_info(alloc):
    cost, human, succ = metrics({"n": N, "c": C, "p": P}, alloc)
    return {"alloc": alloc, "cost": cost, "human": human, "success": succ, "rate": succ / N_TOTAL,
            "cost_per_success": cost / succ}


planAllUp = {"alloc": [(0, 80, 0), (0, 60, 0), (0, 50, 0), (0, 10, 0)]}
planAllMan = {"alloc": [(0, 0, 80), (0, 0, 60), (0, 0, 50), (0, 0, 10)]}
plans = {"A": plan_info(planA["alloc"]), "B": plan_info(planB["alloc"]),
         "C": plan_info(opt["alloc"]), "D": plan_info(planD["alloc"]),
         "ALLUP": plan_info(planAllUp["alloc"]), "ALLMAN": plan_info(planAllMan["alloc"])}
DATA["task2"] = {"opt": compact(opt), "plans": plans}

# ---------------------------------------------------------------- 任务3.1 预算敏感性
budget_curve = []
for B in range(200, 1101, 10):
    r = solve(B=B, H=H0)
    budget_curve.append({"B": B, "success": r["success"], "cost": r["cost"], "human": r["human"],
                         "alloc": r["alloc"]})
DATA["budget_curve"] = budget_curve

# 边际价值（每 4 元预算的收益增量）
mv = {}
for B in range(204, 1101, 4):
    a, b = solve(B=B - 4, H=H0)["success"], solve(B=B, H=H0)["success"]
    mv[B] = round(b - a, 4)
DATA["marginal_budget"] = mv

# ---------------------------------------------------------------- 任务3.2 人工容量
human_curve = {}
for B in (600, 700, 800, 900):
    human_curve[str(B)] = [{"H": Hh, "success": solve(B=B, H=Hh)["success"],
                            "human": solve(B=B, H=Hh)["human"]} for Hh in range(0, 31)]
DATA["human_curve"] = human_curve

# ---------------------------------------------------------------- 任务3.3 需求冲击
surge = []
for n4 in range(10, 41, 2):
    n = [80, 60, 50, n4]
    r = solve(params={"n": n, "c": C, "p": P}, B=600, H=20)
    base_cost = sum(n)
    surge.append({"n4": n4, "N": sum(n), "success": r["success"], "rate": r["success"] / sum(n),
                  "cost": r["cost"], "alloc": r["alloc"], "base_cost": base_cost})
DATA["surge_type4"] = surge

# 结构冲击：总人数不变，高难度占比上升
struct = []
for shift in range(0, 21, 2):
    n = [80 - shift, 60, 50, 10 + shift]
    r = solve(params={"n": n, "c": C, "p": P}, B=600, H=20)
    struct.append({"shift": shift, "n": n, "success": r["success"], "rate": r["success"] / 200,
                   "cost": r["cost"], "alloc": r["alloc"]})
DATA["surge_struct"] = struct

# ---------------------------------------------------------------- 任务3.4 参数扰动
perturb = []
for tag, dp2, dp3 in [("升级成功率-5pp", -0.05, 0.0), ("人工成功率-5pp", 0.0, -0.05),
                      ("双降5pp", -0.05, -0.05), ("升级+5pp", 0.05, 0.0),
                      ("人工+5pp", 0.0, 0.05), ("双升5pp", 0.05, 0.05)]:
    p = [[P[i][0], min(0.999, P[i][1] + dp2), min(0.999, P[i][2] + dp3)] for i in range(4)]
    r = solve(params={"n": N, "c": C, "p": p}, B=600, H=20)
    perturb.append({"tag": tag, "success": r["success"], "alloc": r["alloc"], "cost": r["cost"]})
DATA["perturb"] = perturb

# ---------------------------------------------------------------- 任务3.5 蒙特卡洛
def simulate(alloc, reps=40000, seed=7):
    rg = np.random.default_rng(seed)
    succ = np.zeros(reps)
    for i, (d, a, b) in enumerate(alloc):
        succ += rg.binomial(d, P[i][0], reps) if d else 0
        succ += rg.binomial(a, P[i][1], reps) if a else 0
        succ += rg.binomial(b, P[i][2], reps) if b else 0
    return succ


mc = {}
for key in ("A", "B", "C", "D"):
    s = simulate(plans[key]["alloc"])
    mc[key] = {"mean": float(s.mean()), "sd": float(s.std()),
               "p5": float(np.percentile(s, 5)), "p95": float(np.percentile(s, 95)),
               "min": int(s.min()), "max": int(s.max()),
               "p_ge_170": float((s >= 170).mean()), "p_ge_175": float((s >= 175).mean()),
               "p_ge_155": float((s >= 155).mean()), "p_lt_160": float((s < 160).mean())}
DATA["mc"] = mc

# ---------------------------------------------------------------- 关键阈值
th = []
for B in range(200, 1101, 1):
    r = solve(B=B, H=H0)
    th.append((B, r["success"], r["human"], tuple(r["alloc"])))
changes = []
prev = None
for B, s, h, al in th:
    if prev is not None and al != prev:
        changes.append({"B": B, "success": s, "human": h, "alloc": list(al)})
    prev = al
DATA["allocation_changes"] = changes
DATA["human_full_budget"] = next((B for B, s, h, al in th if h >= H0), None)

with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as f:
    json.dump(DATA, f, ensure_ascii=False, indent=1, default=str)

print("基准最优:", compact(opt))
print("方案对比:")
for k, v in plans.items():
    print(" ", k, round(v["success"], 2), v["cost"], v["human"])
print("无人工最优:", compact(planB))
print("人工名额用满的预算 B =", DATA["human_full_budget"])
print("分配结构变化点:", [(c["B"], c["success"]) for c in changes])
print("蒙特卡洛:", {k: (round(v["mean"], 2), round(v["sd"], 2)) for k, v in mc.items()})
print("扰动:")
for p in perturb:
    print(" ", p["tag"], p["success"], p["alloc"])
