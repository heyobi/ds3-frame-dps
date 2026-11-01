#!/usr/bin/env python3
"""Read-only: decrypt Elden Ring's regulation.bin and write each .param inside it to OUTDIR/params/.

usage: python3 er/er_regulation.py "<...>/ELDEN RING/Game/regulation.bin" OUTDIR

regulation.bin = 16-byte IV + AES-256-CBC (public key from SoulsFormats) over a ZSTD DCX holding a BND4 of params.
Needs `pip install cryptography zstandard`.
"""
import os, struct, sys
import zstandard
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
_a = sys.argv; sys.argv = sys.argv[:1]
import ds3_frames as F          # BND4 reader
sys.argv = _a

KEY = bytes([0x99, 0xBF, 0xFC, 0x36, 0x6A, 0x6B, 0xC8, 0xC6, 0xF5, 0x82, 0x7D, 0x09, 0x36, 0x02, 0xD6, 0x76,
             0xC4, 0x28, 0x92, 0xA0, 0x1C, 0x20, 0x7F, 0xB0, 0x24, 0xD3, 0xAF, 0x4E, 0x49, 0x3F, 0xEF, 0x99])

src, out = sys.argv[1], sys.argv[2]
raw = open(src, "rb").read()
d = Cipher(algorithms.AES(KEY), modes.CBC(raw[:16])).decryptor()
dcx = d.update(raw[16:]) + d.finalize()
assert dcx[:4] == b"DCX\0", "not a DCX after decryption"
usize = struct.unpack_from(">I", dcx, 0x1C)[0]
start = dcx.index(b"DCA\0") + 8
data = zstandard.ZstdDecompressor().decompress(dcx[start:], max_output_size=usize)
os.makedirs(os.path.join(out, "params"), exist_ok=True)
n = 0
for _, name, body in F.bnd4(data):
    if name.lower().endswith(".param"):
        open(os.path.join(out, "params", name.replace("\\", "/").split("/")[-1]), "wb").write(body); n += 1
print(f"{n} params -> {out}/params")
