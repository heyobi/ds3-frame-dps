"""Elden Ring light-attack DPS prototype (scratch)."""
import pickle, math, collections
D = pickle.load(open("er_files/er.pkl", "rb"))
W, RF, CC, AE = D["EquipParamWeapon"], D["ReinforceParamWeapon"], D["CalcCorrectGraph"], D["AttackElementCorrectParam"]
B, A, N, TAE, REFS, ARGS = D["BehaviorParam_PC"], D["AtkParam_Pc"], D["names_w"], D["tae"], D["refs"], D["atkargs"]
ELEM = ["Physics", "Magic", "Fire", "Thunder", "Dark"]          # Dark = holy in ER
STATS = ["Strength", "Dexterity", "Magic", "Faith", "Luck"]
WCORR = ["correctStrength", "correctAgility", "correctMagic", "correctFaith", "correctLuck"]
RCORR = ["correctStrengthRate", "correctAgilityRate", "correctMagicRate", "correctFaithRate", "correctLuckRate"]
BASE = ["attackBasePhysics", "attackBaseMagic", "attackBaseFire", "attackBaseThunder", "attackBaseDark"]
RATE = ["physicsAtkRate", "magicAtkRate", "fireAtkRate", "thunderAtkRate", "darkAtkRate"]
GRAPH = ["correctType_Physics", "correctType_Magic", "correctType_Fire", "correctType_Thunder", "correctType_Dark"]
REQ = ["properStrength", "properAgility", "properMagic", "properFaith", "properLuck"]
INFUSIONS = {0: "Standard", 100: "Heavy", 200: "Keen", 300: "Quality", 400: "Fire", 500: "Flame Art", 600: "Lightning",
             700: "Sacred", 800: "Magic", 900: "Cold", 1000: "Poison", 1100: "Blood", 1200: "Occult"}
MELEE = set(range(1, 42)) | {88, 91, 92, 93, 94, 95}


def graph(gid, x):
    g = CC[gid]
    s = [g[f"stageMaxVal{i}"] for i in range(5)]; v = [g[f"stageMaxGrowVal{i}"] for i in range(5)]
    a = [g[f"adjPt_maxGrowVal{i}"] for i in range(5)]
    if x <= s[0]:
        return v[0]
    for i in range(4):
        if x <= s[i + 1]:
            r = (x - s[i]) / (s[i + 1] - s[i])
            r = r ** a[i] if a[i] > 0 else 1 - (1 - r) ** (-a[i])
            return v[i] + (v[i + 1] - v[i]) * r
    return v[4]


def max_level(w):
    t = w["reinforceTypeId"]
    lv = 0
    for L in range(26):
        if t + L in RF:
            lv = L
        else:
            break
    return lv


def ar(wid, stats, two_hand, level=None):
    w = W[wid]
    lv = max_level(w) if level is None else level
    rf = RF[w["reinforceTypeId"] + lv]
    ae = AE[w["attackElementCorrectId"]]
    st = list(stats)
    if two_hand:
        st[0] = min(int(st[0] * 1.5), 148)
    out = []
    for e, el in enumerate(ELEM):
        base = w[BASE[e]] * rf[RATE[e]]
        if base <= 0:
            out.append(0.0); continue
        add = 0
        for s, sn in enumerate(STATS):
            if not ae.get(f"is{sn}Correct_by{el}"):
                continue
            ow = ae.get(f"overwrite{sn}CorrectRate_by{el}", -1)
            scl = (ow if ow >= 0 else w[WCORR[s]] * rf[RCORR[s]]) / 100
            infl = ae.get(f"Influence{sn}CorrectRate_by{el}", 100) / 100
            add += scl * infl * graph(w[GRAPH[e]], st[s]) / 100
        out.append(base * (1 + add))
    return out


def meets(wid, stats, two_hand):
    w = W[wid]; st = list(stats)
    if two_hand:
        st[0] = int(st[0] * 1.5)
    return all(st[i] >= w[REQ[i]] for i in range(5))


def eff(a, d):
    if a <= 0:
        return 0
    r = a / d
    m = 0.1 if r < 0.125 else 19.2 / 49 * (r - 0.125) ** 2 + 0.1 if r < 1 else -0.4 / 3 * (r - 2.5) ** 2 + 0.7 if r < 2.5 \
        else -0.8 / 121 * (r - 8) ** 2 + 0.9 if r < 8 else 0.9
    return m * a


def resolve(t, aid, depth=0):
    res = TAE.get(t, {})
    e = res.get(t * 1000000 + aid) if t * 1000000 + aid in res else res.get(aid)
    key = t * 1000000 + aid if t * 1000000 + aid in res else aid
    if e is None or depth > 5:
        return None, None
    if any(x[0] == 1 for x in e) and any(x[0] == 0 and x[3] in (4, 115) for x in e):
        return e, (t, key)
    fl, _, imp = REFS.get((t, key), (0, 0, -1))
    if imp and imp > 0:
        return resolve(2000 + (imp // 1000000) % 1000, imp % 1000000, depth + 1)
    return None, None


def chain(cat, base_aid, sp=0):
    steps = []
    for k in range(12):
        e = src = None
        for t in ([2000 + sp] if sp else []) + [2000 + cat]:
            e, src = resolve(t, base_aid + 10 * k)
            if e is not None:
                break
        if e is None:
            break
        cancel = min(round(x[1] * 60) for x in e if x[0] == 0 and x[3] in (4, 115))   # 4 RH attack, 115 R1 attack
        hits = []
        for x in e:
            if x[0] == 1 and round(x[1] * 60) < cancel:
                a = ARGS.get((src[0], src[1], round(x[1] * 60)))
                if a:
                    hits.append(a[2])
        steps.append((cancel, hits))
    return steps


def behavior(var, judge):
    for v in (var, var // 100 * 100):
        b = B.get(100000000 + v * 1000 + judge)
        if b and b["refType"] == 0 and b["refId"] in A:
            return b, A[b["refId"]]
    return None, None


def chain_dps(wid, stats, key, defense=130):
    w = W[wid]
    two = key == "2h"
    if not meets(wid, stats, two):
        return None
    steps = chain(w["wepmotionCategory"], 30000 if key == "1h" else 32000, w["spAtkcategory"])
    if not steps:
        return None
    AR = ar(wid, stats, two)
    dmg = 0; frames = 0; mvs = []
    for cancel, judges in steps:
        best = 0; bestmv = 0
        for j in judges:
            b, a = behavior(w["behaviorVariationId"], j)
            if not a:
                continue
            cor = [a["atkPhysCorrection"], a["atkMagCorrection"], a["atkFireCorrection"], a["atkThunCorrection"], a["atkDarkCorrection"]]
            d = sum(eff(AR[e] * cor[e] / 100, defense) for e in range(5))
            if d > best:
                best, bestmv = d, cor[0]
        dmg += best; frames += cancel; mvs.append(bestmv)
    if frames == 0:
        return None
    return dict(dps=dmg / (frames / 60), ar=AR, frames=[s[0] for s in steps], mvs=mvs)
