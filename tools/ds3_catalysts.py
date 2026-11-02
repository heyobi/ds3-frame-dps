#!/usr/bin/env python3
"""Read-only: catalyst spell buff data for the calculator (adds "cats" and the needed curves to docs/data.json).

usage: python3 tools/ds3_catalysts.py <Game>/Data0.bdt <Paramdex>/DS3 docs/data.json

Spell buff = 100 x (1 + (corretMagic x correctMagicRate x S_int(Int) + corretFaith x correctFaithRate x S_fth(Faith)) / 10000),
rounded down. S_int / S_fth are CalcCorrectGraph curves whose ids sit in two unnamed EquipParamWeapon fields
(Unk21 = Int graph, Unk26 = Faith graph; staffs 6/6, Pyromancy Flame 0/0, talismans 16/6, chimes 16/16).
Checked against in-game / wiki values: Pyromancy Flame +10 116 at 10/10 Int/Fth, 207 at 40/40, 221 at 60/60;
Court Sorcerer's Staff +10 150/202/220/238 at 35/50/55/60 Int; Saint's Talisman +10 187 at 45 Fth, 242 at 60.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv = sys.argv; sys.argv = sys.argv[:1]
from ds3_frames import aes_cbc_dec, bnd4, dcx
sys.argv = _argv
import param_reader as P

data0, paramdex, out = sys.argv[1:4]
raw = open(data0, "rb").read()
body = raw[16:]; body = body[:len(body) // 16 * 16]
dec = aes_cbc_dec(b"ds3#jn/8_7(rsY9pg55GFN7VFL#+3n/)", raw[:16], body)
files = {os.path.basename(n.replace("\\", "/")).rsplit(".", 1)[0]: d for _, n, d in bnd4(dcx(dec))}
P.setup(paramdex, files)
wep, _, _ = P.read_param("EquipParamWeapon", "EQUIP_PARAM_WEAPON_ST")
rw, _, _ = P.read_param("ReinforceParamWeapon", "REINFORCE_PARAM_WEAPON_ST")
cg, _, _ = P.read_param("CalcCorrectGraph", "CACL_CORRECT_GRAPH_ST")
names = {int(l.split()[0]): l.split(None, 1)[1].strip() for l in open(f"{paramdex}/Names/EquipParamWeapon.txt")
         if l.strip() and l.split()[0].isdigit()}


def curve(g, x):
    r = cg[g]; xs = [r[f"stageMaxVal{i}"] for i in range(5)]; ys = [r[f"stageMaxGrowVal{i}"] for i in range(5)]
    ad = [r[f"adjPt_maxGrowVal{i}"] for i in range(5)]
    if x <= xs[0]: return ys[0]
    for i in range(4):
        if x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i]); a = ad[i]
            t = t ** a if a > 0 else 1 - (1 - t) ** (-a)
            return ys[i] + (ys[i + 1] - ys[i]) * t
    return ys[4]


cats, graphs = [], set()
for wid in sorted(wep):
    r = wep[wid]
    if wid % 10000 or not (13000000 <= wid < 13600000): continue
    if not (r["corretMagic"] or r["corretFaith"]): continue
    school = [r["enableMagic"], r["enableMiracle"], r["enablePyromancy"]]
    if not any(school): continue
    maxlv = max(l for l in range(11) if r["reinforceTypeId"] + l in rw)
    t = rw[r["reinforceTypeId"] + maxlv]
    g = [r["Unk21"], r["Unk26"]]; graphs |= set(g)
    cats.append(dict(n=names.get(wid, str(wid)), school=school, up=maxlv,
                     c=[round(r["corretMagic"] * t["correctMagicRate"], 3), round(r["corretFaith"] * t["correctFaithRate"], 3)],
                     g=g, req=[r["properStrength"], r["properMagic"], r["properFaith"]]))
D = json.load(open(out))
for g in graphs:
    D["sats"][str(g)] = [0.0] + [round(curve(g, x), 3) for x in range(1, 100)]
D["cats"] = cats
json.dump(D, open(out, "w"), separators=(",", ":"))
print(len(cats), "catalysts, graphs", sorted(graphs))
for c in cats: print(" ", c["n"], c)
