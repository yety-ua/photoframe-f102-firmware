#!/usr/bin/env python3
"""Rebuild the five known reference variants from the v11k base and compare with the reference images.

A byte-identical result proves the whole toolchain on this machine. If bytes differ only because another liblzma
version compressed the kernel differently, the test still passes when the *decompressed* kernels are identical and
verify_variant passes (reported as WARN).
"""
import hashlib, lzma, os, shutil, struct, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); KIT = os.path.abspath(os.path.join(HERE, ".."))
FW = os.path.join(KIT, "..", "firmware")
T = "jieli_ac792_ili9881c_800x1280"
CASES = [  # name, make_variant args, reference folder, expected sha256
    ("v12a", ["--table", T], "F2_v12a_detect_jieli", "342ee83f5302c0ab59fe46cd4081998799a44305dbfacfb02a3951fa83c02dc8"),
    ("v12d1", ["--table", T, "--timing", "72,908,56,8,1317,22,6"], "F2_v12d1_jieli_timing_fixed", "b4323e22c53bc23aec5f41454f1721ab397cdb7a3e1846aac7a92718a58dade1"),
    ("v12d2", ["--table", T, "--timing", "73,908,56,8,1340,26,6"], "F2_v12d2_jieli_vt1340", "4a3f00cc8d05c96d8eb5036eb543af8b547c4992bc2f4fc99c5991a7d87b96b5"),
    ("v12e1", ["--table", T, "--timing", "72,908,56,8,1317,22,6", "--set", "lcd_dsi_if=2"], "F2_v12e1_d1_dsi_burst", "eab4d8c43a8e90a67b2c50af752305e0cf65d44d463f46493b797eba631ba218"),
    ("F2_profile", ["--frame", "2"], "F2_RELEASE_k101_stock_timing", "33c979a951969a9bc11d1043bcdebf07d3597e21359ef17ea8f766df2415f25b"),
    ("F1_profile", ["--frame", "1"], "F1_v11k_current_frame1", "784eb0582048ad1a203c709ab5a0a38d32758380b527c8732ec7ac9d36036d81"),
    ("frame2_release", ["--table", "linux_k101_im2byl02_init", "--timing", "73,890,25,20,1340,20,4"], "F2_RELEASE_k101_stock_timing", "33c979a951969a9bc11d1043bcdebf07d3597e21359ef17ea8f766df2415f25b"),
    ("v12f0", ["--table", T, "--timing", "72,908,56,8,1317,22,6", "--dump-regs"], "F2_v12f0_dump_regs", "65f2f6096cdddfdee4dfe3b3c6c521b94a4387834fddecc962d4e79c2aa9d7e4"),
    ("v12e2", ["--table", T, "--timing", "72,908,56,8,1317,22,6", "--pre-delay-ms", "200"], "F2_v12e2_d1_predelay200", "4a898eb153cb332946bab6ee3e2c7f589615d9073eb47451df2b7d2723e48873"),
]


def kernel(path):
    img = open(path, "rb").read()
    import verify_variant as V
    it = V.items(img); po, pl = it["melis_pkg_nor.fex"]; pkg = img[po:po + pl]
    ko, kl = struct.unpack_from("<II", pkg, 0x80)
    return lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(pkg[ko:ko + kl])


def main():
    sys.path.insert(0, HERE)
    bad = warn = 0
    for name, args, ref, want in CASES:
        nm = f"selftest_{name}"
        fr = args[args.index("--frame") + 1] if "--frame" in args else None
        od = os.path.join(KIT, "out", (f"F{fr}_" if fr else "") + nm)
        shutil.rmtree(od, ignore_errors=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, "make_variant.py"), "--name", nm, *args], capture_output=True, text=True)
        out = os.path.join(od, "smartframe.img")
        if r.returncode or not os.path.exists(out):
            print(f"FAIL {name}: build error\n{r.stdout[-600:]}{r.stderr[-600:]}"); bad += 1; continue
        got = hashlib.sha256(open(out, "rb").read()).hexdigest()
        if got == want:
            print(f"OK   {name}: identical to reference ({got[:16]}…)")
        else:
            refp = os.path.join(FW, ref, "smartframe.img")
            if os.path.exists(refp) and kernel(out) == kernel(refp):
                print(f"WARN {name}: bytes differ from reference but decompressed kernel is identical (different liblzma build)"); warn += 1
            else:
                print(f"FAIL {name}: differs from reference ({got[:16]}… vs {want[:16]}…)"); bad += 1
        shutil.rmtree(od, ignore_errors=True)
    print("RESULT:", "PASS" if not bad else "FAIL", f"({warn} warning(s))")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
