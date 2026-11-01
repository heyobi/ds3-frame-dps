"""Elden Ring light-attack DPS prototype (scratch)."""
import pickle, math, collections, os
D = pickle.load(open(os.path.join(os.environ.get("ER_FILES", "er_files"), "er.pkl"), "rb"))
W, RF, CC, AE = D["EquipParamWeapon"], D["ReinforceParamWeapon"], D["CalcCorrectGraph"], D["AttackElementCorrectParam"]
B, A, N, TAE, REFS, ATK = D["BehaviorParam_PC"], D["AtkParam_Pc"], D["names_w"], D["tae"], D["refs"], D["atklist"]
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
STRICT = True   # light greatswords carry stamina-free 99x hitboxes; wiki hit counts match only without them
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
    if two_hand and not w.get("isDualBlade"):        # paired weapons get no two-hand Str bonus
        st[0] = min(int(st[0] * 1.5), 148)
    out = []
    for e, el in enumerate(ELEM):
        base = w[BASE[e]] * rf[RATE[e]]
        if base <= 0:
            out.append(0.0); continue
        scal = [s for s, sn in enumerate(STATS) if ae.get(f"is{sn}Correct_by{el}")]
        if any(st[s] < w[REQ[s]] for s in scal):     # unmet requirement: -40% instead of scaling
            out.append(base * 0.6); continue
        add = 0
        for s, sn in enumerate(STATS):
            if not ae.get(f"is{sn}Correct_by{el}"):
                continue
            ow = ae.get(f"overwrite{sn}CorrectRate_by{el}", -1)
            scl = (ow if ow >= 0 else w[WCORR[s]]) * rf[RCORR[s]] / 100
            infl = ae.get(f"Influence{sn}CorrectRate_by{el}", 100) / 100
            add += scl * infl * graph(w[GRAPH[e]], st[s]) / 100
        out.append(base * (1 + add))
    return out


def meets(wid, stats, two_hand):
    w = W[wid]; st = list(stats)
    if two_hand and not w.get("isDualBlade"):
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
        # Hits: every AttackBehavior that starts before the cancel. Windows of the same hand (arg1) that touch or
        # overlap are phases of one swing and count once (strongest); different hands or separate swings all count.
        evs = [(a[1], st, en, a[2]) for st, en, a in ATK.get(src, []) if st < cancel]
        groups = []
        for hand, st, en, j in sorted(evs):
            g = groups[-1] if groups else None
            if g and g["hand"] == hand and st <= g["end"]:
                g["judges"].append(j); g["end"] = max(g["end"], en)
            else:
                groups.append({"hand": hand, "end": en, "judges": [j]})
        steps.append((cancel, [g["judges"] for g in groups]))
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


# ---------------------------------------------------------------- bosses and status
SP, NP, NNPC = D["SpEffectParam"], D["NpcParam"], D["names_npc"]
RC = D.get("ResistCorrectParam")
BOSS_IDS = [("Margit, the Fell Omen", 21300014), ("Godrick the Grafted", 47500014), ("Rennala", 20310024),
            ("Starscourge Radahn", 47300040), ("Morgott, the Omen King", 21300534), ("Rykard", 47101038),
            ("Mohg, Lord of Blood", 48000068), ("Malenia, Blade of Miquella", 21200056), ("Maliketh", 21101072),
            ("Godfrey / Hoarah Loux", 47210070), ("Radagon", 21900078), ("Elden Beast", 22000078),
            ("Dragonlord Placidusax", 45200072), ("Astel", 46200062), ("Fire Giant", 47601050),
            ("Divine Beast Dancing Lion", 52100088), ("Rellana", 53000082), ("Messmer", 51301099),
            ("Romina", 50300094), ("Putrescent Knight", 50200087), ("Commander Gaius", 50000092),
            ("Golden Hippopotamus", 50100098), ("Bayle the Dread", 51200085), ("Midra", 50510086),
            ("Metyr", 52000097), ("Promised Consort Radahn", 52201089), ("Scadutree Avatar", 52300296)]


def boss(name, i):
    r = NP[i]
    effs = [r[k] for k in r if k.lower().startswith("speffectid") and isinstance(r[k], int) and r[k] > 0]
    sc = next((SP[e] for e in effs if e in SP and SP[e].get("maxHpRate", 1) != 1), {})
    g = lambda k: sc.get(k, 1.0)
    rate = lambda k: next((SP[e][k] for e in effs if e in SP and SP[e].get(k, 100) != 100), 100)
    def res(k, rk, rate_key):
        # (base resist, ResistCorrectParam id, area multiplier); None = immune
        v = r[k]
        return None if v >= 999 else (v, r[rk], g(rate_key))
    return dict(n=name, id=i, hp=round(r["hp"] * g("maxHpRate")),
                df=[r["def_phys"] * g("physicsDiffenceRate"), r["def_mag"] * g("magicDiffenceRate"), r["def_fire"] * g("fireDiffenceRate"),
                    r["def_thunder"] * g("thunderDiffenceRate"), r["def_dark"] * g("darkDiffenceRate")],
                mul=[r["neutralDamageCutRate"], r["slashDamageCutRate"], r["blowDamageCutRate"], r["thrustDamageCutRate"],
                     r["magicDamageCutRate"], r["fireDamageCutRate"], r["thunderDamageCutRate"], r["darkDamageCutRate"]],
                bleed=res("resist_blood", "resistCorrectId_blood", "registBloodChangeRate"),
                frost=res("resist_freeze", "resistCorrectId_freeze", "registFreezeChangeRate"),
                bloodRate=rate("bloodDamageRate"), frostRate=rate("freezeDamageRate"))


# ---------------------------------------------------------------- hits, status and time-to-kill against a target
TYPE_IDX = {3: 0, 0: 1, 1: 2, 2: 3}       # atkAttribute -> mul index: standard, slash, strike, pierce


def weapon_types(w):
    return [i for i, k in enumerate(("isNormalAttackType", "isSlashAttackType", "isBlowAttackType", "isThrustAttackType")) if w[k]]


def hit_type(w, attr):
    if attr in TYPE_IDX:
        return TYPE_IDX[attr]
    t = weapon_types(w) or [0]
    return t[0] if attr == 253 else (t[1] if len(t) > 1 else t[0])


def prepare(wid, key):
    """-> list of steps (frames, [hit candidates]); each candidate = (mv5, phys type)"""
    w = W[wid]
    base = {"1h": 30000, "2h": 32000, "ps": 34000}[key]   # ps = powerstance / dual L1 (both hands, same weapon)
    steps = chain(w["wepmotionCategory"], base, w["spAtkcategory"])
    out = []
    for cancel, groups in steps:
        hits = []
        for group in groups:
            cands = []
            for j in group:
                b, a = behavior(w["behaviorVariationId"], j)
                if a and not (STRICT and b["stamina"] == 0 and 900 <= j < 1000):   # STRICT: drop stamina-free extra hitboxes (99x)
                    mv = [a["atkPhysCorrection"], a["atkMagCorrection"], a["atkFireCorrection"], a["atkThunCorrection"], a["atkDarkCorrection"]]
                    if sum(mv):
                        cands.append((mv, hit_type(w, a["atkAttribute"])))
            if cands:
                hits.append(cands)
        if not hits:
            return None
        out.append((cancel, hits))
    return out or None


def status_info(wid, stats):
    """bleed / frost buildup per hit and proc effect: {'b': (buildup, rate%, flat), 'f': ...}"""
    w = W[wid]
    lv = max_level(w); rf = RF[w["reinforceTypeId"] + lv]
    out = {}
    for i in range(3):
        sid = w[f"spEffectBehaviorId{i}"]
        if sid <= 0:
            continue
        e = SP.get(sid + rf.get(f"spEffectId{i + 1}", 0)) or SP.get(sid)
        if not e:
            continue
        luck = 1.0
        if stats[4] < w["properLuck"]:                # unmet Arcane: -40% on bleed/poison/etc.
            luck = 0.6
        elif w["correctLuck"] > 0:
            luck += w["correctLuck"] * rf["correctLuckRate"] / 100 * graph(w["correctType_Blood"], stats[4]) / 100
        if e["bloodAttackPower"] > 0:
            out["b"] = (e["bloodAttackPower"] * luck, e["changeHpRate"], e["changeHpPoint"])
        if e["freezeAttackPower"] > 0:
            out["f"] = (e["freezeAttackPower"], e["changeHpRate"], e["changeHpPoint"])
    return out


def thresholds(res):
    base, rcid, area = res
    rc = RC.get(rcid, {})
    return [(base + (rc.get(f"addPoint{min(k, 5)}", 0) if k else 0)) * area for k in range(40)]


def evaluate(wid, stats, key, prep, T):
    """T: target dict (boss() or flat). Returns (effective dps, parts dict)."""
    two = key == "2h"
    AR = ar(wid, stats, two)
    frames = sum(s[0] for s in prep)
    direct = 0; nhits = 0
    for _, hits in prep:
        for cands in hits:
            nhits += 1
            direct += max(sum(eff(AR[e] * mv[e] / 100, T["df"][e]) * (T["mul"][pt if e == 0 else e + 3] if T.get("mul") else 1)
                              for e in range(5)) for mv, pt in cands)
    secs = frames / 60
    d = direct / secs                      # direct dps
    if not T.get("hp"):
        return d, {"direct": d}
    if d <= 0:
        return 0.0, {"direct": 0.0, "ttk": float("inf"), "bleed": 0, "frost": 0}
    st = status_info(wid, stats)
    hp = T["hp"]; rate_hit = nhits / secs
    ev = []
    if "b" in st and T.get("bleed"):
        b, pr, pf = st["b"]; ev.append(["b", b * rate_hit, thresholds(T["bleed"]), (pr / 100 * hp + pf) * T["bloodRate"] / 100])
    if "f" in st and T.get("frost"):
        f, pr, pf = st["f"]; ev.append(["f", f * rate_hit, thresholds(T["frost"]), (pr / 100 * hp + pf) * T["frostRate"] / 100])
    # event simulation with continuous rates
    t = 0.0; left = hp; acc = {e[0]: 0.0 for e in ev}; n = {e[0]: 0 for e in ev}; frost_until = -1
    got = {"b": 0.0, "f": 0.0}
    for _ in range(400):
        amp = 1.2 if t < frost_until else 1.0
        nxt = [((e[2][n[e[0]]] - acc[e[0]]) / e[1], e) for e in ev if e[1] > 0]
        dt_kill = left / (d * amp)
        if frost_until > t:
            dt_kill = min(dt_kill, frost_until - t) if left > d * amp * (frost_until - t) else dt_kill
        tn, e = min(nxt, key=lambda x: x[0]) if nxt else (float("inf"), None)
        step = min(dt_kill, tn)
        left -= d * amp * step; t += step
        for x in ev: acc[x[0]] += x[1] * step
        if left <= 0:
            break
        if e is not None and abs(step - tn) < 1e-9:
            acc[e[0]] = 0; n[e[0]] += 1; left -= e[3]; got[e[0]] += e[3]
            if e[0] == "f": frost_until = t + 30
            if left <= 0:
                break
    return hp / t, {"direct": d, "ttk": t, "bleed": got["b"] / t, "frost": got["f"] / t,
                    "procs_b": n.get("b", 0), "procs_f": n.get("f", 0)}


def flat_target(defense=130):
    return {"df": [defense] * 5, "mul": None, "hp": 0}
