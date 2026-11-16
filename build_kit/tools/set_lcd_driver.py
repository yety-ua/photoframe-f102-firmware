#!/usr/bin/env python3
"""Switch the active lcd0 panel driver in an IMAGEWTY smartframe image (host-side only).

Replaces the compiled `lcd_driver_name` value in `config_nor.fex` and in its copy
embedded in `melis_pkg_nor.fex`, then recomputes the sunxi-package add_sum and the
`Vmelis_pkg_nor.fex` word sum. Only same-slot replacements are done; the new name
must be registered in the image's kernel. Nothing is flashed.
"""
import argparse, hashlib, json, os, struct, sys

STAMP = 0x5F0A6C39


def items(img):
    if img[:8] != b"IMAGEWTY":
        sys.exit("not an IMAGEWTY image")
    # same layout as tools/inspect_firmware.py
    count = struct.unpack_from("<I", img, 60)[0]
    out = {}
    for i in range(count):
        rec = img[(i + 1) * 1024 : (i + 2) * 1024]
        nl = struct.unpack_from("<I", rec)[0]
        name = rec[36 : 36 + nl].split(b"\0")[0].decode()
        stored_len = struct.unpack_from("<I", rec, 36 + nl)[0]
        orig_len = struct.unpack_from("<I", rec, 44 + nl)[0]
        off = struct.unpack_from("<I", rec, 52 + nl)[0]
        out[name] = (off, orig_len, stored_len)
    return out


def word_sum(b):
    return sum(struct.unpack_from(f"<{len(b) // 4}I", b)) & 0xFFFFFFFF


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("driver", help="registered panel name, e.g. boe_jd9365da_h3_hy_dsi_panel")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    if os.path.exists(a.output):
        sys.exit("output exists; choose a new path")
    img = bytearray(open(a.image, "rb").read())
    it = items(img)
    for need in ("config_nor.fex", "melis_pkg_nor.fex", "Vmelis_pkg_nor.fex"):
        if need not in it:
            sys.exit(f"missing item {need}: {sorted(it)}")
    coff, clen, _ = it["config_nor.fex"]
    poff, plen, _ = it["melis_pkg_nor.fex"]
    voff, _, _ = it["Vmelis_pkg_nor.fex"]
    cfg = bytes(img[coff : coff + clen])
    pkg = img[poff : poff + plen]
    if word_sum(pkg) != struct.unpack_from("<I", img, voff)[0]:
        sys.exit("input Vmelis checksum mismatch")
    emb = pkg.find(cfg)
    if emb < 0:
        sys.exit("config_nor.fex copy not found inside melis_pkg_nor.fex")
    new = a.driver.encode()
    # kernel must register the panel name (as a NUL-terminated string)
    if (b"\0" + new + b"\0") not in pkg and new not in pkg:
        print("warning: driver name not found in package bytes (kernel is compressed; check strings)")
    # locate current value: the string that follows key 'lcd_driver_name' in the value area
    key_idx = cfg.find(b"lcd_driver_name\0")
    if key_idx < 0:
        sys.exit("lcd_driver_name key not found")
    # value pool: find a known panel-name string ending in _panel or auto_mipi after header
    cands = [s for s in cfg.split(b"\0") if s.endswith(b"_panel") or s == b"auto_mipi"]
    if len(cands) != 1:
        sys.exit(f"ambiguous current driver values: {cands}")
    old = cands[0]
    vi = cfg.find(b"\0" + old + b"\0") + 1
    slot_end = vi + len(old)
    while slot_end < len(cfg) and cfg[slot_end] == 0 and slot_end - vi < len(new) + 1:
        slot_end += 1
    if len(new) + 1 > slot_end - vi:
        sys.exit(f"new name longer than slot ({len(new)} vs {slot_end - vi - 1})")
    ncfg = bytearray(cfg)
    ncfg[vi:slot_end] = new + b"\0" * (slot_end - vi - len(new))
    img[coff : coff + clen] = ncfg
    pkg[emb : emb + clen] = ncfg
    length = struct.unpack_from("<I", pkg, 0x24)[0]
    tmp = bytearray(pkg[:length]); struct.pack_into("<I", tmp, 0x14, STAMP)
    struct.pack_into("<I", pkg, 0x14, word_sum(tmp))
    img[poff : poff + plen] = pkg
    struct.pack_into("<I", img, voff, word_sum(pkg))
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    open(a.output, "wb").write(img)
    rep = {
        "source": a.image, "source_sha256": hashlib.sha256(open(a.image, "rb").read()).hexdigest(),
        "output": a.output, "output_sha256": hashlib.sha256(img).hexdigest(),
        "old_driver": old.decode(), "new_driver": a.driver,
        "config_offset_in_item": vi, "embedded_config_offset": emb,
    }
    open(a.output + ".json", "w").write(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
