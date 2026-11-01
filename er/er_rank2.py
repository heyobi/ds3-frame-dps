import sys, time, pickle
sys.path.insert(0, ".")
from er_model import *

def optimize(wid, key, prep, budget, T):
    w = W[wid]; two = key == "2h"
    st = [10] * 5
    need = [w[REQ[i]] for i in range(5)]
    if two: need[0] = math.ceil(need[0] / 1.5)
    cost = 0
    for i in range(5):
        if st[i] < need[i]: cost += need[i] - st[i]; st[i] = need[i]
    if cost > budget: return None
    rel = [i for i in range(5) if w[WCORR[i]] > 0]
    left = budget - cost
    flat = {"df": T["df"], "mul": T.get("mul"), "hp": 0}
    f = lambda s: evaluate(wid, s, key, prep, flat)[0]
    cur = f(st)
    while left > 0 and rel:
        best = (0, None)
        for i in rel:
            for c in (1, 5, 10, 20):
                if c > left or st[i] + c > 99: continue
                t = st[:]; t[i] += c
                g = (f(t) - cur) / c
                if g > best[0]: best = (g, i)
        if best[1] is None: break
        st[best[1]] += 1; left -= 1; cur = f(st)
    if left > 0:                      # spare points: arcane helps status buildup
        st[4] = min(99, st[4] + left)
    # status refinement: move points into arcane if it raises the target's effective dps
    res = evaluate(wid, st, key, prep, T)
    if T.get("hp") and w["correctLuck"] > 0:
        for _ in range(20):
            better = None
            for i in rel:
                if i == 4 or st[i] - 5 < need[i]: continue
                t = st[:]; t[i] -= 5; t[4] = min(99, t[4] + 5)
                r = evaluate(wid, t, key, prep, T)
                if r[0] > res[0] + 1e-6 and (better is None or r[0] > better[1][0]): better = (t, r)
            if not better: break
            st, res = better
    return res[0], st, res[1], ar(wid, st, two)

def run(T, budget=74, tag="flat"):
    rows = []
    for wid, w in sorted(W.items()):
        if wid % 100 or wid >= 70000000 or w["wepType"] not in MELEE: continue
        base = wid - wid % 10000; nm = N.get(base, "")
        if not nm or nm.startswith("[NPC]") or wid not in N: continue
        inf = INFUSIONS.get(wid % 10000)
        if inf is None: continue
        for key in ("1h", "2h", "ps"):
            prep = PREP.get((wid, key))
            if prep is None:
                prep = PREP[(wid, key)] = prepare(wid, key) or False
            if not prep: continue
            r = optimize(wid, key, prep, budget, T)
            if r: rows.append(dict(dps=r[0], name=nm, inf=inf, key=key, stats=r[1], parts=r[2], ar=[round(x) for x in r[3]],
                                   frames=[p[0] for p in prep], hits=[len(p[1]) for p in prep]))
    rows.sort(key=lambda r: -r["dps"])
    return rows

PREP = {}
if __name__ == "__main__":
    targets = [("flat130", flat_target(130))] + [(n, boss(n, i)) for n, i in BOSS_IDS if n in sys.argv[1:]]
    out = {}
    for tag, T in targets:
        t0 = time.time(); rows = run(T); out[tag] = rows
        print(f"== {tag} ({round(time.time()-t0)} s)")
        seen = set(); k = 0
        for r in rows:
            if r["name"] in seen: continue
            seen.add(r["name"]); k += 1
            p = r["parts"]
            print(k, round(r["dps"]), r["inf"], r["name"], r["key"], r["stats"], "direct", round(p["direct"]), "bleed", round(p.get("bleed", 0)), "frost", round(p.get("frost", 0)), "ttk", round(p.get("ttk", 0)), r["hits"])
            if k == 15: break
    pickle.dump(out, open("rank2.pkl", "wb"))
