#!/usr/bin/env python3
"""Read-only: mark weapons that can't take a resin / spell buff (EquipParamWeapon isEnhance = 0) in docs/data.json.

usage: python3 tools/ds3_buffable.py <Game>/Data0.bdt <Paramdex>/DS3 <DS3InventoryBuilder>/DataGenerator/Raw docs/data.json

Adds "nb": 1 to every weapon/infusion row whose regulation row has isEnhance 0. This covers elemental infusions,
Blood / Poison / Blessed / Simple, and unique weapons such as Storm Ruler or Moonlight Greatsword.
"""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv = sys.argv; sys.argv = sys.argv[:1]
from ds3_frames import aes_cbc_dec, bnd4, dcx
sys.argv = _argv
import param_reader as P

data0, paramdex, raw_dir, out = sys.argv[1:5]
raw = open(data0, "rb").read()
body = raw[16:]; body = body[:len(body) // 16 * 16]
dec = aes_cbc_dec(b"ds3#jn/8_7(rsY9pg55GFN7VFL#+3n/)", raw[:16], body)
files = {os.path.basename(n.replace("\\", "/")).rsplit(".", 1)[0]: d for _, n, d in bnd4(dcx(dec))}
P.setup(paramdex, files)
wep, _, _ = P.read_param("EquipParamWeapon", "EQUIP_PARAM_WEAPON_ST")
rows = [r for r in csv.reader(open(f"{raw_dir}/weapons_10.csv")) if r and r[0].isdigit()]
base_name = {int(r[0]) // 10000: r[1] for r in rows if r[3] == "-"}          # infusion rows carry other names
ids = {(base_name.get(int(r[0]) // 10000), r[3]): int(r[0]) for r in rows}
D = json.load(open(out))
n_nb = miss = 0
for w in D["weapons"]:
    wid = ids.get((w["n"], w["i"]))
    if wid is None or wid not in wep:
        miss += 1; continue
    if wep[wid]["isEnhance"] == 0:
        w["nb"] = 1; n_nb += 1
    else:
        w.pop("nb", None)
json.dump(D, open(out, "w"), separators=(",", ":"))
print(f"{n_nb} rows can't be buffed, {miss} rows not matched")
