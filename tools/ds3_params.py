#!/usr/bin/env python3
"""Read boss stats, attack stamina/motion values and status effects from the DS3 regulation (Data0.bdt).

usage: python3 tools/ds3_params.py <Game>/Data0.bdt <Paramdex>/DS3 data/regulation_extract.json

Read-only. Paramdex: git clone https://github.com/soulsmods/Paramdex
Output:
  bosses     name, HP and defense after the area scaling spEffect (NG), damage multipliers per damage type
             (NpcParam "regainRate_*" fields, i.e. 1 - absorption), bleed/frost threshold (None = immune),
             bleed damage rate (NPC "Blood Damage Rate" spEffect)
  weapons    per EquipParamWeapon row: behavior variation, motion category, stamina consume rate,
             physical attack type flags, bleed/frost proc spEffect (% max HP, flat)
  behaviors  per behavior variation and judge id: stamina cost, motion values phys/mag/fire/lightning/dark,
             attack attribute (from AtkParam_Pc)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv = sys.argv; sys.argv = sys.argv[:1]
from ds3_frames import aes_cbc_dec, bnd4, dcx
sys.argv = _argv
import param_reader as P

src, pdx, out = sys.argv[1], sys.argv[2], sys.argv[3]
raw = open(src, "rb").read()
body = raw[16:]; body = body[:len(body) // 16 * 16]
dec = aes_cbc_dec(b"ds3#jn/8_7(rsY9pg55GFN7VFL#+3n/)", raw[:16], body)
files = {os.path.basename(n.replace("\\", "/")).rsplit(".", 1)[0]: d for _, n, d in bnd4(dcx(dec))}
P.setup(pdx, files)
npc, _, _ = P.read_param("NpcParam", "NPC_PARAM_ST")
sp, _, _ = P.read_param("SpEffectParam", "SP_EFFECT_PARAM_ST")
wep, _, _ = P.read_param("EquipParamWeapon", "EQUIP_PARAM_WEAPON_ST")
beh, _, _ = P.read_param("BehaviorParam_PC", "BEHAVIOR_PARAM_ST")
atk, _, _ = P.read_param("AtkParam_Pc", "ATK_PARAM_ST")

# Main boss entries (NpcParam ids). Multi-entity fights use the main body.
BOSSES = [("Iudex Gundyr", 511000), ("Vordt of the Boreal Valley", 224000), ("Curse-rotted Greatwood", 518000),
          ("Crystal Sage", 132000), ("Deacons of the Deep", 522000), ("Abyss Watchers", 304000),
          ("High Lord Wolnir", 516000), ("Old Demon King", 305000), ("Pontiff Sulyvahn", 514000),
          ("Aldrich, Devourer of Gods", 515000), ("Yhorm the Giant", 526000), ("Dancer of the Boreal Valley", 527000),
          ("Dragonslayer Armour", 316000), ("Oceiros, the Consumed King", 209000), ("Champion Gundyr", 511100),
          ("Lorian, Elder Prince", 525000), ("Lothric, Younger Prince", 525100), ("Nameless King", 501000),
          ("Soul of Cinder", 528000), ("Gravetender's Greatwolf", 603000), ("Father Ariandel", 601000),
          ("Sister Friede", 602000), ("Blackflame Friede", 602001), ("Demon Prince", 502001),
          ("Darkeater Midir", 621100), ("Slave Knight Gael", 620000)]


def boss(name, rid):
    r = npc[rid]
    effs = [v for k, v in r.items() if k.startswith("spEffectId") and isinstance(v, int) and v > 0]
    area = next((sp[e] for e in effs if e in sp and 7000 <= e < 7400), {})
    off = {e for e in effs if 30000 <= e < 30050}
    blood = next((sp[e]["bloodDamageRate"] for e in effs if e in sp and 5440 <= e <= 5443), 100)
    g = lambda k: area.get(k, 1.0)
    return dict(
        n=name, id=rid, hp=round(r["Hp"] * g("maxHpRate")),
        df=[round(r["defPhys"] * g("physDefRate"), 1), round(r["defMag"] * g("magicDefRate"), 1),
            round(r["defFire"] * g("fireDefRate"), 1), round(r["defThunder"] * g("thunderDefRate"), 1),
            round(r["defDark"] * g("darkDefRate"), 1)],
        # damage multipliers: standard, slash, strike, thrust, magic, fire, lightning, dark
        mul=[round(r[k], 3) for k in ("regainRate_PhysNeutral", "regainRate_PhysSlash", "regainRate_PhysBlow",
                                       "regainRate_PhysThrust", "regainRate_Magic", "regainRate_Fire",
                                       "regainRate_Thunder", "regainRate_Dark")],
        bleed=None if (30020 in off or r["resistBlood"] >= 999) else round(r["resistBlood"] * g("registBloodChangeRate")),
        frost=None if (30040 in off or r["resistFrost"] >= 999) else round(r["resistFrost"] * g("registFrostChangeRate")),
        bloodRate=blood)


def status(r):
    out = {}
    for k in ("spEffectBehaviorId0", "spEffectBehaviorId1", "spEffectBehaviorId2"):
        e = sp.get(r[k])
        if not e:
            continue
        if e["registBlood"] > 0:
            out["b"] = [e["changeHpRate"], e["changeHpPoint"]]
        if e["registFrost"] > 0:
            out["f"] = [e["changeHpRate"], e["changeHpPoint"]]
    return out


weapons = {}
for wid, r in wep.items():
    if wid % 100 or wid >= 30000000:
        continue
    weapons[wid] = dict(var=r["behaviorVariationId"], cat=r["wepmotionCategory"], scr=round(r["StaminaConsumeRate"], 4),
                        types=[r["isNormalAttackType"], r["isSlashAttackType"], r["isBlowAttackType"], r["isThrustAttackType"]],
                        **status(r))
vars_used = {w["var"] for w in weapons.values()} | {w["cat"] * 100 for w in weapons.values()}
behaviors = {}
for bid, r in beh.items():
    v, j = r["variationId"], r["behaviorJudgeId"]
    if v not in vars_used or j >= 1000 or r["refType"] != 0:
        continue
    a = atk.get(r["refId"])
    if not a:
        continue
    behaviors.setdefault(str(v), {})[str(j)] = [r["stamina"], a["AtkPhysCorrection"], a["AtkMagCorrection"],
                                                a["AtkFireCorrection"], a["AtkThunCorrection"], a["atkDarkCorrection"],
                                                a["AtkAttribute"]]
res = dict(bosses=[boss(n, i) for n, i in BOSSES], weapons=weapons, behaviors=behaviors)
json.dump(res, open(out, "w"), separators=(",", ":"))
print(f"{len(res['bosses'])} bosses, {len(weapons)} weapon rows, {sum(len(v) for v in behaviors.values())} behaviors -> {out}")
