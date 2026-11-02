#!/usr/bin/env python3
"""Weapon reach from the game files: how far from the hand the light-attack hitboxes reach.

usage: python3 tools/ds3_reach.py <Game>/Data0.bdt <Paramdex>/DS3 data/ds3_weapon_models.json \
           --weapons DS3InventoryBuilder/DataGenerator/Raw > results/reach.md

Every hit of a light attack is a sphere (one dummy point) or a capsule (between two dummy points) on the weapon
model, with a radius (AtkParam_Pc Hit*_DmyPoly1/2, Hit*_Radius). The dummy points' positions come from the weapon's
.flver (tools/ds3_models.py). Reach = distance from the model origin (where the hand holds the weapon) to the far end
of the hitbox, radius included. This is weapon reach only: how far the character steps or leans during the swing
is in the animation, not here.
"""
import argparse, csv, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv = sys.argv; sys.argv = sys.argv[:1]
from ds3_frames import aes_cbc_dec, bnd4, dcx
sys.argv = _argv
import param_reader as P, moves as MV

ap = argparse.ArgumentParser()
ap.add_argument("data0"); ap.add_argument("paramdex"); ap.add_argument("models")
ap.add_argument("--weapons", required=True)
ap.add_argument("--frames", default="data/ds3_frames_full.txt")
ap.add_argument("--json", default="data/ds3_reach.json", help="per weapon reach for the calculator")
a = ap.parse_args()

raw = open(a.data0, "rb").read()
body = raw[16:]; body = body[:len(body) // 16 * 16]
dec = aes_cbc_dec(b"ds3#jn/8_7(rsY9pg55GFN7VFL#+3n/)", raw[:16], body)
files = {os.path.basename(n.replace("\\", "/")).rsplit(".", 1)[0]: d for _, n, d in bnd4(dcx(dec))}
P.setup(a.paramdex, files)
atk, _, _ = P.read_param("AtkParam_Pc", "ATK_PARAM_ST")
beh, _, _ = P.read_param("BehaviorParam_PC", "BEHAVIOR_PARAM_ST")
wep, _, _ = P.read_param("EquipParamWeapon", "EQUIP_PARAM_WEAPON_ST")
models = json.load(open(a.models))["models"]
TAE, WCAT = MV.load_frames(a.frames)

names = {}
for r in csv.reader(open(f"{a.weapons}/weapons_10.csv")):
    if r[3] == "-":
        names[int(r[0])] = (r[1], r[2])
SKIP = {"Shield", "Small Shield", "Greatshield", "Staff", "Talisman", "Sacred Chime", "Bow", "Greatbow", "Crossbow",
        "Pyromancy Flame", "Torch"}


def atk_of(var, cat, judge):
    for v in (var, cat * 100):
        b = beh.get(100000000 + v * 1000 + judge)
        if b and b["refType"] == 0 and b["refId"] in atk:
            return atk[b["refId"]]
    return None


def reach_of(model, a_row):
    """far end of every weapon hitbox of one AtkParam row, in metres from the model origin"""
    pts = {d[0]: math.dist((0, 0, 0), d[1:4]) for d in model["dummies"]}
    best = None
    if a_row["AtkPhysCorrection"] == 0 and a_row["AtkMagCorrection"] == 0 and a_row["AtkFireCorrection"] == 0:
        return None                            # no damage (e.g. judge 99 helper boxes)
    for h in range(4):
        if a_row[f"Hit{h}_hitType"] == 2:      # helper volume (wall / map contact), not a damage hitbox
            continue
        r = a_row[f"Hit{h}_Radius"]
        ds = [a_row[f"Hit{h}_DmyPoly{k}"] for k in (1, 2)]
        ds = [d % 1000 if d >= 10000 else d for d in ds if d >= 0]   # 10xxx / 11xxx = right / left weapon's dummy xxx
        if not ds or r <= 0:
            continue
        if any(d < 100 for d in ds):          # dummy on the character (fists, kicks), not the weapon
            return None
        far = [pts[d] for d in ds if d in pts]
        if not far:
            continue
        v = max(far) + r
        best = v if best is None else max(best, v)
    return best


rows = []
for wid, (nm, cls) in sorted(names.items(), key=lambda kv: kv[1]):
    w = wep.get(wid)
    if not w or cls in SKIP or wid // 10000 not in WCAT:
        continue
    model = models.get(f"a_{w['equipModelId']:04d}")
    if not model:
        continue
    blade = max((math.dist((0, 0, 0), d[1:4]) for d in model["dummies"] if 100 <= d[0] < 200), default=0)
    cat, sp = WCAT[wid // 10000]
    out = {}
    for key in ("r1h", "r2h", "l1"):
        steps = MV.chain(TAE, cat, sp, key)
        if not steps:
            continue
        vals = []                              # per swing: the furthest of its hit phases
        for _, judges in steps:
            sv = [v for v in (reach_of(model, ar) for ar in (atk_of(w["behaviorVariationId"], w["wepmotionCategory"], j)
                                                              for j in judges) if ar) if v]
            if sv:
                vals.append(max(sv))
        if vals:
            out[key] = (vals[0], max(vals))
    if out and blade < 3.5:                    # a few models store dummies in another scale; left out
        rows.append((nm, cls, w["equipModelId"], blade, out))

print("# Weapon reach (DS3, from the game files)\n")
print("Distance from the hand to the far end of the light attack's hitbox, in metres, radius included. "
      "First = the first swing of the chain, Max = the longest-reaching swing. Weapon only: steps and lunges in the "
      "animation are not included.\n")
print("| Weapon | Class | Model | Furthest blade point | 1H R1 first | 1H R1 max | 2H R1 first | 2H R1 max | L1 dual max |")
print("|---|---|---|---|---|---|---|---|---|")
f = lambda o, k, i: f"{o[k][i]:.2f}" if k in o else ""
for nm, cls, mid, blade, o in sorted(rows, key=lambda r: -max(v[1] for v in r[4].values())):
    print(f"| {nm} | {cls} | {mid} | {blade:.2f} | {f(o, 'r1h', 0)} | {f(o, 'r1h', 1)} | {f(o, 'r2h', 0)} | {f(o, 'r2h', 1)} | {f(o, 'l1', 1)} |")
json.dump({nm: {k: [round(v[0], 2), round(v[1], 2)] for k, v in o.items()} for nm, cls, mid, blade, o in rows},
          open(a.json, "w"), separators=(",", ":"))
print(f"\n{len(rows)} weapons", file=sys.stderr)
