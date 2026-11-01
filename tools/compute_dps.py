#!/usr/bin/env python3
"""Sustained light-attack DPS for every Dark Souls III melee weapon and infusion.

Inputs
  --frames   output of `ds3_frames.py <Game dir> full` (TAE attack/cancel frames + EquipParamWeapon motion categories)
  --weapons  DataGenerator/Raw folder of https://github.com/Phil25/DS3InventoryBuilder
             (weapons_10.csv and saturations.csv: base damage, scaling and CalcCorrectGraph curves)
  --out      output folder for the CSV files

Model
  AR       : DS3 attack-rating formula (base x (1 + scaling x CalcCorrect)), +10 / +5 weapons, two-handed (Str x 1.5)
  Damage   : per hit, per element, DS-series attack/defense curve against a flat defense value
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
grid = []
for a in range(0, BUDGET + 1, STEP):
    for b in range(0, BUDGET + 1 - a, STEP):
        for c in range(0, BUDGET + 1 - a - b, STEP):
            for d in range(0, BUDGET + 1 - a - b - c, STEP):
                grid.append((a, b, c, d, BUDGET - a - b - c - d))
G = np.minimum(np.array(grid) + np.array(BASE), 99)

BUILDS = {
    "pure_str": (66, 10, 10, 10, 10), "pure_dex": (18, 60, 10, 10, 10), "quality": (40, 40, 10, 10, 10),
    "int": (18, 18, 60, 10, 10), "faith": (18, 18, 10, 60, 10), "int_faith": (16, 16, 40, 40, 10),
    "luck": (18, 18, 10, 10, 60),
}

# ---------------------------------------------------------------- frames (from ds3_frames.py full)
TAE, WCAT = {}, {}
for line in open(args.frames):
    line = line.rstrip("\n")
    if line.startswith("W "):
        for tok in line.split()[1:]:
            i, c, o, b, sp = map(int, tok.split(":")); WCAT[i] = (c, sp)
        continue
    tae, aid, atk, rh, lh, rhi, ref = line.split("|")
    f, imp, _ = map(int, ref.split(":"))
    TAE[(int(tae[1:]), int(aid))] = dict(
        hits=[tuple(map(int, x.split("-"))) for x in atk.split("/") if x],
        rh=[int(x) for x in rh.split("/") if x], lh=[int(x) for x in lh.split("/") if x],
        ref=imp if f == 1 else None)


def resolve(t, aid, depth=0):
    e = TAE.get((t, aid))
    if e is None or depth > 5:
        return None, None
    if e["hits"] and (e["rh"] or e["lh"]):
        return e, t
    if e["ref"] and e["ref"] > 0:
        return resolve(e["ref"] // 1000000, e["ref"] % 1000000, depth + 1)
    return None, None


def chain(cat, sp, base, hand):
    out, srcs = [], []
    for k in range(3):
        e = src = None
        for t in ([sp] if sp else []) + [cat]:
            e, src = resolve(t, base + 10 * k)
            if e:
                break
        if e is None or not e[hand]:
            return None, None
        out.append(e[hand][0]); srcs.append(f"a{src}_{base + 10 * k}")
    return out, srcs

# ---------------------------------------------------------------- motion values (community AtkParam sheet)
MV_R1_CLASS = {"Ultra Greatsword": 105, "Greataxe": 105, "Great Hammer": 105}
MV_R1_W = {"Halberd": 98, "Red Hilted Halberd": 98, "Friede's Great Scythe": 115}
MV_L1 = {"Sellsword Twinblades": [85, 85], "Warden Twinblades": [85, 85], "Winged Knight Twinaxes": [90, 90],
         "Dancer's Enchanted Swords": [90, 90], "Brigand Twindaggers": [90, 90], "Gotthard Twinswords": [85, 85],
         "Onikiri and Ubadachi": [85, 85], "Drang Twinspears": [65, 90], "Drang Hammers": [88, 88],
         "Crow Quills": [85, 85], "Caestus": [85, 85], "Demon's Fist": [85, 85], "Claw": [85, 85],
         "Manikin Claws": [85, 85], "Crow Talons": [85, 85], "Farron Greatsword": [30, 100]}
SKIP_CLS = {"Shield", "Small Shield", "Greatshield", "Staff", "Talisman", "Sacred Chime", "Bow", "Greatbow",
            "Crossbow", "Pyromancy Flame"}
SKIP_W = {"Giant Door Shield", "Dark Hand", "Ringed Knight Paired Greatswords"}

# ---------------------------------------------------------------- per-weapon chains
chains = {}
with open(f"{args.out}/weapon_chains{args.tag}.csv", "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["weapon_id", "weapon", "class", "wepmotionCategory", "spAtkCategory",
                 "1h_r1_frames", "1h_r1_seconds_per_attack", "2h_r1_frames", "2h_r1_seconds_per_attack",
                 "l1_dual_frames", "l1_dual_seconds_per_attack", "1h_r1_source_anims", "2h_r1_source_anims",
                 "l1_source_anims"])
    for bid, name in sorted(base_name.items()):
        cls = next(w["cls"] for w in WEAPONS if w["bid"] == bid)
        if bid not in WCAT or cls in SKIP_CLS:
            continue
        cat, sp = WCAT[bid]
        r1h, s1h = chain(cat, sp, 30000, "rh")
        r2h, s2h = chain(cat, sp, 34000, "rh")
        l1, sl1 = chain(cat, sp, 33000, "lh") if name in MV_L1 else (None, None)
        chains[name] = (r1h, r2h, l1)
        fmt = lambda x: "/".join(map(str, x)) if x else ""
        sec = lambda x: round(np.mean(x) / 60, 3) if x else ""
        wr.writerow([bid * 10000, name, cls, cat, sp, fmt(r1h), sec(r1h), fmt(r2h), sec(r2h), fmt(l1), sec(l1),
                     " ".join(s1h or []), " ".join(s2h or []), " ".join(sl1 or [])])

# ---------------------------------------------------------------- DPS
# 1H R1 motion value is 100 for every weapon in the motion-value sheet; 2H R1 is 103 (105 for UGS, greataxes,
# great hammers). Paired weapons and fists: 2H R1 is the single-blade 1H R1 clone (MV 100), L1 is the dual attack.
results, BMODE = [], {}
for w in WEAPONS:
    if w["cls"] in SKIP_CLS or w["name"] in SKIP_W or w["name"] not in chains:
        continue
    r1h, r2h, l1 = chains[w["name"]]
    opts = []
    if r2h:
        mv = [100] if w["name"] in MV_L1 else [MV_R1_W.get(w["name"]) or MV_R1_CLASS.get(w["cls"], 103)]
        opts.append(("2H R1", r2h, mv, True))
    if r1h:
        opts.append(("1H R1", r1h, [100], False))
    if l1:
        opts.append(("L1 dual", l1, MV_L1[w["name"]], True))
    req = w["req"]
    best, per_mode, bbest = None, {}, {}
    for mode, frames, mv, th in opts:
        sm = 1.5 if th else 1.0
        ok = (G[:, 0] * sm >= req["str"]) & (G[:, 1] >= req["dex"]) & (G[:, 2] >= req["int"]) & (G[:, 3] >= req["fth"])
        if not ok.any():
            continue
        A = ar_vec(w, G, th)
        secs = np.mean(frames) / 60
        per = {dfn: np.where(ok, sum(eff(A[i] * m / 100, dfn) for m in mv for i in range(5)) / secs, -1) for dfn in DEFS}
        j = int(np.argmax(per[MAIN_DEF]))
        per_mode[mode] = round(float(per[MAIN_DEF][j]))
        rec = dict(weapon=w["name"], infusion=w["inf"], cls=w["cls"], mode=mode, frames="/".join(map(str, frames)),
                   seconds_per_attack=round(secs, 3), motion_values="+".join(map(str, mv)),
                   str=int(G[j, 0]), dex=int(G[j, 1]), int=int(G[j, 2]), fth=int(G[j, 3]), lck=int(G[j, 4]),
                   ar_total=round(float(A[:, j].sum())), **{f"ar_{e}": round(float(A[i, j])) for i, e in enumerate(ELEM)})
        for dfn in DEFS:
            rec[f"dps_def{dfn}"] = round(float(per[dfn][j]))
        for bn, bs in BUILDS.items():
            okb = bs[0] * sm >= req["str"] and bs[1] >= req["dex"] and bs[2] >= req["int"] and bs[3] >= req["fth"]
            ab = ar_vec(w, np.array([bs]), th)
            rec[f"build_{bn}"] = round(float(sum(eff(ab[i] * m / 100, MAIN_DEF) for m in mv for i in range(5))[0] / secs)) if okb else ""
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
