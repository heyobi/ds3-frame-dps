#!/usr/bin/env python3
"""Read-only: dump the root motion (forward step) of every DS3 player attack animation to JSON.

usage: python3 tools/ds3_rootmotion.py "<steam>/DARK SOULS III/Game" data/ds3_rootmotion.json
   or: python3 tools/ds3_rootmotion.py --files c0000_a2x.anibnd.dcx [...] --out data/ds3_rootmotion.json

Player animations live in /chr/c0000_a0x..a9x and c0000_dlc1/2 .anibnd.dcx. For every animation a<tae>_<id>.hkx with
id 30000-49999 (light / heavy / dual attacks), the hkaDefaultAnimatedReferenceFrame samples are read
(tools/hkx_rootmotion.py) and stored as forward distance per sample (metres, 30 per second).
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ap = argparse.ArgumentParser()
ap.add_argument("game", nargs="?")
ap.add_argument("out", nargs="?", default="data/ds3_rootmotion.json")
ap.add_argument("--files", nargs="*")
ap.add_argument("--out", dest="out2")
a = ap.parse_args()
_argv = sys.argv; sys.argv = [sys.argv[0], a.game or "/none"]
import ds3_frames as F
sys.argv = _argv
import hkx_rootmotion as H

PACKS = [f"/chr/c0000_a{k}x.anibnd.dcx" for k in range(10)] + ["/chr/c0000_dlc1.anibnd.dcx", "/chr/c0000_dlc2.anibnd.dcx"]
blobs = []
if a.files:
    blobs = [(p, open(p, "rb").read()) for p in a.files]
else:
    for p in PACKS:
        try:
            blobs.append((p, F.find_file(p)))
        except SystemExit as e:
            print(f"# skip {p}: {e}", file=sys.stderr)

out = {}
for p, raw in blobs:
    n = 0
    for _, name, body in F.bnd4(F.dcx(raw)):
        base = name.replace("\\", "/").split("/")[-1].lower()
        if not (base.startswith("a") and base.endswith(".hkx") and "_" in base):
            continue
        try:
            aid = int(base[5:11])
        except ValueError:
            continue
        if not 30000 <= aid < 50000:
            continue
        r = H.root_motion(body)
        if not r:
            continue
        dur, smp = r
        out[base[:-4]] = [round(dur, 3), [round(-s[2], 3) for s in smp], [round(s[0], 3) for s in smp]]
        n += 1
    print(f"# {p}: {n} attack animations", file=sys.stderr)
dst = a.out2 or a.out
json.dump(out, open(dst, "w"), separators=(",", ":"))
print(f"{len(out)} animations -> {dst}")
