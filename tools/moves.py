"""Light-attack chains per weapon, combining TAE frame data (tools/ds3_frames.py full output) with the
behavior / attack params from the regulation (tools/ds3_params.py output).

A chain step = one animation: it lasts until the first attack-cancel frame (RH for R1 chains, LH for L1 chains).
R1 steps deal their strongest AttackBehavior hit; dual L1 steps deal every AttackBehavior that starts before the
cancel frame (one per blade). Each hit's behavior judge id is looked up in
BehaviorParam_PC (weapon's behavior variation first, then the motion category's base variation) to get its
stamina cost and its motion values (AtkParam_Pc *Correction fields).
"""
import json

MOVE_DEF = {"r1h": (30000, "rh"), "r2h": (34000, "rh"), "l1": (33000, "lh")}
# Weapons whose two-handed L1 is the dual attack chain
L1_WEAPONS = {"Sellsword Twinblades", "Warden Twinblades", "Winged Knight Twinaxes", "Dancer's Enchanted Swords",
              "Brigand Twindaggers", "Gotthard Twinswords", "Onikiri and Ubadachi", "Drang Twinspears", "Drang Hammers",
              "Crow Quills", "Caestus", "Demon's Fist", "Claw", "Manikin Claws", "Crow Talons", "Farron Greatsword"}
SKIP_W = {"Giant Door Shield", "Dark Hand", "Ringed Knight Paired Greatswords"}
PHYS_TYPE = {0: 1, 1: 2, 2: 3, 3: 0}     # AtkAttribute -> index in boss multipliers (0 std, 1 slash, 2 strike, 3 thrust)


def load_frames(path):
    tae, wcat = {}, {}
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("W "):
            for tok in line.split()[1:]:
                i, c, o, b, sp = map(int, tok.split(":")); wcat[i] = (c, sp)
            continue
        f = line.split("|")
        t, aid, atk, rh, lh = f[0], f[1], f[2], f[3], f[4]
        fl, imp, _ = map(int, f[6].split(":"))
        wins = [tuple(map(int, x.split("-"))) for x in atk.split("/") if x]
        args = [tuple(map(int, x.split(","))) for x in f[7].split("/")] if len(f) > 7 and f[7] else [()] * len(wins)
        hits = [(w[0], a[2] if len(a) > 2 else None, a[0] if a else 0) for w, a in zip(wins, args)]
        tae[(int(t[1:]), int(aid))] = dict(hits=hits, rh=[int(x) for x in rh.split("/") if x],
                                          lh=[int(x) for x in lh.split("/") if x], ref=imp if fl == 1 else None)
    return tae, wcat


def resolve(tae, t, aid, depth=0):
    e = tae.get((t, aid))
    if e is None or depth > 5:
        return None
    if e["hits"] and (e["rh"] or e["lh"]):
        return e
    if e["ref"] and e["ref"] > 0:
        return resolve(tae, e["ref"] // 1000000, e["ref"] % 1000000, depth + 1)
    return None


def chain(tae, cat, sp, key):
    base, hand = MOVE_DEF[key]
    steps = []
    for k in range(3):
        e = None
        for t in ([sp] if sp else []) + [cat]:
            e = resolve(tae, t, base + 10 * k)
            if e:
                break
        if e is None or not e[hand]:
            return None
        cancel = e[hand][0]
        hits = [judge for start, judge, a0 in sorted(e["hits"]) if judge is not None and a0 == 0 and start < cancel]
        steps.append((cancel, hits))
    return steps


def behavior(reg, var, cat, judge):
    for v in (str(var), str(cat * 100)):
        b = reg["behaviors"].get(v, {}).get(str(judge))
        if b:
            return b
    return None


def weapon_moves(tae, wcat, reg, bid, name, row):
    """-> {key: [[frames, stamina, [[mvPhys, mvMag, mvFire, mvLight, mvDark, physType], ...]], ...]} (3 steps)."""
    if bid not in wcat or name in SKIP_W:
        return {}
    cat, sp = wcat[bid]
    out = {}
    for key in MOVE_DEF:
        if key == "l1" and name not in L1_WEAPONS:
            continue
        steps = chain(tae, cat, sp, key)
        if not steps:
            continue
        res = []
        for cancel, judges in steps:
            found = []
            for j in judges:
                b = behavior(reg, row["var"], row["cat"], j)
                if not b or sum(b[1:6]) == 0:
                    continue
                attr = b[6]
                if attr == 4:     # weapon default physical type
                    t = row["types"]
                    ptype = 1 if t[1] else 2 if t[2] else 3 if t[3] else 0
                else:
                    ptype = PHYS_TYPE.get(attr, 0)
                found.append((b[0], b[1:6] + [ptype]))
            if not found:
                res = None
                break
            if key != "l1":
                # An R1 swing can carry several hitbox phases (e.g. halberd/scythe sweep, katana 1H); it damages a
                # target once, with the strongest phase. Matches the community motion values (98, 105, 115...).
                found = [max(found, key=lambda f: sum(f[1][:5]))]
            # Dual L1: every AttackBehavior is a separate blade/strike (identical duplicate events = both blades)
            res.append([cancel, sum(f[0] for f in found), [f[1] for f in found]])
        if res:
            out[key] = res
    return out
