import sys, time
sys.path.insert(0, ".")
from er_model import *

def prepared(wid, key):
    w = W[wid]
    steps = chain(w["wepmotionCategory"], 30000 if key == "1h" else 32000, w["spAtkcategory"])
    out = []
    for cancel, judges in steps:
        cands = []
        for j in judges:
            b, a = behavior(w["behaviorVariationId"], j)
            if a:
                cands.append([a["atkPhysCorrection"], a["atkMagCorrection"], a["atkFireCorrection"], a["atkThunCorrection"], a["atkDarkCorrection"]])
        if not cands:
            return None
        out.append((cancel, cands))
    return out or None

def dps_of(wid, st, key, prep, d=130):
    AR = ar(wid, st, key == "2h")
    dmg = sum(max(sum(eff(AR[e] * c[e] / 100, d) for e in range(5)) for c in cands) for _, cands in prep)
    return dmg / (sum(x[0] for x in prep) / 60), AR

def optimize(wid, key, prep, budget):
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
    cur = dps_of(wid, st, key, prep)[0]
    while left > 0 and rel:
        best = (0, None)
        for i in rel:
            for c in (1, 5, 10, 20):
                if c > left or st[i] + c > 99: continue
                t = st[:]; t[i] += c
                g = (dps_of(wid, t, key, prep)[0] - cur) / c
                if g > best[0]: best = (g, i)
        if best[1] is None: break
        st[best[1]] += 1; left -= 1
        cur = dps_of(wid, st, key, prep)[0]
    d, AR = dps_of(wid, st, key, prep)
    return d, st, AR

budget = int(sys.argv[1]) if len(sys.argv) > 1 else 74
rows = []
t0 = time.time()
for wid, w in sorted(W.items()):
    if wid % 100 or wid >= 70000000 or w["wepType"] not in MELEE: continue
    base = wid - wid % 10000
    nm = N.get(base, "")
    if not nm or nm.startswith("[NPC]") or wid not in N: continue
    inf = INFUSIONS.get(wid % 10000)
    if inf is None: continue
    for key in ("1h", "2h"):
        prep = prepared(wid, key)
        if not prep: continue
        r = optimize(wid, key, prep, budget)
        if r: rows.append((r[0], nm, inf, key, r[1], [round(x) for x in r[2]], [p[0] for p in prep]))
rows.sort(reverse=True)
import pickle; pickle.dump(rows, open(f"rank_{budget}.pkl", "wb"))
print(len(rows), "rows", round(time.time() - t0), "s")
seen = set(); k = 0
for r in rows:
    if r[1] in seen: continue
    seen.add(r[1]); k += 1
    print(k, round(r[0]), r[2], r[1], r[3], r[4], r[5], r[6])
    if k == 30: break
