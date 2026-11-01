"""Load Elden Ring params + TAE into python structures (scratch)."""
import sys, os, struct, pickle
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools")); _a = sys.argv; sys.argv = sys.argv[:1]
import ds3_frames as F, param_reader as P
sys.argv = _a
FD = os.environ.get("ER_FILES", "er_files")   # c0000.anibnd + params/ from tools/er_extract.py
PDX = os.environ.get("PARAMDEX_ER", "Paramdex/ER")
files = {f.rsplit('.', 1)[0]: open(f"{FD}/params/" + f, 'rb').read() for f in os.listdir(f"{FD}/params")}
P.setup(PDX, files)
out = {}
for f, t in [("EquipParamWeapon", "EquipParamWeapon"), ("BehaviorParam_PC", "BehaviorParam"), ("AtkParam_Pc", "AtkParam"),
             ("ReinforceParamWeapon", "ReinforceParamWeapon"), ("CalcCorrectGraph", "CalcCorrectGraph"),
             ("AttackElementCorrectParam", "AttackElementCorrectParam"), ("NpcParam", "NpcParam"), ("SpEffectParam", "SpEffect"), ("ResistCorrectParam", "ResistCorrectParam")]:
    out[f] = P.read_param(f, t)[0]
out["names_w"] = P.names("EquipParamWeapon"); out["names_npc"] = P.names("NpcParam")
raw = open(f"{FD}/c0000.anibnd", "rb").read()
T = {}
for _, n, d in F.bnd4(raw):
    if n.lower().endswith(".tae") and d[:4] == b"TAE ":
        tid, res = F.tae_events(d); T[tid] = res
out["tae"] = T; out["refs"] = dict(F.REFS); out["atkargs"] = dict(F.ATKARGS); out["atklist"] = dict(F.ATKLIST)
pickle.dump(out, open(f"{FD}/er.pkl", "wb"))
print({k: len(v) for k, v in out.items()})
