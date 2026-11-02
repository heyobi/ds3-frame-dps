#!/usr/bin/env python3
"""Read-only: dump the dummy points (hitbox anchors) of every DS3 weapon model to JSON.

usage: python3 tools/ds3_models.py "<steam>/DARK SOULS III/Game" data/ds3_weapon_models.json

Looks up /parts/wp_<x>_<nnnn>.partsbnd.dcx in the encrypted archives (nothing is written to the game folder),
decompresses it, finds the .flver inside and reads its dummy list: reference id, position, parent and attach bone.
AtkParam hitboxes are spheres / capsules placed on these dummies, so dummy position + hit radius = reach.
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAME, OUT = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], GAME]           # ds3_frames reads the game path from argv
sys.path.insert(0, HERE)
import ds3_frames as F


def flver_dummies(d):
    """FLVER2: header 0x80 bytes, then dummies (0x40 bytes each). Returns dummies, bones (name, parent, translation)."""
    assert d[:6] == b"FLVER\0", d[:8]
    E = "<" if d[6:8] == b"L\0" else ">"
    version, data_off, data_len, n_dummy, n_mat, n_bone = struct.unpack_from(E + "6i", d, 0x08)
    dummies = []
    for k in range(n_dummy):
        o = 0x80 + k * 0x40
        x, y, z = struct.unpack_from(E + "3f", d, o)
        fx, fy, fz = struct.unpack_from(E + "3f", d, o + 0x10)
        ref, parent = struct.unpack_from(E + "2h", d, o + 0x1C)
        attach = struct.unpack_from(E + "h", d, o + 0x2C)[0]
        dummies.append([ref, round(x, 4), round(y, 4), round(z, 4), parent, attach, round(fx, 3), round(fy, 3), round(fz, 3)])
    # bones come after dummies and materials (material = 0x20 bytes); bone = 0x80 bytes starting with translation
    bones = []
    bo = 0x80 + n_dummy * 0x40 + n_mat * 0x20
    for k in range(n_bone):
        o = bo + k * 0x80
        tx, ty, tz = struct.unpack_from(E + "3f", d, o)
        parent = struct.unpack_from(E + "h", d, o + 0x10)[0]
        bones.append([round(tx, 4), round(ty, 4), round(tz, 4), parent])
    return dict(version=version, dummies=dummies, bones=bones)


entries = {}
for arc in ["DLC2", "DLC1", "Data5", "Data4", "Data3", "Data2", "Data1"]:
    bhd_p = os.path.join(GAME, arc + ".bhd")
    if not os.path.exists(bhd_p):
        continue
    raw = open(bhd_p, "rb").read()
    bhd = raw if raw[:4] == b"BHD5" else F.rsa_decrypt_file(bhd_p, F.KEYS[arc])
    entries[arc] = F.bhd_entries(bhd)
    print(f"# {arc}: {len(entries[arc])} files", file=sys.stderr)

out, errors = {}, {}
for letter in "abcd":
    for n in range(10000):
        path = f"/parts/wp_{letter}_{n:04d}.partsbnd.dcx"
        h = F.hash_path(path)
        arc = next((a for a in entries if h in entries[a]), None)   # first hit = newest archive (DLC first)
        if not arc:
            continue
        try:
            data = F.dcx(F.bdt_read(os.path.join(GAME, arc + ".bdt"), entries[arc][h]))
            for _, name, body in F.bnd4(data):
                if name.lower().endswith(".flver"):
                    out[f"{letter}_{n:04d}"] = dict(arc=arc, file=name.replace("\\", "/").split("/")[-1], **flver_dummies(body))
                    break
        except Exception as e:      # keep going; report at the end
            errors[path] = repr(e)
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
json.dump(dict(models=out, errors=errors), open(OUT, "w"), separators=(",", ":"))
print(f"{len(out)} weapon models, {len(errors)} errors -> {OUT}")
