#!/usr/bin/env python3
"""Set a single-word (u32) key of the compiled config in an IMAGEWTY smartframe image (host-side only).

config_nor.fex layout (observed): header, then 32-byte-name entries followed by (u32 word offset,
u16 word count, u16 type); a type-1 value lives at file offset word_offset * 4. The same config is
embedded in melis_pkg_nor.fex; both copies are patched, then the sunxi-package add_sum and the
Vmelis_pkg_nor.fex word sum are recomputed (same as tools/set_lcd_driver.py). Nothing is flashed.
"""
import argparse, hashlib, json, os, struct, sys

STAMP = 0x5F0A6C39


def items(img):
    if img[:8] != b"IMAGEWTY":
        sys.exit("not an IMAGEWTY image")
    out = {}
    for i in range(struct.unpack_from("<I", img, 60)[0]):
        rec = img[(i + 1) * 1024:(i + 2) * 1024]
        nl = struct.unpack_from("<I", rec)[0]
        name = rec[36:36 + nl].split(b"\0")[0].decode()
        out[name] = (struct.unpack_from("<I", rec, 52 + nl)[0], struct.unpack_from("<I", rec, 44 + nl)[0])
    return out


def wsum(b):
    return sum(struct.unpack_from(f"<{len(b) // 4}I", b)) & 0xFFFFFFFF


def locate(cfg, key):
    i = cfg.find(key.encode() + b"\0")
    if i < 0 or cfg[i - 1:i] not in (b"\0",) and i != 0:
        pass
    off, cnt, ty = struct.unpack_from("<IHH", cfg, i + 32)
    if (cnt, ty) != (1, 1):
        sys.exit(f"{key}: not a single u32 value (count={cnt}, type={ty})")
    return off * 4


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("assign", nargs="+", help="key=value, e.g. lcd_dsi_if=2")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    if os.path.exists(a.output):
        sys.exit("output exists; choose a new path")
    img = bytearray(open(a.image, "rb").read())
    it = items(img)
    coff, clen = it["config_nor.fex"]
    poff, plen = it["melis_pkg_nor.fex"]
    voff, _ = it["Vmelis_pkg_nor.fex"]
    cfg = bytearray(img[coff:coff + clen])
    pkg = bytearray(img[poff:poff + plen])
    if wsum(pkg) != struct.unpack_from("<I", img, voff)[0]:
        sys.exit("input Vmelis checksum mismatch")
    emb = pkg.find(bytes(cfg))
    if emb < 0:
        sys.exit("config copy not found inside melis_pkg_nor.fex")
    changes = {}
    for kv in a.assign:
        key, val = kv.split("=")
        pos = locate(cfg, key)
        old = struct.unpack_from("<I", cfg, pos)[0]
        struct.pack_into("<I", cfg, pos, int(val, 0))
        changes[key] = {"old": old, "new": int(val, 0), "offset_in_config": pos}
    img[coff:coff + clen] = cfg
    pkg[emb:emb + clen] = cfg
    length = struct.unpack_from("<I", pkg, 0x24)[0]
    tmp = bytearray(pkg[:length]); struct.pack_into("<I", tmp, 0x14, STAMP)
    struct.pack_into("<I", pkg, 0x14, wsum(tmp))
    img[poff:poff + plen] = pkg
    struct.pack_into("<I", img, voff, wsum(pkg))
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    open(a.output, "wb").write(img)
    rep = {"source": a.image, "source_sha256": hashlib.sha256(open(a.image, "rb").read()).hexdigest(),
           "output": a.output, "output_sha256": hashlib.sha256(img).hexdigest(), "changes": changes,
           "embedded_config_offset": emb}
    open(a.output + ".json", "w").write(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
