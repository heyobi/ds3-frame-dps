#!/usr/bin/env python3
"""Export what the Elden Ring calculator page (docs/er/) needs into docs/er/data.json.

usage: ER_FILES=er_files python3 er/export_web.py --out docs/er/data.json

Per weapon + infusion (max upgrade only): requirements, per element base damage, stat coefficients, scaling curve,
requirement mask, status buildup and proc. Per moveset: 1H R1, 2H R1 and powerstance chains (frames, hits, motion
values). Bosses with status thresholds after every proc.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import er_model as M

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="docs/er/data.json")
args = ap.parse_args()

CLASS = {1: "Dagger", 3: "Straight Sword", 5: "Greatsword", 7: "Colossal Sword", 9: "Curved Sword",
         11: "Curved Greatsword", 13: "Katana", 14: "Twinblade", 15: "Thrusting Sword", 16: "Heavy Thrusting Sword",
         17: "Axe", 19: "Greataxe", 21: "Hammer", 23: "Great Hammer", 24: "Flail", 25: "Spear", 28: "Great Spear",
         29: "Halberd", 31: "Reaper", 35: "Fist", 37: "Claw", 39: "Whip", 41: "Colossal Weapon", 88: "Hand-to-Hand",
         91: "Throwing Blade", 92: "Backhand Blade", 93: "Light Greatsword", 94: "Great Katana", 95: "Beast Claw"}
r2 = lambda x: round(x, 2)
graphs_used, moves, weapons, mkeys = set(), {}, [], {}

for wid, w in sorted(M.W.items()):
    if wid % 100 or wid >= 70000000 or w["wepType"] not in CLASS:
        continue
    base_id = wid - wid % 10000
    nm = M.N.get(base_id, "")
    inf = M.INFUSIONS.get(wid % 10000)
    if not nm or nm.startswith("[NPC]") or wid not in M.N or inf is None:
        continue
    preps = {}
    for key in ("1h", "2h", "ps"):
        p = M.prepare(wid, key)
        if p:
            preps[key] = [[c, [[[*mv, pt] for mv, pt in cands] for cands in hits]] for c, hits in p]
    if not preps:
        continue
    sig = json.dumps(preps, separators=(",", ":"))
    if sig not in mkeys:
        mkeys[sig] = len(moves); moves[len(moves)] = preps
    lv = M.max_level(w); rf = M.RF[w["reinforceTypeId"] + lv]; ae = M.AE[w["attackElementCorrectId"]]
    el = []
    for e, en in enumerate(M.ELEM):
        b = w[M.BASE[e]] * rf[M.RATE[e]]
        if b <= 0:
            el.append(None); continue
        coef, mask = [0] * 5, [0] * 5
        for s, sn in enumerate(M.STATS):
            if not ae.get(f"is{sn}Correct_by{en}"):
                continue
            mask[s] = 1
            ow = ae.get(f"overwrite{sn}CorrectRate_by{en}", -1)
            coef[s] = round((ow if ow >= 0 else w[M.WCORR[s]]) * rf[M.RCORR[s]] / 100
                            * ae.get(f"Influence{sn}CorrectRate_by{en}", 100) / 100, 5)
        graphs_used.add(w[M.GRAPH[e]])
        el.append([r2(b), coef, w[M.GRAPH[e]], mask])
    row = dict(n=nm, i=inf, c=CLASS[w["wepType"]], up=lv, req=[w[k] for k in M.REQ], el=el, m=mkeys[sig])
    if w["isDualBlade"]:
        row["pair"] = 1
    raw = {}
    for i in range(3):                                    # buildup without arcane, plus arcane coefficient
        sid = w[f"spEffectBehaviorId{i}"]
        e = M.SP.get(sid + rf.get(f"spEffectId{i + 1}", 0)) or M.SP.get(sid) if sid > 0 else None
        if e and e["bloodAttackPower"] > 0:
            raw["b"] = [e["bloodAttackPower"], e["changeHpRate"], e["changeHpPoint"]]
        if e and e["freezeAttackPower"] > 0:
            raw["f"] = [e["freezeAttackPower"], e["changeHpRate"], e["changeHpPoint"]]
    if raw:
        row.update(raw)
        if "b" in raw and w["correctLuck"] > 0:
            row["lc"] = round(w["correctLuck"] * rf["correctLuckRate"] / 100, 5); row["lg"] = w["correctType_Blood"]
            graphs_used.add(w["correctType_Blood"])
    weapons.append(row)

bosses = []
for name, i in M.BOSS_IDS:
    b = M.boss(name, i)
    bosses.append(dict(n=name, hp=b["hp"], df=[r2(x) for x in b["df"]], mul=[r2(x) for x in b["mul"]],
                       bleed=[r2(x) for x in M.thresholds(b["bleed"])] if b["bleed"] else None,
                       frost=[r2(x) for x in M.thresholds(b["frost"])] if b["frost"] else None,
                       br=b["bloodRate"], fr=b["frostRate"]))

graphs = {g: [0] + [round(M.graph(g, x), 3) for x in range(1, 100)] for g in sorted(graphs_used)}
json.dump(dict(graphs=graphs, moves=moves, weapons=weapons, bosses=bosses), open(args.out, "w"), separators=(",", ":"))
print(f"{len(weapons)} weapon/infusion rows, {len(moves)} movesets, {len(bosses)} bosses -> {args.out}")
