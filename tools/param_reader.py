"""Minimal reader for DS3 .param files, field layout from Paramdex (github.com/soulsmods/Paramdex) XML defs.

Call setup(paramdex_dir, files) first: files maps "NpcParam" -> raw bytes of NpcParam.param."""
import re, struct, os, html
DEFS = None
FILES = {}


def setup(paramdex_ds3_dir, files):
    global DEFS, FILES
    DEFS = os.path.join(paramdex_ds3_dir, "Defs"); FILES = files
SZ = {"s8": ("b", 1), "u8": ("B", 1), "s16": ("h", 2), "u16": ("H", 2), "s32": ("i", 4), "u32": ("I", 4), "f32": ("f", 4)}

def load_def(paramtype):
    s = open(os.path.join(DEFS, paramtype + ".xml"), encoding="utf-8-sig").read()
    out = []
    for d in re.findall(r'<Field Def="([^"]+)"', s):
        d = re.sub(r"\[[A-Za-z_]\w*\]", "", html.unescape(d).split("=")[0]).strip()
        m = re.match(r"(\w+)\s+([^\[:]+?)\s*(?:\[(\d+)\])?\s*(?::\s*(\d+))?$", d)
        t, name, n, bits = m.group(1), m.group(2).strip(), m.group(3), m.group(4)
        out.append((t, name, int(n) if n else None, int(bits) if bits else None))
    return out

def parse_row(defs, d, off):
    row = {}; p = off; bit_t = None; bit_pos = 0; bit_val = 0
    for t, name, n, bits in defs:
        if bits is not None and t in SZ:
            fmt, sz = SZ[t]
            if bit_t != t or bit_pos + bits > sz * 8:
                if bit_t is not None: p += SZ[bit_t][1]
                bit_t, bit_pos = t, 0
                bit_val = struct.unpack_from("<" + fmt.upper(), d, p)[0]
            row[name] = (bit_val >> bit_pos) & ((1 << bits) - 1); bit_pos += bits
            continue
        if bit_t is not None: p += SZ[bit_t][1]; bit_t = None
        if t == "dummy8":
            if bits is not None:   # dummy8 bitfield padding
                bit_t = "u8"; bit_pos = bits; continue
            p += n or 1; continue
        if t == "fixstr": p += n; continue
        if t == "fixstrW": p += 2 * n; continue
        fmt, sz = SZ[t]
        if n:
            row[name] = list(struct.unpack_from("<" + fmt * n, d, p)); p += sz * n
        else:
            row[name] = struct.unpack_from("<" + fmt, d, p)[0]; p += sz
    if bit_t is not None: p += SZ[bit_t][1]
    return row, p - off

def read_param(fname, paramtype):
    d = FILES[fname]
    f2d = d[0x2D]; nrows = struct.unpack_from("<H", d, 0x0A)[0]
    idx = []
    for r in range(nrows):
        if f2d & 4: rid, _, doff, _ = struct.unpack_from("<iiqq", d, 0x40 + r * 24)
        else:
            base = 0x40 if (f2d & 3) == 3 else 0x30
            rid, doff, _ = struct.unpack_from("<iII", d, base + r * 12)
        idx.append((rid, doff))
    defs = load_def(paramtype)
    rows = {}
    size = None
    for rid, doff in idx:
        rows[rid], size = parse_row(defs, d, doff)
    real = idx[1][1] - idx[0][1] if len(idx) > 1 else None
    return rows, size, real

def names(fname):
    out = {}
    p = os.path.join(os.path.dirname(DEFS), "Names", fname + ".txt")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8-sig"):
            k, _, v = line.strip().partition(" ")
            if k.lstrip("-").isdigit(): out[int(k)] = v
    return out
