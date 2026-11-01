#!/usr/bin/env python3
"""Export the data the interactive calculator (docs/) needs into docs/data.json.

usage: python3 tools/export_web.py --weapons DS3InventoryBuilder/DataGenerator/Raw --out docs/data.json

Per weapon and infusion: requirements, saturation curve ids, base damage + scaling + status buildup for every
upgrade level (+0..+10, or +0..+5 for unique / boss weapons), stamina rate, bleed/frost proc effect.
Per base weapon: 1H R1, 2H R1 and dual L1 chains from tools/moves.py (frames, stamina, per-hit motion values).
Bosses from tools/ds3_params.py.
"""
import argparse, csv, json, re

ap = argparse.ArgumentParser()
ap.add_argument("--weapons", required=True)
ap.add_argument("--frames", default="data/ds3_frames_full.txt")
ap.add_argument("--regulation", default="data/regulation_extract.json")
ap.add_argument("--readme", default="README.md")
ap.add_argument("--out", default="docs/data.json")
args = ap.parse_args()
RAW = args.weapons

ID, NAME, CLASS, INF = 0, 1, 2, 3
REQ = [8, 9, 10, 11]                     # str dex int fth
SAT = [23, 24, 25, 26, 27]               # physical magic fire lightning dark
DMG = [178, 179, 180, 181, 182]
SCL = [194, 195, 196, 197, 198]          # str dex int fth lck

sats = {}
for row in csv.reader(open(f"{RAW}/saturations.csv")):
    if int(row[1]) > 16:
        break
    sats[int(row[1])] = [0.0] + [round(float(row[c]), 3) for c in range(319, 418)]

levels = [{r[ID]: r for r in csv.reader(open(f"{RAW}/weapons_{n}.csv"))} for n in range(11)]
sat_idx = {i: [int(r[c]) for c in SAT] for i, r in levels[0].items()}
base_name = {int(i) // 10000: r[NAME] for i, r in levels[10].items() if r[INF] == "-"}

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moves as MV
TAE, WCAT = MV.load_frames(args.frames)
REG = json.load(open(args.regulation))
SKIP_CLS = {"Shield", "Small Shield", "Greatshield", "Staff", "Talisman", "Sacred Chime", "Bow", "Greatbow",
            "Crossbow", "Pyromancy Flame"}
moves = {}
for i, r in levels[10].items():
    if r[INF] != "-" or r[CLASS] in SKIP_CLS:
        continue
    bid = int(i) // 10000
    row = REG["weapons"].get(str(bid * 10000))
    if row:
        m = MV.weapon_moves(TAE, WCAT, REG, bid, r[NAME], row)
        if m:
            moves[r[NAME]] = m

def lv(r):
    # base damage x5, scaling x5, bleed buildup, frost buildup, luck modifier for status
    return ([round(float(r[c]), 2) for c in DMG] + [round(float(r[c]), 2) for c in SCL]
            + [float(r[170]), float(r[177]), float(r[39])])


weapons = []
for i, r10 in levels[10].items():
    name = base_name[int(i) // 10000]
    if name not in moves:
        continue
    lvs = [lv(levels[n][i]) for n in range(11)]
    unique = lvs[0] == lvs[1] and lvs[0] != lvs[2]
    if unique:                                     # +k is stored in file 2k
        lvs = [lvs[2 * k] for k in range(6)]
    reg = REG["weapons"].get(i, {})
    w = dict(n=name, c=r10[CLASS], i=r10[INF], req=[int(r10[c]) for c in REQ], sat=sat_idx[i], lv=lvs,
             scr=reg.get("scr", 1.0), lc=float(levels[0][i][17]), sb=int(levels[0][i][28]))
    if "b" in reg: w["pb"] = reg["b"]          # bleed proc: % max HP, flat
    if "f" in reg: w["pf"] = reg["f"]          # frost proc
    weapons.append(w)

md = open(args.readme).read()
links = dict(re.findall(r"\[([^\]]+)\]\((https://darksouls3\.wiki\.fextralife\.com/[^)]+)\)", md))
used = sorted({s for w in weapons for s in w["sat"]} | {w["sb"] for w in weapons})
out = dict(sats={k: sats[k] for k in used}, moves=moves, weapons=weapons, links=links, bosses=REG["bosses"])
json.dump(out, open(args.out, "w"), separators=(",", ":"))
print(f"{len(weapons)} weapon/infusion rows, {len(moves)} movesets -> {args.out}")
