import sys, os, json, random, subprocess
sys.path.insert(0, ".")
import er_model as M
random.seed(int(sys.argv[1]) if len(sys.argv)>1 else 7)
refnames = {w["name"] for w in json.load(open(os.environ.get("ER_CALC", "elden-ring-weapon-calculator") + "/public/regulation-vanilla-v1.17.js"))["weapons"]}
ids = [i for i, w in M.W.items() if M.N.get(i) in refnames and w.get("wepmotionCategory", 0) and M.max_level(w) > 0]
print("candidate ids", len(ids))
cases, meta = [], []
for i in random.sample(ids, min(400, len(ids))):
    st = [random.randint(10, 80) for _ in range(5)]
    th = random.random() < 0.5
    for lv in (M.max_level(M.W[i]), 0):
        cases.append(dict(name=M.N[i], stats=st, th=th, up=lv)); meta.append((i, st, th, lv))
json.dump(cases, open("/tmp/er_ar_cases.json", "w"))
ref = json.loads(subprocess.check_output(["node", "--experimental-strip-types", "--no-warnings", os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate_ar_ref.ts"),
                                          "/tmp/er_ar_cases.json"]))
bad = 0; n = 0
for (i, st, th, lv), r in zip(meta, ref):
    if r is None: continue
    ours = M.ar(i, st, th, lv)
    # requirement penalty as in reference: 0.6 if any requirement unmet (after 2H)
    theirs = [r.get(str(k), 0) for k in range(5)]
    n += 1
    if any(abs(a - b) > 0.6 for a, b in zip(ours, theirs)):
        bad += 1
        if bad <= 15: print(M.N[i], lv, st, th, [round(x,1) for x in ours], [round(x,1) for x in theirs], "meets", M.meets(i, st, th))
print("compared", n, "mismatch", bad)
# status buildup at max level (lv == max cases only)
sb = 0; sn = 0
for (i, st, th, lv), r in zip(meta, ref):
    if r is None or lv != M.max_level(M.W[i]): continue
    s = M.status_info(i, st)
    for k, idx in (("b", "7"), ("f", "8")):
        a = s.get(k, (0,))[0]; b = r.get(idx, 0)
        if a or b:
            sn += 1
            if abs(a - b) > 0.6:
                sb += 1
                if sb <= 8: print("status", M.N[i], k, round(a, 1), round(b, 1))
print("status compared", sn, "mismatch", sb)
