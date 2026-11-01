#!/usr/bin/env python3
"""DS3: read c0000.anibnd TAE (attack + cancel frames) and EquipParamWeapon motion categories. Read-only."""
KEYS = {
    'Data1': '-----BEGIN RSA PUBLIC KEY-----\nMIIBCwKCAQEA05hqyboW/qZaJ3GBIABFVt1X1aa0/sKINklvpkTRC+5Ytbxvp18L\nM1gN6gjTgSJiPUgdlaMbptVa66MzvilEk60aHyVVEhtFWy+HzUZ3xRQm6r/2qsK3\n8wXndgEU5JIT2jrBXZcZfYDCkUkjsGVkYqjBNKfp+c5jlnNwbieUihWTSEO+DA8n\naaCCzZD3e7rKhDQyLCkpdsGmuqBvl02Ou7QeehbPPno78mOYs2XkP6NGqbFFGQwa\nswyyyXlQ23N15ZaFGRRR0xYjrX4LSe6OJ8Mx/Zkec0o7L28CgwCTmcD2wO8TEATE\nAUbbV+1Su9uq2+wQxgnsAp+xzhn9og9hmwIEC35bSQ==\n-----END RSA PUBLIC KEY-----',
    'Data2': '-----BEGIN RSA PUBLIC KEY-----\nMIIBCwKCAQEAvCZAK9UfPdk5JaTlG7n1r0LSVzIan3h0BSLaMXQHOwO7tTGpvtdX\nm2ZLY9y8SVmOxWTQqRq14aVGLTKDyH87hPuKd47Y0E5K5erTqBbXW6AD4El1eir2\nVJz/pwHt73FVziOlAnao1A5MsAylZ9B5QJyzHJQG+LxzMzmWScyeXlQLOKudfiIG\n0qFw/xhRMLNAI+iypkzO5NKblYIySUV5Dx7649XdsZ5UIwJUhxONsKuGS+MbeTFB\nmTMehtNj5EwPxGdT4CBPAWdeyPhpoHJHCbgrtnN9akwQmpwdBBxT/sTD16Adn9B+\nTxuGDQQALed4S4KvM+fadx27pQz8pP9VLwIEL67iCQ==\n-----END RSA PUBLIC KEY-----',
    'Data3': '-----BEGIN RSA PUBLIC KEY-----\nMIIBCwKCAQEAqLytWD20TSXPeAA1RGDwPW18nJwe2rBX+0HPtdzFmQc/KmQlWrP+\n94k6KClK5f7m0xUHwT8+yFGLxPdRvUPyOhBEnRA6tkObVDSxij5y0Jh4h4ilAO73\nI8VMcmscS71UKkck4444+eR4vVd+SPlzIu8VgqLefvEn/sX/pAevDp7w+gD0NgvO\ne9U6iWEXKwTOPB97X+Y2uB03gSSognmV8h2dtUFJ4Ryn5jrpWmsuUbdvGp0CWBKH\nCFruNXnfsG0hlf9LqbVmEzbFl/MhjBmbVjjtelorZsoLPK+OiPTHW5EcwwnPh1vH\nFFGM7qRMc0yvHqJnniEWDsSz8Bvg+GxpgQIEC8XNVw==\n-----END RSA PUBLIC KEY-----',
    'Data4': '-----BEGIN RSA PUBLIC KEY-----\nMIIBCwKCAQEArfUaZWjYAUaZ0q+5znpX55GeyepawCZ5NnsMjIW9CA3vrOgUGRkh\n6aAU9frlafQ81LQMRgAznOnQGE7K3ChfySDpq6b47SKm4bWPqd7Ulh2DTxIgi6QP\nqm4UUJL2dkLaCnuoya/pGMOOvhT1LD/0CKo/iKwfBcYf/OAnwSnxMRC3SNRugyvF\nylCet9DEdL5L8uBEa4sV4U288ZxZSZLg2tB10xy5SHAsm1VNP4Eqw5iJbqHEDKZW\nn2LJP5t5wpEJvV2ACiA4U5fyjQLDzRwtCKzeK7yFkKiZI95JJhU/3DnVvssjIxku\ngYZkS9D3k9m+tkNe0VVrd4mBEmqVxg+V9wIEL6Y6tw==\n-----END RSA PUBLIC KEY-----',
    'Data5': '-----BEGIN RSA PUBLIC KEY-----\nMIIBCwKCAQEAvKTlU3nka4nQesRnYg1NWovCCTLhEBAnjmXwI69lFYfc4lvZsTrQ\nE0Y25PtoP0ZddA3nzflJNz1rBwAkqfBRGTeeTCAyoNp/iel3EAkid/pKOt3JEkHx\nrojRuWYSQ0EQawcBbzCfdLEjizmREepRKHIUSDWgu0HTmwSFHHeCFbpBA1h99L2X\nizH5XFTOu0UIcUmBLsK6DYsIj5QGrWaxwwXcTJN/X+/syJ/TbQK9W/TCGaGiirGM\n1u2wvZXSZ7uVM3CHwgNhAMiqLvqORygcDeNqxgq+dXDTxka43j7iPJWdHs8b25fy\naH3kbUxKlDGaEENNNyZQcQrgz8Q76jIE0QIEFUsz9w==\n-----END RSA PUBLIC KEY-----',
    'DLC1': '-----BEGIN RSA PUBLIC KEY-----\nMIIBCwKCAQEAsCGM9dFwzaIOUIin3DXy7xrmI2otKGLZJQyKi5X3znKhSTywpcFc\nKoW6hgjeh4fJW24jhzwBosG6eAzDINm+K02pHCG8qZ/D/hIbu+ui0ENDKqrVyFhn\nQtX5/QJkVQtj8M4a0FIfdtE3wkxaKtP6IXWIy4DesSdGWONVWLfi2eq62A5ts5MF\nqMoSV3XjTYuCgXqZQ6eOE+NIBQRqpZxLNFSzbJwWXpAg2kBMkpy5+ywOByjmWzUw\njnIFl1T17R8DpTU/93ojx+/q1p+b1o5is5KcoP7QwjOqzjHJH8bTytzRbgmRcDMW\n3ahxgI070d45TMXK2YwRzI6/JbM1P29anQIEFezyYw==\n-----END RSA PUBLIC KEY-----',
    'DLC2': '-----BEGIN RSA PUBLIC KEY-----\nMIIBCwKCAQEAtCXU9a/GBMVoqtpQox9p0/5sWPaIvDp8avLFnIBhN7vkgTwulZHi\nu64vZAiUAdVeFX4F+Qtk+5ivK488Mu2CzAMJcz5RvyMQJtOQXuDDqzIv21Tr5zuu\nsswoErHxxP8TZNxkHm7Ram7Oqtn7LQnMTYxsBgZZ34yJkRtAmZnGoCu5YaUR5euk\n8lF75idi97ssczUNV212tLzIMa1YOV7sxOb7+gc0VTIqs3pa+OXLPI/bMfwUc/KN\njur5aLDDntQHGx5zuNtc78gMGwlmPqDhgTusKPO4VyKvoL0kITYvukoXJATaa1HI\nWVUjhLm+/uj8r8PNgolerDeS+8FM5Bpe9QIEHwCZLw==\n-----END RSA PUBLIC KEY-----',
}

import base64, os, struct, sys, zlib

GAME = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.steam/steam/steamapps/common/DARK SOULS III/Game")
MODE = sys.argv[2] if len(sys.argv) > 2 else "discover"
OUT = sys.argv[3] if len(sys.argv) > 3 else None

# ---------------- AES (cryptography if present, else pure python) ----------------
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    def aes_ecb_dec(key, data):
        d = Cipher(algorithms.AES(key), modes.ECB()).decryptor(); return d.update(data) + d.finalize()
    def aes_cbc_dec(key, iv, data):
        d = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor(); return d.update(data) + d.finalize()
except ImportError:
    SB = [0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16]
    ISB = [0] * 256
    for i, v in enumerate(SB): ISB[v] = i
    def _xt(a): return ((a << 1) ^ 0x1b) & 0xff if a & 0x80 else a << 1
    def _mul(a, b):
        r = 0
        while b:
            if b & 1: r ^= a
            a = _xt(a); b >>= 1
        return r
    M9 = [_mul(i, 9) for i in range(256)]; M11 = [_mul(i, 11) for i in range(256)]
    M13 = [_mul(i, 13) for i in range(256)]; M14 = [_mul(i, 14) for i in range(256)]
    def _expand(key):
        nk = len(key) // 4; nr = nk + 6
        w = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
        rcon = 1
        for i in range(nk, 4 * (nr + 1)):
            t = list(w[i - 1])
            if i % nk == 0:
                t = t[1:] + t[:1]; t = [SB[b] for b in t]; t[0] ^= rcon; rcon = _xt(rcon)
            elif nk > 6 and i % nk == 4:
                t = [SB[b] for b in t]
            w.append([w[i - nk][j] ^ t[j] for j in range(4)])
        return [sum(w[4 * r:4 * r + 4], []) for r in range(nr + 1)], nr
    _cache = {}
    def _dec_block(rk, nr, b):
        s = [b[i] ^ rk[nr][i] for i in range(16)]
        for rnd in range(nr - 1, -1, -1):
            s = [s[0], s[13], s[10], s[7], s[4], s[1], s[14], s[11], s[8], s[5], s[2], s[15], s[12], s[9], s[6], s[3]]
            s = [ISB[x] for x in s]
            s = [s[i] ^ rk[rnd][i] for i in range(16)]
            if rnd:
                n = []
                for c in range(4):
                    a0, a1, a2, a3 = s[4 * c:4 * c + 4]
                    n += [M14[a0] ^ M11[a1] ^ M13[a2] ^ M9[a3], M9[a0] ^ M14[a1] ^ M11[a2] ^ M13[a3],
                          M13[a0] ^ M9[a1] ^ M14[a2] ^ M11[a3], M11[a0] ^ M13[a1] ^ M9[a2] ^ M14[a3]]
                s = n
        return bytes(s)
    def _rk(key):
        if key not in _cache: _cache[key] = _expand(key)
        return _cache[key]
    def aes_ecb_dec(key, data):
        rk, nr = _rk(key)
        return b"".join(_dec_block(rk, nr, data[i:i + 16]) for i in range(0, len(data), 16))
    def aes_cbc_dec(key, iv, data):
        rk, nr = _rk(key); out = []; prev = iv
        for i in range(0, len(data), 16):
            blk = data[i:i + 16]; d = _dec_block(rk, nr, blk)
            out.append(bytes(x ^ y for x, y in zip(d, prev))); prev = blk
        return b"".join(out)

# ---------------- RSA (BHD headers) ----------------
def der_rsa_pub(pem):
    b = base64.b64decode("".join(l for l in pem.strip().splitlines() if "-----" not in l))
    def tlv(p):
        tag = b[p]; ln = b[p + 1]; p += 2
        if ln & 0x80:
            k = ln & 0x7f; ln = int.from_bytes(b[p:p + k], "big"); p += k
        return tag, p, ln
    _, p, _ = tlv(0)
    _, p, ln = tlv(p); n = int.from_bytes(b[p:p + ln], "big"); p += ln
    _, p, ln = tlv(p); e = int.from_bytes(b[p:p + ln], "big")
    return n, e

def rsa_decrypt_file(path, pem):
    n, e = der_rsa_pub(pem); k = (n.bit_length() + 7) // 8
    data = open(path, "rb").read(); out = bytearray()
    for i in range(0, len(data), k):
        c = int.from_bytes(data[i:i + k], "big")
        out += pow(c, e, n).to_bytes(k - 1, "big")
    return bytes(out)

# ---------------- BHD5 / BDT ----------------
def hash_path(p):
    p = p.strip().replace("\\", "/").lower()
    if not p.startswith("/"): p = "/" + p
    h = 0
    for ch in p: h = (h * 37 + ord(ch)) & 0xFFFFFFFF
    return h

def bhd_entries(bhd):
    assert bhd[:4] == b"BHD5", bhd[:16]
    bucket_count, buckets_off = struct.unpack_from("<ii", bhd, 0x10)
    ents = {}
    for bi in range(bucket_count):
        cnt, off = struct.unpack_from("<ii", bhd, buckets_off + bi * 8)
        for j in range(cnt):
            o = off + j * 0x28
            h, padded, foff, sha_off, aes_off, unpadded = struct.unpack_from("<IiqqqQ", bhd, o)
            aes = None
            if aes_off:
                key = bhd[aes_off:aes_off + 16]; rc = struct.unpack_from("<i", bhd, aes_off + 16)[0]
                ranges = [struct.unpack_from("<qq", bhd, aes_off + 20 + 16 * r) for r in range(rc)]
                aes = (key, ranges)
            ents[h] = (padded, foff, aes, unpadded)
    return ents

def bdt_read(bdt_path, ent):
    padded, foff, aes, unpadded = ent
    with open(bdt_path, "rb") as f:
        f.seek(foff); data = bytearray(f.read(padded))
    if aes:
        key, ranges = aes
        for s, e in ranges:
            if s != -1 and e != -1 and s != e:
                data[s:e] = aes_ecb_dec(key, bytes(data[s:e]))
    return bytes(data[:unpadded]) if unpadded > 0 else bytes(data)

def find_file(path):
    h = hash_path(path)
    for arc in ["DLC2", "DLC1", "Data5", "Data4", "Data3", "Data2", "Data1"]:
        bhd_p = os.path.join(GAME, arc + ".bhd"); bdt_p = os.path.join(GAME, arc + ".bdt")
        if not os.path.exists(bhd_p): continue
        raw = open(bhd_p, "rb").read()
        bhd = raw if raw[:4] == b"BHD5" else rsa_decrypt_file(bhd_p, KEYS[arc])
        ents = bhd_entries(bhd)
        if h in ents:
            print(f"# {path} -> {arc}", file=sys.stderr)
            return bdt_read(bdt_p, ents[h])
    raise SystemExit(f"not found: {path}")

def dcx(data):
    if data[:4] != b"DCX\0": return data
    i = data.index(b"DCA\0"); hl = struct.unpack_from(">i", data, i + 4)[0]
    fmt = data[0x28:0x2C]
    if fmt != b"DFLT": raise SystemExit(f"unsupported DCX {fmt}")
    return zlib.decompress(data[i + hl:])

def bnd4(data):
    assert data[:4] == b"BND4", data[:4]
    big = data[9] == 1
    E = ">" if big else "<"
    nfiles = struct.unpack_from(E + "i", data, 0x0C)[0]
    hdr_size = struct.unpack_from(E + "q", data, 0x20)[0]
    unicode = data[0x30] == 1
    raw = data[0x31]; bitbig = data[10] == 0
    fmt = raw if (bitbig or (raw & 1 and not raw & 0x80)) else int(f"{raw:08b}"[::-1], 2)
    ids, names1, names2, long_off, comp = fmt & 2, fmt & 4, fmt & 8, fmt & 0x10, fmt & 0x20
    files = []
    for k in range(nfiles):
        o = 0x40 + k * hdr_size
        p = o + 8
        csize = struct.unpack_from(E + "q", data, p)[0]; p += 8
        if comp: p += 8
        if long_off: off = struct.unpack_from(E + "q", data, p)[0]; p += 8
        else: off = struct.unpack_from(E + "I", data, p)[0]; p += 4
        fid = -1
        if ids: fid = struct.unpack_from(E + "i", data, p)[0]; p += 4
        name = ""
        if names1 or names2:
            no = struct.unpack_from(E + "I", data, p)[0]
            if unicode:
                end = no
                while data[end:end + 2] != b"\0\0": end += 2
                name = data[no:end].decode("utf-16-le")
            else:
                name = data[no:data.index(b"\0", no)].decode("shift_jis", "replace")
        files.append((fid, name, data[off:off + csize]))
    return files

# ---------------- TAE3 ----------------
REFS = {}
ATKARGS = {}   # (tae, anim, start frame) -> first three s32 args of AttackBehavior (incl. behavior judge id)
ATKLIST = {}   # (tae, anim) -> [(start frame, end frame, args)] for every AttackBehavior (no collisions on equal frames)

def tae_events(t):
    assert t[:4] == b"TAE ", t[:4]
    tid, nanims, anims_off = struct.unpack_from("<iiq", t, 0x50)
    res = {}
    for a in range(nanims):
        aid, aoff = struct.unpack_from("<qq", t, anims_off + a * 16)
        ev_off, grp_off, times_off, file_off, nev = struct.unpack_from("<qqqqi", t, aoff)
        evs = []
        for k in range(nev):
            s_off, e_off, d_off = struct.unpack_from("<qqq", t, ev_off + k * 24)
            st = struct.unpack_from("<f", t, s_off)[0]; en = struct.unpack_from("<f", t, e_off)[0]
            etype = struct.unpack_from("<q", t, d_off)[0]
            arg = struct.unpack_from("<i", t, d_off + 16)[0] if etype in (0, 1) else None
            if etype == 1:
                ATKARGS[(tid, aid, round(st * 60))] = struct.unpack_from("<iii", t, d_off + 16)
                ATKLIST.setdefault((tid, aid), []).append((round(st * 60), round(en * 60), struct.unpack_from("<iii", t, d_off + 16)))
            evs.append((etype, st, en, arg))
        ref_flag, _, _, imp, unk1c = struct.unpack_from("<qqqii", t, file_off)
        res[aid] = evs
        REFS[(tid, aid)] = (ref_flag, imp, unk1c)
    return tid, res

# ---------------- regulation / EquipParamWeapon ----------------
def weapon_motion_categories():
    raw = open(os.path.join(GAME, "Data0.bdt"), "rb").read()
    body = raw[16:]; body = body[:len(body) // 16 * 16]
    dec = aes_cbc_dec(b"ds3#jn/8_7(rsY9pg55GFN7VFL#+3n/)", raw[:16], body)
    bnd = bnd4(dcx(dec))
    for fid, name, d in bnd:
        if name.replace("\\", "/").lower().endswith("/equipparamweapon.param"):
            f2d = d[0x2D]
            nrows = struct.unpack_from("<H", d, 0x0A)[0]
            rows = []
            for r in range(nrows):
                if f2d & 4:
                    rid, _, doff, _ = struct.unpack_from("<iiqq", d, 0x40 + r * 24)
                else:
                    base = 0x40 if (f2d & 3) == 3 else 0x30
                    rid, doff, _ = struct.unpack_from("<iII", d, base + r * 12)
                rows.append((rid, doff))
            size = rows[1][1] - rows[0][1]
            print(f"# EquipParamWeapon rows={nrows} rowsize={size} fmt2d={f2d:#x}", file=sys.stderr)
            return {rid: (d[doff + 227], d[doff + 236], d[doff + 237], round(struct.unpack_from("<f", d, doff + 12)[0], 1), struct.unpack_from("<h", d, doff + 234)[0]) for rid, doff in rows}
    raise SystemExit("EquipParamWeapon not found")

def ev_summary(evs):
    atk = sorted(round(s * 60) for t, s, e, a in evs if t == 1)
    rh = sorted(round(s * 60) for t, s, e, a in evs if t == 0 and a == 4)
    lh = sorted(round(s * 60) for t, s, e, a in evs if t == 0 and a == 16)
    return atk, rh, lh

if __name__ == "__main__":
    ani = bnd4(dcx(find_file("/chr/c0000.anibnd.dcx")))
    taes_all = [(n, d) for _, n, d in ani if n.lower().endswith(".tae")]
    taes = [(n, d) for n, d in taes_all if d[:4] == b"TAE "]
    print(f"# files={len(ani)} tae={len(taes_all)} nonempty={len(taes)} sizes0={sum(1 for n, d in taes_all if len(d) == 0)} other_magic={[d[:4] for n, d in taes_all if d and d[:4] != b'TAE '][:3]}", file=sys.stderr)
    lines = []
    if MODE == "discover":
        lines.append("TAEs: " + " ".join(os.path.basename(n.replace("\\", "/")) for n, _ in taes))
        for n, d in taes:
            tid, res = tae_events(d)
            ids = sorted(a for a in res if 30000 <= a % 1000000 < 40000 and any(e[0] == 1 for e in res[a]))
            if ids:
                lines.append(f"{os.path.basename(n)} n={len(ids)} " + ",".join(str(i % 1000000) for i in ids[:60]))
        cats = weapon_motion_categories()
        lines.append("W " + " ".join(f"{k // 10000}:{v[0]}:{v[1]}:{v[2]}:{v[3]}:{v[4]}" for k, v in sorted(cats.items()) if k % 10000 == 0 and k < 30000000))
    elif MODE == "flags":
        # Parry / defensive frame data: every animation that has ChrActionFlag 5 ("Parry Possible") anywhere,
        # plus the same animation id in every other TAE (they may import it). All type-0 flags are listed.
        parsed = [(os.path.basename(n.replace("\\", "/"))[:-4],) + tae_events(d) for n, d in taes]
        # AttackBehavior (type 1) with AttackType 64 = "Parry" is the parry window; ChrActionFlag 5 marks the
        # frames in which an attack can be parried by the opponent.
        ids = {aid % 1000000 for _, tid, res in parsed for aid, evs in res.items()
               if any(e[0] == 1 and ATKARGS.get((tid, aid, round(e[1] * 60)), (0,))[0] == 64 for e in evs)}
        lines.append("PARRY_IDS " + ",".join(map(str, sorted(ids))))
        for short, tid, res in parsed:
            for aid in sorted(res):
                if aid % 1000000 not in ids:
                    continue
                fl = "/".join(f"{a}:{round(st * 60)}-{round(en * 60)}" for t, st, en, a in res[aid] if t == 0)
                pw = "/".join(f"{round(st * 60)}-{round(en * 60)}" for t, st, en, a in res[aid]
                              if t == 1 and ATKARGS.get((tid, aid, round(st * 60)), (0,))[0] == 64)
                rf = REFS.get((tid, aid), (0, 0, 0))
                lines.append(f"{short}|{aid % 1000000}|{pw}|{fl}|{rf[0]}:{rf[1]}:{rf[2]}")
        cats = weapon_motion_categories()
        lines.append("W " + " ".join(f"{k // 10000}:{v[0]}:{v[1]}:{v[2]}:{v[4]}" for k, v in sorted(cats.items()) if k % 10000 == 0 and k < 30000000))
    else:
        KEEP = {30000, 30010, 30020, 30030, 32000, 32010, 32020, 33000, 33010, 33020, 33030, 34000, 34010, 34020, 34030}
        for n, d in taes:
            tid, res = tae_events(d)
            short = os.path.basename(n.replace("\\", "/"))
            for aid in sorted(res):
                if aid % 1000000 in KEEP:
                    evs = res[aid]
                    atk = "/".join(f"{round(st * 60)}-{round(en * 60)}" for t, st, en, a in evs if t == 1)
                    rh = "/".join(str(round(st * 60)) for t, st, en, a in evs if t == 0 and a == 4)
                    lh = "/".join(str(round(st * 60)) for t, st, en, a in evs if t == 0 and a == 16)
                    rhi = "/".join(str(round(st * 60)) for t, st, en, a in evs if t == 0 and a == 1)
                    rf = REFS.get((tid, aid), (0, 0, 0))
                    ja = "/".join(",".join(map(str, ATKARGS.get((tid, aid, round(st * 60)), ()))) for t, st, en, a in evs if t == 1)
                    lines.append(f"{short[:-4]}|{aid % 1000000}|{atk}|{rh}|{lh}|{rhi}|{rf[0]}:{rf[1]}:{rf[2]}|{ja}")
        cats = weapon_motion_categories()
        lines.append("W " + " ".join(f"{k // 10000}:{v[0]}:{v[1]}:{v[2]}:{v[4]}" for k, v in sorted(cats.items()) if k % 10000 == 0 and k < 30000000))
    text = "\n".join(lines)
    if OUT:
        open(OUT, "w").write(text); print(f"wrote {OUT} ({len(text)} chars)")
    else:
        print(text)
