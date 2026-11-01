#!/usr/bin/env python3
"""Read-only: pull files out of Elden Ring's encrypted archives (Data0-3.bhd/bdt, DLC.bhd/bdt) without changing
anything in the game folder. Files come out still DCX-compressed (Oodle Kraken); decompress them elsewhere.

usage: python3 er_extract.py "<...>/ELDEN RING/Game" OUTDIR /chr/c0000.anibnd.dcx [more paths...]

Needs er_keys.json (archive RSA public keys from UXM Selective Unpacker) next to this script. Pure Python 3;
uses the `cryptography` package for AES if installed, otherwise a slower built-in AES.
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = json.load(open(os.path.join(HERE, "er_keys.json")))

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    def aes_ecb_dec(key, data):
        d = Cipher(algorithms.AES(key), modes.ECB()).decryptor(); return d.update(data) + d.finalize()
except ImportError:
    _argv = sys.argv; sys.argv = sys.argv[:1]
    sys.path.insert(0, HERE)
    from ds3_frames import aes_ecb_dec   # pure-Python fallback
    sys.argv = _argv


def der_rsa_pub(pem):
    import base64
    b = base64.b64decode("".join(l for l in pem.strip().splitlines() if "-----" not in l))
    def tlv(p):
        ln = b[p + 1]; p += 2
        if ln & 0x80:
            k = ln & 0x7f; ln = int.from_bytes(b[p:p + k], "big"); p += k
        return p, ln
    p, _ = tlv(0)
    p, ln = tlv(p); n = int.from_bytes(b[p:p + ln], "big"); p += ln
    p, ln = tlv(p); e = int.from_bytes(b[p:p + ln], "big")
    return n, e


def rsa_decrypt(data, pem):
    n, e = der_rsa_pub(pem); k = (n.bit_length() + 7) // 8
    out = bytearray()
    for i in range(0, len(data), k):
        out += pow(int.from_bytes(data[i:i + k], "big"), e, n).to_bytes(k - 1, "big")
    return bytes(out)


def hash64(p):
    p = p.strip().replace("\\", "/").lower()
    if not p.startswith("/"):
        p = "/" + p
    h = 0
    for ch in p:
        h = (h * 0x85 + ord(ch)) & 0xFFFFFFFFFFFFFFFF
    return h


def bhd_entries(bhd):
    assert bhd[:4] == b"BHD5", bhd[:32].hex()
    # same layout test as SoulsFormats: 64-bit counts/offsets if the ints at 0x14 and 0x1C are both 0
    is64 = struct.unpack_from("<i", bhd, 0x14)[0] == 0 and struct.unpack_from("<i", bhd, 0x1C)[0] == 0
    if is64:
        bucket_count, buckets_off = struct.unpack_from("<qq", bhd, 0x10)
    else:
        bucket_count, buckets_off = struct.unpack_from("<ii", bhd, 0x10)
    ents = {}
    for bi in range(bucket_count):
        if is64:
            cnt, _, off = struct.unpack_from("<iiq", bhd, buckets_off + bi * 16)
        else:
            cnt, off = struct.unpack_from("<ii", bhd, buckets_off + bi * 8)
        for j in range(cnt):
            h, padded, unpadded, foff, sha_off, aes_off = struct.unpack_from("<QiiqqQ", bhd, off + j * 0x28)
            aes = None
            if aes_off:
                key = bhd[aes_off:aes_off + 16]; rc = struct.unpack_from("<i", bhd, aes_off + 16)[0]
                aes = (key, [struct.unpack_from("<qq", bhd, aes_off + 20 + 16 * r) for r in range(rc)])
            ents[h] = (padded, unpadded, foff, aes)
    return ents


def read(bdt, ent):
    padded, unpadded, foff, aes = ent
    with open(bdt, "rb") as f:
        f.seek(foff); data = bytearray(f.read(padded))
    if aes:
        key, ranges = aes
        for s, e in ranges:
            if s != -1 and e != -1 and s != e:
                data[s:e] = aes_ecb_dec(key, bytes(data[s:e]))
    return bytes(data[:unpadded]) if unpadded > 0 else bytes(data)


if __name__ == "__main__":
    game, outdir, paths = sys.argv[1], sys.argv[2], sys.argv[3:]
    os.makedirs(outdir, exist_ok=True)
    want = {hash64(p): p for p in paths}
    found = set()
    for arc in ["DLC", "Data0", "Data1", "Data2", "Data3"]:
        bhd_p, bdt_p = os.path.join(game, arc + ".bhd"), os.path.join(game, arc + ".bdt")
        if not os.path.exists(bhd_p):
            continue
        raw = open(bhd_p, "rb").read()
        bhd = raw if raw[:4] == b"BHD5" else rsa_decrypt(raw, KEYS[arc])
        print(f"# {arc}: header {bhd[:32].hex()}", file=sys.stderr)
        ents = bhd_entries(bhd)
        print(f"# {arc}: {len(ents)} files", file=sys.stderr)
        for h, p in want.items():
            if h in ents:
                data = read(bdt_p, ents[h])
                name = f"{arc}__{p.strip('/').replace('/', '__')}"
                open(os.path.join(outdir, name), "wb").write(data)
                found.add(p)
                print(f"{p} -> {arc} ({len(data)} bytes, starts {data[:4]!r})")
    for p in paths:
        if p not in found:
            print(f"{p}: not found")
