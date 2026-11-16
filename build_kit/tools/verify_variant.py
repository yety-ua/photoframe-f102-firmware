#!/usr/bin/env python3
"""Independent structural check of a smartframe image variant (host-side, stdlib only).

Checks: IMAGEWTY item table, Vmelis_pkg_nor.fex word sum, sunxi-package add_sum, Vdata_udisk sum, the melis
kernel (LZMA, decodes to exactly its stored size), embedded config == config_nor.fex, panel timing table,
panel timing rule (vbp - vspw > 3), compressed kernel fits its slot, and a summary of what differs from --base.
Exit code 0 = all hard checks passed. Says nothing about whether the image boots (only the device can).
"""
import argparse, hashlib, json, lzma, struct, sys

STAMP = 0x5F0A6C39
TIMING_OFF = 0x10E7F0          # 9 x u16 in the decompressed kernel: dclk,x,y,ht,vt,hbp,vbp,hspw,vspw
TIMING_ORIG = (73, 800, 1280, 890, 1340, 25, 20, 20, 4)
CFG_KEYS = ("lcd_if", "lcd_use_drv_timing", "lcd_dsi_if", "lcd_dsi_lane", "lcd_dsi_format", "lcd_dsi_te")


def items(img):
    if img[:8] != b"IMAGEWTY":
        raise ValueError("not an IMAGEWTY image")
    out = {}
    for i in range(struct.unpack_from("<I", img, 60)[0]):
        rec = img[(i + 1) * 1024:(i + 2) * 1024]
        nl = struct.unpack_from("<I", rec)[0]
        name = rec[36:36 + nl].split(b"\0")[0].decode()
        out[name] = (struct.unpack_from("<I", rec, 52 + nl)[0], struct.unpack_from("<I", rec, 44 + nl)[0])
    return out


def wsum(b):
    return sum(struct.unpack_from(f"<{len(b) // 4}I", b)) & 0xFFFFFFFF


def cfg_value(cfg, key):
    i = cfg.find(key.encode() + b"\0")
    off, cnt, ty = struct.unpack_from("<IHH", cfg, i + 32)
    if ty == 2:
        return cfg[off * 4:off * 4 + 32].split(b"\0")[0].decode()
    return struct.unpack_from("<I", cfg, off * 4)[0]


def analyse(img):
    r, it = {"ok": True, "problems": []}, items(img)
    def bad(msg):
        r["ok"] = False; r["problems"].append(msg)
    po, pl = it["melis_pkg_nor.fex"]; vo, _ = it["Vmelis_pkg_nor.fex"]
    pkg = img[po:po + pl]
    if wsum(pkg) != struct.unpack_from("<I", img, vo)[0]:
        bad("Vmelis_pkg_nor.fex sum mismatch")
    L = struct.unpack_from("<I", pkg, 0x24)[0]
    t = bytearray(pkg[:L]); stored = struct.unpack_from("<I", t, 0x14)[0]
    struct.pack_into("<I", t, 0x14, STAMP)
    if wsum(t) != stored:
        bad("package add_sum mismatch")
    do, dl = it["data_udisk.fex"]; dvo, _ = it["Vdata_udisk.fex"]
    if wsum(img[do:do + dl]) != struct.unpack_from("<I", img, dvo)[0]:
        bad("Vdata_udisk sum mismatch")
    ko, kl = struct.unpack_from("<II", pkg, 0x80)
    nxt = min(struct.unpack_from("<I", pkg, 0x80 + 0x170 * i)[0] for i in (1, 2))
    r["kernel_compressed"], r["kernel_slot"] = kl, nxt - ko
    if ko + kl > nxt:
        bad("compressed kernel overflows its slot")
    dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    try:
        kern = dec.decompress(pkg[ko:ko + kl])
    except lzma.LZMAError as e:
        bad(f"kernel does not decompress: {e}"); kern = b""
    declared = struct.unpack_from("<Q", pkg, ko + 5)[0]
    if kern and len(kern) != declared:
        bad("kernel size != header size")
    r["kernel"] = kern
    co, cl = it["config_nor.fex"]; cfg = img[co:co + cl]
    if pkg.find(cfg) < 0:
        bad("config_nor.fex copy not found inside melis package")
    r["config"] = {k: cfg_value(cfg, k) for k in ("lcd_driver_name",) + CFG_KEYS}
    if kern:
        tm = struct.unpack_from("<9H", kern, TIMING_OFF)
        n = dict(zip("dclk x y ht vt hbp vbp hspw vspw".split(), tm))
        r["timing"] = n
        r["derived"] = {"vbp-vspw": n["vbp"] - n["vspw"], "vfp": n["vt"] - n["y"] - n["vbp"],
                        "hfp": n["ht"] - n["x"] - n["hbp"], "fps": round(n["dclk"] * 1e6 / (n["ht"] * n["vt"]), 2)}
        if n["hbp"] <= n["hspw"]:
            bad("timing: hbp <= hspw (sunxi hbp includes hspw; reported TCON hang)")
        if n["vbp"] - n["vspw"] <= 3:
            bad("timing: vbp - vspw <= 3 (kernel rejects: 'vbp is too small')")
    r["items"] = it
    r["sha256"] = hashlib.sha256(img).hexdigest()
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("--base", help="reference image to diff against")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--frame", choices=["1", "2"], help="check against a frame profile (needs --stock)")
    ap.add_argument("--stock", help="stock seller 16.10 image (kernel reference for --frame)")
    ap.add_argument("--recipe-timing", help="expected dclk,ht,hbp,hspw,vt,vbp,vspw for --frame 2")
    a = ap.parse_args()
    img = open(a.image, "rb").read()
    r = analyse(img)
    lines = [f"image   : {a.image}", f"sha256  : {r['sha256']}", f"size    : {len(img)}",
             f"kernel  : {r['kernel_compressed']} B compressed, slot {r['kernel_slot']} B, free {r['kernel_slot'] - r['kernel_compressed']} B",
             f"config  : {r['config']}", f"timing  : {r.get('timing')}", f"derived : {r.get('derived')}"]
    if a.base:
        base = open(a.base, "rb").read()
        b = analyse(base)
        lines.append(f"base    : {a.base}  sha256 {b['sha256'][:16]}…")
        if len(base) != len(img):
            r["ok"] = False; r["problems"].append("image length differs from base")
        else:
            it = r["items"]; chg = {}
            for i in range(len(img)):
                if img[i] != base[i]:
                    n = next((k for k, (o, l) in it.items() if o <= i < o + l), "<outside items>")
                    chg[n] = chg.get(n, 0) + 1
            lines.append(f"changed : {chg or 'nothing'}  (bytes per item)")
            if "<outside items>" in chg:
                r["ok"] = False; r["problems"].append("bytes changed outside any item")
            if r["kernel"] and b["kernel"] and len(r["kernel"]) == len(b["kernel"]):
                d = [i for i in range(len(r["kernel"])) if r["kernel"][i] != b["kernel"][i]]
                lines.append(f"kernel Δ: {len(d)} decompressed bytes" + (f" in {hex(min(d))}..{hex(max(d))}" if d else ""))
            for k in set(r["items"]) - {"melis_pkg_nor.fex", "Vmelis_pkg_nor.fex", "config_nor.fex"}:
                o, l = r["items"][k]
                if img[o:o + l] != base[o:o + l]:
                    r["ok"] = False; r["problems"].append(f"unexpected change in item {k}")
    if a.frame:
        if not a.stock:
            r["ok"] = False; r["problems"].append("--frame needs --stock")
        else:
            st = analyse(open(a.stock, "rb").read())
            sk, ik = st["kernel"], r["kernel"]
            d = [i for i in range(min(len(sk), len(ik))) if sk[i] != ik[i]] if len(sk) == len(ik) else None
            allowed = lambda i: 0x810AE <= i < 0x81F94 or 0x10E7F0 <= i < 0x10E802
            same_cfg = st["config"] == r["config"]
            if a.frame == "1":
                ok1 = d == [] and same_cfg
                lines.append(f"frame 1 : kernel identical to stock = {d == []}, config identical to stock = {same_cfg}")
                if not ok1:
                    r["ok"] = False; r["problems"].append("FRAME 1 image must have the stock kernel and config; this one is patched: do NOT flash on frame 1")
            else:
                ok2 = d is not None and all(allowed(i) for i in d) and bool(d) and same_cfg
                lines.append(f"frame 2 : kernel differs from stock only in init-routine slot/timing table = {d is not None and all(allowed(i) for i in d)}, "
                             f"patched = {bool(d)}, config identical to stock = {same_cfg}")
                if a.recipe_timing:
                    dclk, ht, hbp, hspw, vt, vbp, vspw = (int(x) for x in a.recipe_timing.split(","))
                    want = dict(dclk=dclk, x=800, y=1280, ht=ht, vt=vt, hbp=hbp, vbp=vbp, hspw=hspw, vspw=vspw)
                    lines.append(f"recipe timing match = {r.get('timing') == want}")
                    ok2 = ok2 and r.get("timing") == want
                if not ok2:
                    r["ok"] = False; r["problems"].append("frame 2 profile check failed")
    lines.append("RESULT  : " + ("PASS (structure only; device boot is untested)" if r["ok"] else "FAIL: " + "; ".join(r["problems"])))
    print("\n".join(lines))
    if a.json:
        r.pop("kernel", None); r.pop("items", None)
        print(json.dumps(r, indent=2))
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
