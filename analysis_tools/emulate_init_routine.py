#!/usr/bin/env python3
"""Extract the panel register writes of a straight-line init routine in the decompressed melis kernel by emulating it.

Handles the instruction subset the compiled vendor routine uses (addi, c.li, c.mv, c.lui, c.addi4spn, sb/sh/sw, lw, jal, c.jr)
and intercepts calls to DCS_WR / DELAY_MS / HS_ON. Output: JSON list of events. Also works on our replacement routine.
usage: emulate_init_routine.py KERNEL.bin [START_FILE_OFFSET=0x810ae] [END=0x81f94] > events.json
"""
import json, re, sys
import capstone

BASE = 0x40000000                       # tool convention: file offset + 0x40000000 (true runtime is +0x40050000)
DCS_WR, DELAY_MS, HS_ON = 0x4007C71E, 0x4007C51C, 0x4007C6B8
REG = {"zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4, "t0": 5, "t1": 6, "t2": 7, "s0": 8, "s1": 9,
       **{f"a{i}": 10 + i for i in range(8)}, **{f"s{i}": 16 + i for i in range(2, 12)}, **{f"t{i}": 25 + i for i in range(3, 7)}}


def run(kernel, start, end):
    md = capstone.Cs(capstone.CS_ARCH_RISCV, capstone.CS_MODE_RISCV32 | capstone.CS_MODE_RISCVC); md.skipdata = True
    ins = list(md.disasm(kernel[start:end], BASE + start))
    r = [0] * 32; r[2] = 0x10000000; mem = {}; ev = []
    M = 0xFFFFFFFF
    def st(a, v, n):
        for i in range(n): mem[(a + i) & M] = (v >> (8 * i)) & 0xFF
    def rd(a, n):
        v = [mem.get((a + i) & M) for i in range(n)]
        if None in v: ev.append({"op": "unwritten_read", "addr": hex(a)})
        return [x or 0 for x in v]
    for i in ins:
        mn, op = i.mnemonic, [x.strip() for x in i.op_str.split(",")]
        def mm(s):
            m = re.fullmatch(r"(-?0x[0-9a-f]+|-?\d+)\((\w+)\)", s); return int(m.group(1), 0), REG[m.group(2)]
        if mn in ("addi", "c.addi"):
            rdn = REG[op[0]]; src = REG[op[1]] if len(op) == 3 else rdn; imm = int(op[-1], 0); r[rdn] = (r[src] + imm) & M
        elif mn == "c.li": r[REG[op[0]]] = int(op[1], 0) & M
        elif mn == "c.mv": r[REG[op[0]]] = r[REG[op[1]]]
        elif mn == "c.lui": r[REG[op[0]]] = (int(op[1], 0) & 0xFFFFF) << 12
        elif mn == "c.addi4spn": r[REG[op[0]]] = (r[2] + int(op[2], 0)) & M
        elif mn in ("sb", "sh", "sw", "c.sw", "c.swsp"):
            off, b = mm(op[1]) if mn != "c.swsp" else (int(op[1].split("(")[0], 0), 2)
            st((r[b] + off) & M, r[REG[op[0]]], {"sb": 1, "sh": 2}.get(mn, 4))
        elif mn in ("lw", "c.lw", "c.lwsp"):
            pass                                              # epilogue restores; irrelevant for the writes
        elif mn == "jal":
            tgt = (i.address + int(op[-1], 0)) & M
            if tgt == DCS_WR: ev.append({"op": "dcs", "reg": r[11], "n": r[13], "data": rd(r[12], r[13])})
            elif tgt == DELAY_MS: ev.append({"op": "delay", "ms": r[10]})
            elif tgt == HS_ON: ev.append({"op": "hs_on"})
            else: ev.append({"op": "call", "target": hex(tgt)})
        elif mn == "c.jr": break
        else: ev.append({"op": "unhandled", "ins": f"{mn} {i.op_str}", "at": hex(i.address)})
    return ev


if __name__ == "__main__":
    k = open(sys.argv[1], "rb").read()
    s = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x810AE
    e = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x81F94
    print(json.dumps(run(k, s, e)))
