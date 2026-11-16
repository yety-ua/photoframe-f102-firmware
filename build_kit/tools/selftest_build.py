#!/usr/bin/env python3
"""Self-test of the build kit: rebuild known images and compare them with their recorded SHA-256.

A byte-identical result proves the whole toolchain on this machine. If the bytes differ only because another liblzma
version compressed the kernel differently, the build is still valid when verify_variant passes; that is reported as WARN.
Needs the seller's original image (firmware/stock/seller-2026-10-16/smartframe.img) for the variant profiles.
"""
import os, subprocess, sys, shutil, hashlib

HERE = os.path.dirname(os.path.abspath(__file__)); KIT = os.path.abspath(os.path.join(HERE, ".."))
T = "jieli_ac792_ili9881c_800x1280"
K101 = ["--table", "linux_k101_im2byl02_init", "--timing", "73,890,25,20,1340,20,4"]
CASES = [  # label, make_variant arguments, output folder prefix, expected SHA-256
    ("variant A profile (stock kernel)", ["--variant", "a"], "variant-a_", "784eb0582048ad1a203c709ab5a0a38d32758380b527c8732ec7ac9d36036d81"),
    ("variant B profile (K101 init + seller timing)", ["--variant", "b"], "variant-b_", "33c979a951969a9bc11d1043bcdebf07d3597e21359ef17ea8f766df2415f25b"),
    ("variant B built by hand (same parameters)", K101, "", "33c979a951969a9bc11d1043bcdebf07d3597e21359ef17ea8f766df2415f25b"),
    ("experiment: JieLi table with its own timing", ["--table", T, "--timing", "72,908,56,8,1317,22,6"], "", "b4323e22c53bc23aec5f41454f1721ab397cdb7a3e1846aac7a92718a58dade1"),
    ("experiment: register-dump build", ["--table", T, "--timing", "72,908,56,8,1317,22,6", "--dump-regs"], "", "65f2f6096cdddfdee4dfe3b3c6c521b94a4387834fddecc962d4e79c2aa9d7e4"),
    ("experiment: config change (lcd_dsi_if=2 is a known-bad value; regression test only)", ["--table", T, "--timing", "72,908,56,8,1317,22,6", "--set", "lcd_dsi_if=2"], "", "eab4d8c43a8e90a67b2c50af752305e0cf65d44d463f46493b797eba631ba218"),
]


def main():
    bad = warn = 0
    for i, (label, args, prefix, want) in enumerate(CASES):
        nm = f"selftest_{i}"; od = os.path.join(KIT, "out", prefix + nm)
        shutil.rmtree(od, ignore_errors=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, "make_variant.py"), "--name", nm, *args], capture_output=True, text=True)
        out = os.path.join(od, "smartframe.img")
        if r.returncode or not os.path.exists(out):
            print(f"FAIL {label}: build error\n{(r.stdout + r.stderr)[-600:]}"); bad += 1; continue
        got = hashlib.sha256(open(out, "rb").read()).hexdigest()
        if got == want:
            print(f"OK   {label}: identical to the recorded image ({got[:16]}…)")
        else:
            v = subprocess.run([sys.executable, os.path.join(HERE, "verify_variant.py"), out], capture_output=True, text=True)
            if v.returncode == 0:
                print(f"WARN {label}: bytes differ from the recorded image but the structure verifies (different liblzma build?)"); warn += 1
            else:
                print(f"FAIL {label}: differs and does not verify ({got[:16]}… vs {want[:16]}…)"); bad += 1
        shutil.rmtree(od, ignore_errors=True)
    print("RESULT:", "PASS" if not bad else "FAIL", f"({warn} warning(s))")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
