#!/usr/bin/env python3
"""Read the root motion (how far the character moves) from a Havok 2014 packfile animation (DS3 .hkx).

The animation's hkaDefaultAnimatedReferenceFrame holds referenceFrameSamples: one (x, y, z, yaw) vector per sample
over the animation's duration. Only that object is read; bone tracks are not decoded.
"""
import struct


def sections(d):
    assert d[:8] == b"\x57\xe0\xe0\x57\x10\xc0\xc0\x10", d[:8]
    ver = struct.unpack_from("<i", d, 0x0C)[0]
    nsec = struct.unpack_from("<i", d, 0x14)[0]
    hdr = 0x40
    if ver >= 11:                       # extra header block (predicates)
        hdr += struct.unpack_from("<h", d, 0x3E)[0]
    secs = {}
    for i in range(nsec):
        o = hdr + i * (0x40 if ver >= 11 else 0x30)
        name = d[o:o + 20].split(b"\0")[0].decode()
        start, loc, glo, virt, exp, imp, end = struct.unpack_from("<7i", d, o + 20)
        secs[name] = dict(start=start, loc=loc, glo=glo, virt=virt, exp=exp, imp=imp, end=end)
    return secs


def objects(d):
    """[(class name, absolute offset)] and local fixups {absolute pointer location: absolute target}"""
    s = sections(d)
    cn, data = s["__classnames__"], s["__data__"]
    a = data["start"]
    local = {}
    for o in range(a + data["loc"], a + data["glo"] - 7, 8):
        src, dst = struct.unpack_from("<ii", d, o)
        if src != -1:
            local[a + src] = a + dst
    objs = []
    for o in range(a + data["virt"], a + data["exp"] - 11, 12):
        src, sec, name_off = struct.unpack_from("<iii", d, o)
        if src == -1:
            continue
        nm = d[cn["start"] + name_off:].split(b"\0")[0].decode()
        objs.append((nm, a + src))
    return objs, local


def root_motion(d):
    """-> (duration s, [(x, y, z, yaw), ...]) or None"""
    objs, local = objects(d)
    for nm, o in objs:
        if nm != "hkaDefaultAnimatedReferenceFrame":
            continue
        # 64-bit layout: hkReferencedObject 0x10, frameType 0x10, up 0x20, forward 0x30, duration 0x40,
        # referenceFrameSamples hkArray at 0x48 (ptr, size, capacity|flags)
        duration = struct.unpack_from("<f", d, o + 0x40)[0]
        n = struct.unpack_from("<i", d, o + 0x50)[0]
        p = local.get(o + 0x48)
        if p is None or n <= 0:
            return duration, []
        return duration, [struct.unpack_from("<4f", d, p + 16 * i) for i in range(n)]
    return None
