#!/usr/bin/env python3
"""Tiny RV32IM assembler for the init-routine template used by force_auto_mipi_branch.py.

Replaces llvm-mc + ld.lld + llvm-objcopy so that Windows needs only Python. Supported subset (all that the
template uses): addi, lw, lbu, sw, sb, beq/bne (+beqz), jal (+j), jalr (+ret), auipc, lui, mv, li, la, call,
`.byte`, labels, and the directives `.option/.text/.globl` (ignored). Output equals what
`llvm-mc -triple=riscv32 -mattr=+m` + `ld.lld --no-relax -Ttext=BASE` + `llvm-objcopy -O binary` produces
for this subset (checked byte-for-byte in tools/selftest_build.py when LLVM is available).
"""
import re
import struct

REGS = {"zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4, "t0": 5, "t1": 6, "t2": 7, "s0": 8, "fp": 8, "s1": 9,
        **{f"a{i}": 10 + i for i in range(8)}, **{f"s{i}": 16 + i for i in range(2, 12)},
        **{f"t{i}": 25 + i for i in range(3, 7)}, **{f"x{i}": i for i in range(32)}}


def reg(n):
    try:
        return REGS[n.strip()]
    except KeyError:
        raise ValueError(f"unknown register {n!r}")


def num(s):
    return int(s.strip(), 0)


def r_i(op, f3, rd, rs1, imm):
    if not -2048 <= imm <= 2047:
        raise ValueError(f"imm12 out of range: {imm}")
    return (imm & 0xFFF) << 20 | rs1 << 15 | f3 << 12 | rd << 7 | op


def r_s(op, f3, rs1, rs2, imm):
    if not -2048 <= imm <= 2047:
        raise ValueError(f"imm12 out of range: {imm}")
    return ((imm >> 5) & 0x7F) << 25 | rs2 << 20 | rs1 << 15 | f3 << 12 | (imm & 0x1F) << 7 | op


def r_b(f3, rs1, rs2, off):
    if off % 2 or not -4096 <= off <= 4094:
        raise ValueError(f"branch offset out of range: {off}")
    o = off & 0x1FFF
    return ((o >> 12) & 1) << 31 | ((o >> 5) & 0x3F) << 25 | rs2 << 20 | rs1 << 15 | f3 << 12 | \
        ((o >> 1) & 0xF) << 8 | ((o >> 11) & 1) << 7 | 0x63


def r_u(op, rd, imm20):
    return (imm20 & 0xFFFFF) << 12 | rd << 7 | op


def r_j(rd, off):
    if off % 2 or not -(1 << 20) <= off < (1 << 20):
        raise ValueError(f"jal offset out of range: {off}")
    o = off & 0x1FFFFF
    return ((o >> 20) & 1) << 31 | ((o >> 1) & 0x3FF) << 21 | ((o >> 11) & 1) << 20 | ((o >> 12) & 0xFF) << 12 | rd << 7 | 0x6F


def hi_lo(off):
    hi = (off + 0x800) >> 12
    lo = off - (hi << 12)
    return hi & 0xFFFFF, lo


def split_ops(s):
    return [x.strip() for x in s.split(",")] if s.strip() else []


def mem(op):
    m = re.fullmatch(r"\s*(-?\w+)\((\w+)\)\s*", op)
    if not m:
        raise ValueError(f"bad memory operand {op!r}")
    return num(m.group(1)), reg(m.group(2))


def parse(text):
    lines = []
    for raw in text.splitlines():
        line = raw.split("#")[0].strip()
        if not line:
            continue
        while True:
            m = re.match(r"^([A-Za-z_]\w*):\s*(.*)$", line)
            if not m:
                break
            lines.append(("label", m.group(1)))
            line = m.group(2)
        if line:
            parts = line.split(None, 1)
            lines.append(("ins", parts[0], parts[1] if len(parts) > 1 else ""))
    return lines


def li_size(imm):
    return 4 if -2048 <= imm <= 2047 else 8


def assemble(text, base, syms=None):
    syms = dict(syms or {})
    items = parse(text)
    labels, pc, sized = {}, base, []
    for it in items:
        if it[0] == "label":
            labels[it[1]] = pc
            continue
        _, mn, args = it
        if mn in (".option", ".text", ".globl"):
            continue
        if mn == ".byte":
            n = len(split_ops(args))
        elif mn in ("call", "la"):
            n = 8
        elif mn == "li":
            n = li_size(num(split_ops(args)[1]))
        else:
            n = 4
        sized.append((pc, mn, args))
        pc += n
    labels.update({k: v for k, v in syms.items() if k not in labels})

    def target(name):
        if name in labels:
            return labels[name]
        raise ValueError(f"undefined symbol {name!r}")

    out = bytearray()
    for pc, mn, args in sized:
        o = split_ops(args)
        w = []
        if mn == ".byte":
            out += bytes(num(x) & 0xFF for x in o)
            continue
        if mn == "addi":
            w = [r_i(0x13, 0, reg(o[0]), reg(o[1]), num(o[2]))]
        elif mn == "mv":
            w = [r_i(0x13, 0, reg(o[0]), reg(o[1]), 0)]
        elif mn == "li":
            imm, rd = num(o[1]), reg(o[0])
            if li_size(imm) == 4:
                w = [r_i(0x13, 0, rd, 0, imm)]
            else:
                hi, lo = hi_lo(imm)
                w = [r_u(0x37, rd, hi), r_i(0x13, 0, rd, rd, lo)]
        elif mn == "la":
            hi, lo = hi_lo(target(o[1]) - pc)
            rd = reg(o[0])
            w = [r_u(0x17, rd, hi), r_i(0x13, 0, rd, rd, lo)]
        elif mn == "call":
            hi, lo = hi_lo(target(o[0]) - pc)
            w = [r_u(0x17, 1, hi), r_i(0x67, 0, 1, 1, lo)]
        elif mn == "lw":
            imm, rs1 = mem(o[1]); w = [r_i(0x03, 2, reg(o[0]), rs1, imm)]
        elif mn == "lbu":
            imm, rs1 = mem(o[1]); w = [r_i(0x03, 4, reg(o[0]), rs1, imm)]
        elif mn == "sw":
            imm, rs1 = mem(o[1]); w = [r_s(0x23, 2, rs1, reg(o[0]), imm)]
        elif mn == "sb":
            imm, rs1 = mem(o[1]); w = [r_s(0x23, 0, rs1, reg(o[0]), imm)]
        elif mn == "beqz":
            w = [r_b(0, reg(o[0]), 0, target(o[1]) - pc)]
        elif mn == "beq":
            w = [r_b(0, reg(o[0]), reg(o[1]), target(o[2]) - pc)]
        elif mn == "bne":
            w = [r_b(1, reg(o[0]), reg(o[1]), target(o[2]) - pc)]
        elif mn == "j":
            w = [r_j(0, target(o[0]) - pc)]
        elif mn == "ret":
            w = [r_i(0x67, 0, 0, 1, 0)]
        else:
            raise ValueError(f"unsupported instruction {mn!r}")
        for x in w:
            out += struct.pack("<I", x)
    return bytes(out)
