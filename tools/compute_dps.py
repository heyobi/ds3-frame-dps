#!/usr/bin/env python3
"""Sustained light-attack DPS for every Dark Souls III melee weapon and infusion.

Inputs
  --frames   output of `ds3_frames.py <Game dir> full` (TAE attack/cancel frames + EquipParamWeapon motion categories)
  --regulation  output of tools/ds3_params.py (behavior stamina + motion values, read from Data0.bdt)
  --weapons  DataGenerator/Raw folder of https://github.com/Phil25/DS3InventoryBuilder
             (weapons_10.csv and saturations.csv: base damage, scaling and CalcCorrectGraph curves)
  --out      output folder for the CSV files

Model
  AR       : DS3 attack-rating formula (base x (1 + scaling x CalcCorrect)), +10 / +5 weapons, two-handed (Str x 1.5)
  Damage   : per hit, per element, AR x motion value (AtkParam_Pc, per element) through the DS-series
             attack/defense curve against a flat defense value; hit list per step from tools/moves.py
  Timing   : 3-step chain, each step lasts from the start of the attack until the first frame the next attack
             can be started (TAE ChrActionFlag 4 "Cancel - RH Attack" for R1, flag 16 "Cancel - LH Attack" for L1)
  Moves    : 1H R1 chain (anims 30000/30010/30020, no Str bonus), 2H R1 chain (34000/34010/34020, Str x 1.5) and,
             for paired weapons and fists, the dual L1 chain (33000/33010/33020); the best one is reported
  Stats    : SL120 Deprived (Vig 27, Att 10, End 20, Vit 15), remaining 87 points spread over Str/Dex/Int/Fth/Lck
             on a 3-point grid to maximise DPS for that weapon and infusion
  Excluded : stamina, bleed/poison/frost buildup, buffs, rings, counter/backstab bonuses
"""
import argparse, csv, os
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--frames", required=True)
ap.add_argument("--weapons", required=True)
ap.add_argument("--regulation", default="data/regulation_extract.json", help="output of tools/ds3_params.py")
ap.add_argument("--out", default="results")
ap.add_argument("--defense", default="80,120,160")
ap.add_argument("--budget", type=int, default=87,
                help="offensive points to spread over Str/Dex/Int/Fth/Lck (SL120 Deprived with Vig27/End20/Vit15 = 87)")
ap.add_argument("--base", default="10,10,10,10,10",
                help="starting Str,Dex,Int,Fth,Lck before spending points (add ring bonuses here, e.g. 10,15,10,10,10 for Hunter's Ring)")
ap.add_argument("--tag", default="", help="suffix for output file names")
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
RAW = args.weapons
DEFS = [int(x) for x in args.defense.split(",")]
MAIN_DEF = 120 if 120 in DEFS else DEFS[0]

# ---------------------------------------------------------------- weapon parameters (AR)
ID, NAME, CLASS, INF = 0, 1, 2, 3
REQ = dict(str=8, dex=9, int=10, fth=11)
SAT = dict(physical=23, magic=24, fire=25, lightning=26, dark=27)
DMG = dict(physical=178, magic=179, fire=180, lightning=181, dark=182)
SCL = dict(str=194, dex=195, int=196, fth=197, lck=198)
ELEM = ["physical", "magic", "fire", "lightning", "dark"]

sats = {}
for row in csv.reader(open(f"{RAW}/saturations.csv")):
    if int(row[1]) > 16:
        break
    sats[int(row[1])] = np.array([0.0] + [float(row[c]) for c in range(319, 418)])

sat_idx = {r[ID]: {k: int(r[v]) for k, v in SAT.items()} for r in csv.reader(open(f"{RAW}/weapons_0.csv"))}
rows = list(csv.reader(open(f"{RAW}/weapons_10.csv")))
base_name = {int(r[ID]) // 10000: r[NAME] for r in rows if r[INF] == "-"}
WEAPONS = [dict(id=int(r[ID]), bid=int(r[ID]) // 10000, name=base_name[int(r[ID]) // 10000], cls=r[CLASS], inf=r[INF],
                req={k: int(r[v]) for k, v in REQ.items()}, dmg={k: float(r[v]) for k, v in DMG.items()},
                scl={k: float(r[v]) for k, v in SCL.items()}, sat=sat_idx[r[ID]]) for r in rows]


def ar_vec(w, G, two_hand=True):
    d, s, si = w["dmg"], w["scl"], w["sat"]
    S = lambda k, v: sats[si[k]][v] / 100
    st, dx, it, ft, lk = G.T
    st2 = np.minimum((st * 1.5).astype(int), 99) if two_hand else st
    phys = d["physical"] * (1 + s["str"] / 100 * S("physical", st2) + s["dex"] / 100 * S("physical", dx)
                            + s["lck"] / 100 * S("physical", lk)
                            + (s["fth"] / 100 * S("physical", ft) if w["inf"] == "Blessed" else 0))
    mag = d["magic"] * (1 + s["int"] / 100 * S("magic", it))
    fire = d["fire"] * (1 + s["int"] / 100 * S("fire", it) + s["fth"] / 100 * S("fire", ft))
    lig = d["lightning"] * (1 + s["fth"] / 100 * S("lightning", ft))
    dark = d["dark"] * (1 + s["int"] / 100 * S("dark", it) + s["fth"] / 100 * S("dark", ft))
    return np.stack([phys, mag, fire, lig, dark])


def eff(ar, dfn):
    ar = np.asarray(ar, float); r = np.where(ar > 0, ar / dfn, 0.0)
    m = np.select([r < 0.125, r < 1, r < 2.5, r < 8],
                  [0.1, 19.2 / 49 * (r - 0.125) ** 2 + 0.1, -0.4 / 3 * (r - 2.5) ** 2 + 0.7,
                   -0.8 / 121 * (r - 8) ** 2 + 0.9], 0.9)
    return m * ar


BUDGET, STEP = args.budget, 3
BASE = [int(x) for x in args.base.split(",")]
# Points are placed in steps of 3; when the budget is not a multiple of 3 the leftover (1 or 2) is tried on every
# stat, so it never gets dumped into one fixed stat.
B3, REM = BUDGET - BUDGET % STEP, BUDGET % STEP
grid = set()
for a in range(0, B3 + 1, STEP):
    for b in range(0, B3 + 1 - a, STEP):
        for c in range(0, B3 + 1 - a - b, STEP):
            for d in range(0, B3 + 1 - a - b - c, STEP):
                base = (a, b, c, d, B3 - a - b - c - d)
                if REM == 0:
                    grid.add(base)
                else:
                    for k in range(5):
                        grid.add(tuple(v + REM * (i == k) for i, v in enumerate(base)))
grid = sorted(grid)
G = np.minimum(np.array(grid) + np.array(BASE), 99)

BUILDS = {
    "pure_str": (66, 10, 10, 10, 10), "pure_dex": (18, 60, 10, 10, 10), "quality": (40, 40, 10, 10, 10),
    "int": (18, 18, 60, 10, 10), "faith": (18, 18, 10, 60, 10), "int_faith": (16, 16, 40, 40, 10),
    "luck": (18, 18, 10, 10, 60),
}

# ---------------------------------------------------------------- moves (frames + regulation behaviors)
import json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moves as MV
TAE, WCAT = MV.load_frames(args.frames)
REG = json.load(open(args.regulation))
SKIP_CLS = {"Shield", "Small Shield", "Greatshield", "Staff", "Talisman", "Sacred Chime", "Bow", "Greatbow",
            "Crossbow", "Pyromancy Flame"}
LABEL = {"r1h": "1H R1", "r2h": "2H R1", "l1": "L1 dual"}

# ---------------------------------------------------------------- per-weapon chains
chains = {}
with open(f"{args.out}/weapon_chains{args.tag}.csv", "w", newline="") as f:
    wr = csv.writer(f)
    hdr = ["weapon_id", "weapon", "class", "wepmotionCategory", "spAtkCategory"]
    for k in ("1h_r1", "2h_r1", "l1_dual"):
        hdr += [f"{k}_frames", f"{k}_seconds_per_attack", f"{k}_motion_values", f"{k}_stamina"]
    wr.writerow(hdr)
    for bid, name in sorted(base_name.items()):
        cls = next(w["cls"] for w in WEAPONS if w["bid"] == bid)
        row = REG["weapons"].get(str(bid * 10000))
        if bid not in WCAT or cls in SKIP_CLS or not row:
            continue
        m = MV.weapon_moves(TAE, WCAT, REG, bid, name, row)
        if not m:
            continue
        chains[name] = m
        cat, sp = WCAT[bid]
        out = [bid * 10000, name, cls, cat, sp]
        for k in ("r1h", "r2h", "l1"):
            st = m.get(k)
            out += (["/".join(str(x[0]) for x in st), round(np.mean([x[0] for x in st]) / 60, 3),
                     "/".join("+".join(str(h[0]) for h in x[2]) for x in st), "/".join(str(x[1]) for x in st)]
                    if st else ["", "", "", ""])
        wr.writerow(out)


def chain_dps(A, steps, dfn):
    """A: AR split (5 x n). Damage of the whole 3-step chain / its duration."""
    dmg = 0
    for frames, _, hits in steps:
        for h in hits:
            for e in range(5):
                dmg = dmg + eff(A[e] * h[e] / 100, dfn)
    return dmg / (sum(x[0] for x in steps) / 60)


# ---------------------------------------------------------------- DPS
# Motion values and hit counts come from the game (BehaviorParam_PC -> AtkParam_Pc), see tools/moves.py.
results, BMODE = [], {}
for w in WEAPONS:
    if w["cls"] in SKIP_CLS or w["name"] not in chains:
        continue
    m = chains[w["name"]]
    opts = [(LABEL[k], m[k], k != "r1h") for k in ("r2h", "r1h", "l1") if k in m]
    req = w["req"]
    best, per_mode, bbest = None, {}, {}
    for mode, steps, th in opts:
        sm = 1.5 if th else 1.0
        ok = (G[:, 0] * sm >= req["str"]) & (G[:, 1] >= req["dex"]) & (G[:, 2] >= req["int"]) & (G[:, 3] >= req["fth"])
        if not ok.any():
            continue
        A = ar_vec(w, G, th)
        secs = np.mean([x[0] for x in steps]) / 60
        per = {dfn: np.where(ok, chain_dps(A, steps, dfn), -1) for dfn in DEFS}
        j = int(np.argmax(per[MAIN_DEF]))
        per_mode[mode] = round(float(per[MAIN_DEF][j]))
        rec = dict(weapon=w["name"], infusion=w["inf"], cls=w["cls"], mode=mode, frames="/".join(str(x[0]) for x in steps),
                   seconds_per_attack=round(secs, 3), motion_values="/".join("+".join(str(h[0]) for h in x[2]) for x in steps),
                   str=int(G[j, 0]), dex=int(G[j, 1]), int=int(G[j, 2]), fth=int(G[j, 3]), lck=int(G[j, 4]),
                   ar_total=round(float(A[:, j].sum())), **{f"ar_{e}": round(float(A[i, j])) for i, e in enumerate(ELEM)})
        for dfn in DEFS:
            rec[f"dps_def{dfn}"] = round(float(per[dfn][j]))
        for bn, bs in BUILDS.items():
            okb = bs[0] * sm >= req["str"] and bs[1] >= req["dex"] and bs[2] >= req["int"] and bs[3] >= req["fth"]
            ab = ar_vec(w, np.array([bs]), th)
            rec[f"build_{bn}"] = round(float(chain_dps(ab, steps, MAIN_DEF)[0])) if okb else ""
        for bn in BUILDS:  # fixed builds: keep the best move for that build, independent of the free-stat winner
            v = rec[f"build_{bn}"]
            if v != "" and (bn not in bbest or v > bbest[bn][0]):
                bbest[bn] = (v, mode)
        if best is None or rec[f"dps_def{MAIN_DEF}"] > best[f"dps_def{MAIN_DEF}"]:
            best = rec
    if best is None:
        continue
    for bn in BUILDS:
        best[f"build_{bn}"] = bbest[bn][0] if bn in bbest else ""
    BMODE[(w["name"], w["inf"])] = {bn: m for bn, (v, m) in bbest.items()}
    for m in ("1H R1", "2H R1", "L1 dual"):
        best[f"dps_{m.replace(' ', '_').lower()}_def{MAIN_DEF}"] = per_mode.get(m, "")
    results.append(best)

results.sort(key=lambda r: -r[f"dps_def{MAIN_DEF}"])
with open(f"{args.out}/dps_all_weapons{args.tag}.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    wr.writeheader(); wr.writerows(results)

with open(f"{args.out}/dps_best_per_build{args.tag}.csv", "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["build", "stats_str_dex_int_fth_lck", "rank", "weapon", "infusion", "mode", f"dps_def{MAIN_DEF}"])
    for bn, bs in BUILDS.items():
        rb = sorted([r for r in results if r[f"build_{bn}"] != ""], key=lambda r: -r[f"build_{bn}"])[:10]
        for k, r in enumerate(rb, 1):
            wr.writerow([bn, "/".join(map(str, bs)), k, r["weapon"], r["infusion"], BMODE[(r["weapon"], r["infusion"])][bn], r[f"build_{bn}"]])

print(f"wrote {len(results)} weapon/infusion rows to {args.out}")
for r in results[:5]:
    print(r[f"dps_def{MAIN_DEF}"], r["infusion"], r["weapon"], r["mode"], r["seconds_per_attack"])
