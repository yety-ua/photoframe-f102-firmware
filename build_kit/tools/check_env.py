#!/usr/bin/env python3
"""Check that this machine can build variants: Python version, liblzma >= 5.4 (LZMA1EXT), assembler self-test."""
import os, struct, sys, lzma

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ok = True
print("python  :", sys.version.split()[0], sys.platform, "64-bit" if sys.maxsize > 2**32 else "32-bit")
if sys.version_info < (3, 8):
    print("FAIL    : Python 3.8+ needed"); ok = False
import force_auto_mipi_branch as fab
try:
    lib = fab.load_liblzma()
    print(f"liblzma : {lib.found_version} at {lib.found_path}")
    data = bytes(range(256)) * 400 + b"photo frame" * 500
    comp = fab.compress(data, 1 << 20, 3, 0, 2)
    back = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(comp)
    print("lzma1ext: round-trip", "OK" if back == data else "FAIL"); ok &= back == data
    marker_free = struct.unpack_from("<Q", comp, 5)[0] == len(data)
    print("header  : known size recorded =", marker_free)
except SystemExit as e:
    print("FAIL    :", e); ok = False
import rv32asm
code = rv32asm.assemble("_start:\n addi sp, sp, -32\n sw ra, 28(sp)\n li a0, 200\n call f\n ret\nf:\n j _start\n", 0x1000)
want = bytes.fromhex("130101fe232e11001305800c97000000e780c000678000006ff09ffe")   # checked against llvm-mc
print("asm     :", "OK" if code == want else "FAIL (assembler output differs)"); ok &= code == want
print("RESULT  :", "READY" if ok else "NOT READY - fix the FAIL lines above")
sys.exit(0 if ok else 1)
