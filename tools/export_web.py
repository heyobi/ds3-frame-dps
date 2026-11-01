#!/usr/bin/env python3
"""Export the data the interactive calculator (docs/) needs into docs/data.json.

usage: python3 tools/export_web.py --frames data/ds3_frames_full.txt \
           --weapons DS3InventoryBuilder/DataGenerator/Raw --chains results/weapon_chains.csv --out docs/data.json

Per weapon and infusion: requirements, saturation curve ids, and base damage + scaling for every upgrade level
(+0..+10, or +0..+5 for unique / boss weapons). Per base weapon: 1H R1, 2H R1 and dual L1 chain frames and the
motion values used in tools/compute_dps.py.
"""
import argparse, csv, json, re

ap = argparse.ArgumentParser()
ap.add_argument("--weapons", required=True)
ap.add_argument("--chains", default="results/weapon_chains.csv")
ap.add_argument("--readme", default="README.md")
ap.add_argument("--out", default="docs/data.json")
args = ap.parse_args()
RAW = args.weapons

ID, NAME, CLASS, INF = 0, 1, 2, 3
REQ = [8, 9, 10, 11]                     # str dex int fth
SAT = [23, 24, 25, 26, 27]               # physical magic fire lightning dark
DMG = [178, 179, 180, 181, 182]
SCL = [194, 195, 196, 197, 198]          # str dex int fth lck

# keep in sync with tools/compute_dps.py
MV_R1_CLASS = {"Ultra Greatsword": 105, "Greataxe": 105, "Great Hammer": 105}
MV_R1_W = {"Halberd": 98, "Red Hilted Halberd": 98, "Friede's Great Scythe": 115}
MV_L1 = {"Sellsword Twinblades": [85, 85], "Warden Twinblades": [85, 85], "Winged Knight Twinaxes": [90, 90],
         "Dancer's Enchanted Swords": [90, 90], "Brigand Twindaggers": [90, 90], "Gotthard Twinswords": [85, 85],
         "Onikiri and Ubadachi": [85, 85], "Drang Twinspears": [65, 90], "Drang Hammers": [88, 88],
         "Crow Quills": [85, 85], "Caestus": [85, 85], "Demon's Fist": [85, 85], "Claw": [85, 85],
         "Manikin Claws": [85, 85], "Crow Talons": [85, 85], "Farron Greatsword": [30, 100]}
SKIP_W = {"Giant Door Shield", "Dark Hand", "Ringed Knight Paired Greatswords"}

sats = {}
for row in csv.reader(open(f"{RAW}/saturations.csv")):
    if int(row[1]) > 16:
        break
    sats[int(row[1])] = [0.0] + [round(float(row[c]), 3) for c in range(319, 418)]

levels = [{r[ID]: r for r in csv.reader(open(f"{RAW}/weapons_{n}.csv"))} for n in range(11)]
sat_idx = {i: [int(r[c]) for c in SAT] for i, r in levels[0].items()}
base_name = {int(i) // 10000: r[NAME] for i, r in levels[10].items() if r[INF] == "-"}

moves = {}
for r in csv.DictReader(open(args.chains)):
    name = r["weapon"]
    if name in SKIP_W:
        continue
    fr = lambda k: [int(x) for x in r[k].split("/")] if r[k] else None
    m = {}
    if fr("1h_r1_frames"):
        m["r1h"] = [fr("1h_r1_frames"), [100]]
    if fr("2h_r1_frames"):
        mv = [100] if name in MV_L1 else [MV_R1_W.get(name) or MV_R1_CLASS.get(r["class"], 103)]
        m["r2h"] = [fr("2h_r1_frames"), mv]
    if fr("l1_dual_frames"):
        m["l1"] = [fr("l1_dual_frames"), MV_L1[name]]
    if m:
        moves[name] = m


def lv(r):
    return [round(float(r[c]), 2) for c in DMG] + [round(float(r[c]), 2) for c in SCL]


weapons = []
for i, r10 in levels[10].items():
    name = base_name[int(i) // 10000]
    if name not in moves:
        continue
    lvs = [lv(levels[n][i]) for n in range(11)]
    unique = lvs[0] == lvs[1] and lvs[0] != lvs[2]
    if unique:                                     # +k is stored in file 2k
        lvs = [lvs[2 * k] for k in range(6)]
    weapons.append(dict(n=name, c=r10[CLASS], i=r10[INF], req=[int(r10[c]) for c in REQ], sat=sat_idx[i], lv=lvs))

md = open(args.readme).read()
links = dict(re.findall(r"\[([^\]]+)\]\((https://darksouls3\.wiki\.fextralife\.com/[^)]+)\)", md))
used = sorted({s for w in weapons for s in w["sat"]})
out = dict(sats={k: sats[k] for k in used}, moves=moves, weapons=weapons, links=links)
json.dump(out, open(args.out, "w"), separators=(",", ":"))
print(f"{len(weapons)} weapon/infusion rows, {len(moves)} movesets -> {args.out}")
