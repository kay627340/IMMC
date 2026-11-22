import itertools
import json
import numpy as np

# Base case from the problem statement (page 1-2): 200 requests/day,
# budget 600 units, at most 20 human reviews.
TYPES = [
    # name, count, p_direct, p_ai, p_human
    ("single", 80, 0.95, 0.97, 0.98),
    ("multi", 60, 0.80, 0.90, 0.95),
    ("synthesis", 50, 0.55, 0.85, 0.92),
    ("exceptional", 10, 0.35, 0.50, 0.95),
]
COST = {"direct": 1, "ai": 5, "human": 13}
BUDGET = 600
HUMAN_CAP = 20
BATCHES = 5000
SEED = 2027


def expected_correct(alloc):
    """alloc: dict type -> (n_human, n_ai); rest is direct."""
    total = 0.0
    for name, n, pd, pa, ph in TYPES:
        h, a = alloc[name]
        d = n - h - a
        assert d >= 0, (name, h, a, n)
        total += h * ph + a * pa + d * pd
    return total


def cost_of(alloc):
    total = 0
    for name, n, pd, pa, ph in TYPES:
        h, a = alloc[name]
        d = n - h - a
        total += h * COST["human"] + a * COST["ai"] + d * COST["direct"]
    return total


def best_allocation():
    best = None
    names = [t[0] for t in TYPES]
    counts = {t[0]: t[1] for t in TYPES}
    gains_ai = {t[0]: t[3] - t[2] for t in TYPES}
    for h_vals in itertools.product(*[range(0, min(c, HUMAN_CAP) + 1) for c in counts.values()]):
        H = sum(h_vals)
        if H > HUMAN_CAP:
            continue
        R = 200 - H
        remaining = BUDGET - 13 * H
        if remaining < R:
            continue
        k = (remaining - R) // 4  # number of AI upgrades affordable
        # greedy: upgrade highest-gain AI first among requests left after human
        left = {names[i]: counts[names[i]] - h_vals[i] for i in range(4)}
        ai_counts = {}
        for name in sorted(names, key=lambda x: -gains_ai[x]):
            take = min(k, left[name])
            ai_counts[name] = take
            k -= take
        alloc = {names[i]: (h_vals[i], ai_counts[names[i]]) for i in range(4)}
        c = cost_of(alloc)
        if c > BUDGET:
            continue
        e = expected_correct(alloc)
        if best is None or e > best["expected"]:
            best = {"expected": e, "cost": c, "alloc": {k2: list(v) for k2, v in alloc.items()}}
    return best


def sim_batches(alloc, batches=BATCHES, seed=SEED):
    rng = np.random.default_rng(seed)
    out = np.zeros(batches, dtype=int)
    for name, n, pd, pa, ph in TYPES:
        h, a = alloc[name]
        d = n - h - a
        # draw per-request outcomes
        out += rng.binomial(h, ph, batches)
        out += rng.binomial(a, pa, batches)
        out += rng.binomial(d, pd, batches)
    return out


def random_allocation(seed=7):
    """Random escalation within budget: shuffle the 200 requests, then assign
    each one direct / AI / human with fixed weights, only among options that
    still leave room for the remaining requests. Never exceeds the budget."""
    rng = np.random.default_rng(seed)
    pool = []
    for name, n, *_ in TYPES:
        pool += [name] * n
    order = rng.permutation(len(pool))
    alloc = {t[0]: [0, 0] for t in TYPES}
    spent, humans = 0, 0
    total = len(pool)
    for pos, idx in enumerate(order):
        name = pool[idx]
        left_after = total - pos - 1
        options, weights = [], []
        # direct always feasible if budget allows
        if spent + 1 + left_after <= BUDGET:
            options.append(1)
            weights.append(0.55)
        if spent + 5 + left_after <= BUDGET:
            options.append(5)
            weights.append(0.30)
        if humans < HUMAN_CAP and spent + 13 + left_after <= BUDGET:
            options.append(13)
            weights.append(0.15)
        if not options:
            raise RuntimeError("infeasible at position %d" % pos)
        w = np.array(weights) / sum(weights)
        c = int(rng.choice(options, p=w))
        spent += c
        if c == 5:
            alloc[name][1] += 1
        elif c == 13:
            alloc[name][0] += 1
            humans += 1
    return {k: tuple(v) for k, v in alloc.items()}


def fixed_rule_allocation():
    """300+300 style: 20 human reviews on exceptions then synthesis,
    40 AI escalations on multi-condition, rest direct."""
    return {
        "single": (0, 0),
        "multi": (0, 40),
        "synthesis": (10, 0),
        "exceptional": (10, 0),
    }


all_direct = {t[0]: (0, 0) for t in TYPES}

opt = best_allocation()
allocations = {
    "all_direct": all_direct,
    "random": random_allocation(),
    "fixed": fixed_rule_allocation(),
    "optimal": {k: tuple(v) for k, v in opt["alloc"].items()},
}

rows = []
for label, alloc in allocations.items():
    e = expected_correct(alloc)
    c = cost_of(alloc)
    sims = sim_batches(alloc)
    rows.append({
        "strategy": label,
        "expected": round(e, 2),
        "cost": c,
        "mean": round(float(sims.mean()), 2),
        "sd": round(float(sims.std(ddof=1)), 2),
        "p2_5": int(np.percentile(sims, 2.5)),
        "p97_5": int(np.percentile(sims, 97.5)),
        "per_yuan": round(float(sims.mean()) / c, 4),
        "alloc": {k: list(v) for k, v in alloc.items()},
    })

print(json.dumps(rows, indent=2, ensure_ascii=False))
print("\noptimal allocation detail:", json.dumps(opt, indent=2, ensure_ascii=False))
