#!/usr/bin/env python3
"""Experiment: force the `auto_mipi` panel driver of the 16.10 seller kernel into one init branch.

Host-side only. Works on the 16.10 seller image (kernel SHA-256 checked). Patches the first ID
compare in the auto_mipi init function (0x40082e8e) into an unconditional jump to the chosen
branch, recompresses the kernel (LZMA-alone, original props/dict, explicit size), rewrites the
melis-lzma item length, the sunxi-package add_sum and Vmelis_pkg_nor.fex. Nothing is flashed.
"""
import argparse, hashlib, json, lzma, os, struct, sys

KERNEL_SHA = "1bfcc4c0e759bf2ca1c8e155044a8d31f78507fd0fb7c4a411bc434ac68b2ef6"
BASE = 0x40000000
SITE = 0x40082E8E
SITE_BYTES = bytes.fromhex("6384c700")  # beq a5,a2,+8
BRANCHES = {  # ID that auto_mipi maps to this init table -> branch entry
    "m080_110b1_160": 0x4008371E,       # 93 66 ff 00 (JD9366)
    "ili9881_inx_f101a35": 0x400841F4,  # 98 81 1c 00
    "nt35521": 0x40084252,              # 00 80 00 00
    "s8036_ili9881_fc": 0x40084B92,     # 98 81 5c 00
}
BRANCH_HEAD = {  # first 4 bytes at each branch entry (auipc a7, ...) in the 16.10 kernel
    "m080_110b1_160": bytes.fromhex("97180500"),
    "ili9881_inx_f101a35": bytes.fromhex("97080500"),
    "s8036_ili9881_fc": bytes.fromhex("97f80400"),
}
STAMP = 0x5F0A6C39

# liblzma LZMA1EXT encoder via ctypes: known size in header, no end-of-payload marker (as in the original stream)
import ctypes.util
import ctypes
_LZMA = None


def load_liblzma():
    """Load a liblzma >= 5.4 (needs the LZMA1EXT raw filter). Search: $LZMA_DLL, tools/../bin, common Windows/macOS/Linux spots."""
    global _LZMA
    if _LZMA is not None:
        return _LZMA
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [os.environ.get("LZMA_DLL")]
    for d in (os.path.join(here, "..", "bin"), os.path.join(here, "bin"), here, os.getcwd()):
        cands += [os.path.join(d, n) for n in ("liblzma.dll", "liblzma-5.dll", "liblzma.so.5", "liblzma.dylib")]
    cands += [ctypes.util.find_library("lzma"), "liblzma.dll", "liblzma-5.dll",
              r"C:\Program Files\Git\mingw64\bin\liblzma-5.dll", r"C:\msys64\mingw64\bin\liblzma-5.dll",
              "/opt/homebrew/lib/liblzma.dylib", "/usr/local/lib/liblzma.dylib", "liblzma.so.5"]
    tried = []
    for c in cands:
        if not c:
            continue
        try:
            lib = ctypes.CDLL(c)
            lib.lzma_version_string.restype = ctypes.c_char_p
            ver = lib.lzma_version_string().decode()
        except (OSError, AttributeError):
            tried.append(c)
            continue
        major, minor = (int(x) for x in ver.split(".")[:2])
        if (major, minor) < (5, 4):
            tried.append(f"{c} (version {ver} < 5.4)")
            continue
        _LZMA = lib
        _LZMA.found_path = c
        _LZMA.found_version = ver
        return lib
    sys.exit("liblzma >= 5.4 not found (needed for LZMA1EXT). Put liblzma.dll next to the tools in ..\\bin\\ "
             "or set LZMA_DLL. Tried: " + "; ".join(tried))
class Opt(ctypes.Structure):
    _fields_=[('dict_size',ctypes.c_uint32),('preset_dict',ctypes.c_void_p),('preset_dict_size',ctypes.c_uint32),
    ('lc',ctypes.c_uint32),('lp',ctypes.c_uint32),('pb',ctypes.c_uint32),('mode',ctypes.c_int),('nice_len',ctypes.c_uint32),
    ('mf',ctypes.c_int),('depth',ctypes.c_uint32),('ext_flags',ctypes.c_uint32),('ext_size_low',ctypes.c_uint32),('ext_size_high',ctypes.c_uint32),
    ('r4',ctypes.c_uint32),('r5',ctypes.c_uint32),('r6',ctypes.c_uint32),('r7',ctypes.c_uint32),('r8',ctypes.c_uint32),
    ('e1',ctypes.c_int),('e2',ctypes.c_int),('e3',ctypes.c_int),('e4',ctypes.c_int),('p1',ctypes.c_void_p),('p2',ctypes.c_void_p)]
class Filter(ctypes.Structure): _fields_=[('id',ctypes.c_uint64),('options',ctypes.c_void_p)]
class Stream(ctypes.Structure):
    _fields_=[('next_in',ctypes.c_void_p),('avail_in',ctypes.c_size_t),('total_in',ctypes.c_uint64),('next_out',ctypes.c_void_p),('avail_out',ctypes.c_size_t),('total_out',ctypes.c_uint64),('allocator',ctypes.c_void_p),('internal',ctypes.c_void_p)]+[('rp%d'%i,ctypes.c_void_p) for i in range(4)]+[('ri%d'%i,ctypes.c_uint64) for i in range(4)]+[('rs%d'%i,ctypes.c_size_t) for i in range(2)]+[('re%d'%i,ctypes.c_int) for i in range(2)]
def compress(data,dict_size,lc,lp,pb,preset=6):
    L=load_liblzma()
    o=Opt(); assert L.lzma_lzma_preset(ctypes.byref(o),preset)==0
    o.dict_size=dict_size;o.lc=lc;o.lp=lp;o.pb=pb;o.ext_flags=0
    o.ext_size_low=len(data)&0xffffffff;o.ext_size_high=len(data)>>32
    f=(Filter*2)(Filter(0x4000000000000002,ctypes.cast(ctypes.byref(o),ctypes.c_void_p)),Filter(0xffffffffffffffff,None))
    s=Stream(); r=L.lzma_raw_encoder(ctypes.byref(s),f); assert r==0,r
    inb=ctypes.create_string_buffer(bytes(data),len(data)); out=ctypes.create_string_buffer(len(data)+65536)
    s.next_in=ctypes.cast(inb,ctypes.c_void_p);s.avail_in=len(data);s.next_out=ctypes.cast(out,ctypes.c_void_p);s.avail_out=len(out)
    r=L.lzma_code(ctypes.byref(s),3)  # LZMA_FINISH
    assert r==1,r  # LZMA_STREAM_END
    n=s.total_out; L.lzma_end(ctypes.byref(s))
    props=(pb*5+lp)*9+lc
    return bytes([props])+struct.pack('<IQ',dict_size,len(data))+out.raw[:n]



def items(img):
    out = {}
    for i in range(struct.unpack_from("<I", img, 60)[0]):
        rec = img[(i + 1) * 1024:(i + 2) * 1024]
        nl = struct.unpack_from("<I", rec)[0]
        name = rec[36:36 + nl].split(b"\0")[0].decode()
        out[name] = (struct.unpack_from("<I", rec, 52 + nl)[0], struct.unpack_from("<I", rec, 44 + nl)[0])
    return out


def wsum(b):
    return sum(struct.unpack_from(f"<{len(b) // 4}I", b)) & 0xFFFFFFFF


def jal_x0(src, dst):
    o = dst - src
    assert -(1 << 20) <= o < (1 << 20) and o % 2 == 0
    imm = o & 0x1FFFFF
    w = ((imm >> 20) & 1) << 31 | ((imm >> 1) & 0x3FF) << 21 | ((imm >> 11) & 1) << 20 | ((imm >> 12) & 0xFF) << 12 | 0x6F
    return struct.pack("<I", w)


# --- optional: replace the ili9881_inx_f101a35 init routine with a table-driven ILI9881C init ---
ILI_FN = (0x400810AE, 0x40081F94)          # vendor init routine called by that branch (a0 = sel)
ILI_FN_HEAD = bytes.fromhex("130101cb")     # addi sp,sp,-0x350
DCS_WR = 0x4007C71E                         # (sel, cmd, u8 *para, u32 n)
DELAY_MS = 0x4007C51C                       # (ms)
SET_MRPS = 0x4007C6CA                       # (sel, n) set maximum return packet size (thunk; true address 0x400cc6ca)
DCS_RD = 0x4007C6DE                         # (sel, reg, u8 *buf, int *num) -> 0 ok   (thunk; true address 0x400cc6de)
PRINTF = 0x4001FBB6                         # kernel printf (call target of the 'mipi id read ok' print; true 0x4006fbb6)
FMT_MIPI_ID = 0x400F4F68                    # "mipi id read ok: num %d [0x%x 0x%x 0x%x 0x%x]" (true 0x40144f68)
HS_ON = 0x4007C6B8                          # (sel), called by the vendor routine after display on
AUTO_MIPI_TIMING = 0x10E7F0                 # file offset: dclk,x,y,ht,vt,hbp,vbp,hspw,vspw (u16; memcpy'd at 0x400cc3ba, fields stored at 0x400c834e)
AUTO_MIPI_TIMING_ORIG = (73, 800, 1280, 890, 1340, 25, 20, 20, 4)
LLVM = os.environ.get("LLVM_BIN", "/opt/homebrew/opt/llvm/bin")
LLD = os.environ.get("LLD_BIN", "/opt/homebrew/opt/lld/bin")


def linux_table(path, name):
    import re
    src = open(path).read()
    m = re.search(r"static const struct ili9881c_instr %s_init\[\] = \{(.*?)\n\};" % re.escape(name), src, re.S)
    if not m:
        sys.exit(f"table {name}_init not found")
    out = []
    for op, args in re.findall(r"ILI9881C_(SWITCH_PAGE|COMMAND)_INSTR\(([^)]*)\)", m.group(1)):
        names = {"MIPI_DCS_WRITE_CONTROL_DISPLAY": 0x53, "MIPI_DCS_WRITE_POWER_SAVE": 0x55}
        v = [names[x.strip()] if x.strip() in names else int(x.strip(), 0) for x in args.split(",")]
        if op == "COMMAND" and v[0] == 0xFF:
            sys.exit("table uses register 0xFF directly; marker would clash")
        out.append((0xFF, v[0]) if op == "SWITCH_PAGE" else (v[0], v[1]))
    return out


PRE_DELAY_MS = 0   # optional settle delay before the first DCS command (--pre-delay-ms)
DUMP_REGS = False   # read-only diagnostic: dump panel registers of pages 0-7 to the UART before the normal init (--dump-regs)


DUMP_BLOCK = """    li a0, 20
    call DELAY_MS
    mv a0, s0
    li a1, 1
    call SET_MRPS
    li s3, 0
page_loop:
    li t0, 0x98
    sb t0, 0(sp)
    li t0, 0x81
    sb t0, 1(sp)
    sb s3, 2(sp)
    mv a0, s0
    li a1, 0xff
    mv a2, sp
    li a3, 3
    call DCS_WR
    li a0, 10
    call DELAY_MS
    li s4, 0
reg_loop:
    sb zero, 12(sp)
    sw zero, 8(sp)
    mv a0, s0
    mv a1, s4
    addi a2, sp, 12
    addi a3, sp, 8
    call DCS_RD
    lbu a3, 12(sp)
    lw a5, 8(sp)
    mv a4, a0
    addi a1, s3, 1000
    mv a2, s4
    la a0, FMT_MIPI_ID
    call PRINTF
    addi s4, s4, 1
    li t0, 256
    bne s4, t0, reg_loop
    addi s3, s3, 1
    li t0, 8
    bne s3, t0, page_loop
"""

def build_ili_fn(table):
    """Return machine code for the replacement init routine (0xFF entries = page switch FF 98 81 xx)."""
    import subprocess, tempfile
    PAD = (-ILI_FN[0]) % 4
    pre = f"    li a0, {PRE_DELAY_MS}\n    call DELAY_MS\n" if PRE_DELAY_MS else ""
    dump = DUMP_BLOCK if DUMP_REGS else ""
    asm = f"""
    .option norvc
    .text
    .globl _start
_start:
    addi sp, sp, -32
    sw ra, 28(sp)
    sw s0, 24(sp)
    sw s1, 20(sp)
    sw s2, 16(sp)
    mv s0, a0
{pre}{dump}    la s1, table
    li s2, {len(table)}
loop:
    beqz s2, done
    lbu t0, 0(s1)
    lbu t1, 1(s1)
    li t2, 0xff
    bne t0, t2, single
    li t3, 0x98
    sb t3, 0(sp)
    li t3, 0x81
    sb t3, 1(sp)
    sb t1, 2(sp)
    mv a0, s0
    li a1, 0xff
    mv a2, sp
    li a3, 3
    call DCS_WR
    j next
single:
    sb t1, 0(sp)
    mv a0, s0
    mv a1, t0
    mv a2, sp
    li a3, 1
    call DCS_WR
next:
    addi s1, s1, 2
    addi s2, s2, -1
    j loop
done:
    li t3, 0x98
    sb t3, 0(sp)
    li t3, 0x81
    sb t3, 1(sp)
    sb zero, 2(sp)
    mv a0, s0
    li a1, 0xff
    mv a2, sp
    li a3, 3
    call DCS_WR
    sb zero, 0(sp)
    mv a0, s0
    li a1, 0x35
    mv a2, sp
    li a3, 1
    call DCS_WR
    mv a0, s0
    li a1, 0x11
    mv a2, sp
    li a3, 0
    call DCS_WR
    li a0, 120
    call DELAY_MS
    mv a0, s0
    li a1, 0x29
    mv a2, sp
    li a3, 0
    call DCS_WR
    li a0, 20
    call DELAY_MS
    mv a0, s0
    call HS_ON
    li a0, 20
    call DELAY_MS
    lw ra, 28(sp)
    lw s0, 24(sp)
    lw s1, 20(sp)
    lw s2, 16(sp)
    addi sp, sp, 32
    ret
table:
    .byte {", ".join(f"{c:#x}, {d:#x}" for c, d in table)}
"""
    if DUMP_REGS:
        pro = "    addi sp, sp, -32\n    sw ra, 28(sp)\n    sw s0, 24(sp)\n    sw s1, 20(sp)\n    sw s2, 16(sp)\n"
        epi = "    lw ra, 28(sp)\n    lw s0, 24(sp)\n    lw s1, 20(sp)\n    lw s2, 16(sp)\n    addi sp, sp, 32\n    ret\n"
        assert pro in asm and epi in asm
        asm = asm.replace(pro, "    addi sp, sp, -64\n    sw ra, 60(sp)\n    sw s0, 56(sp)\n    sw s1, 52(sp)\n    sw s2, 48(sp)\n    sw s3, 44(sp)\n    sw s4, 40(sp)\n")
        asm = asm.replace(epi, "    lw ra, 60(sp)\n    lw s0, 56(sp)\n    lw s1, 52(sp)\n    lw s2, 48(sp)\n    lw s3, 44(sp)\n    lw s4, 40(sp)\n    addi sp, sp, 64\n    ret\n")
    SYMS = {"DCS_WR": DCS_WR, "DELAY_MS": DELAY_MS, "HS_ON": HS_ON, "SET_MRPS": SET_MRPS, "DCS_RD": DCS_RD,
            "PRINTF": PRINTF, "FMT_MIPI_ID": FMT_MIPI_ID}
    if os.environ.get("USE_LLVM") == "1":      # optional cross-check backend (needs llvm-mc, ld.lld, llvm-objcopy)
        with tempfile.TemporaryDirectory() as td:
            open(f"{td}/a.s", "w").write(asm)
            run = lambda *c: subprocess.run(c, check=True, capture_output=True)
            run(f"{LLVM}/llvm-mc", "-triple=riscv32", "-mattr=+m", "-filetype=obj", f"{td}/a.s", "-o", f"{td}/a.o")
            run(f"{LLD}/ld.lld", "-m", "elf32lriscv", "--no-relax", f"-Ttext={ILI_FN[0] + PAD:#x}", "-e", "_start",
                *[f"--defsym={k}={v:#x}" for k, v in SYMS.items()],
                f"{td}/a.o", "-o", f"{td}/a.elf")
            run(f"{LLVM}/llvm-objcopy", "-O", "binary", "--only-section=.text", f"{td}/a.elf", f"{td}/a.bin")
            code = open(f"{td}/a.bin", "rb").read()
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import rv32asm
        code = rv32asm.assemble(asm, ILI_FN[0] + PAD, SYMS)
    code = bytes.fromhex("0100") * (PAD // 2) + code   # c.nop pad so the 4-aligned link address matches placement
    if len(code) > ILI_FN[1] - ILI_FN[0]:
        sys.exit(f"init routine too large: {len(code)}")
    return code, asm


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("branch", choices=sorted(BRANCHES))
    ap.add_argument("--output", required=True)
    ap.add_argument("--linux-source", help="panel-ilitek-ili9881c.c from Linux (with --ili9881-table)")
    ap.add_argument("--ili9881-table", help="Linux table name, e.g. k101_im2byl02; replaces the ili9881_inx_f101a35 routine")
    ap.add_argument("--diag-id", action="store_true",
                    help="diagnostic: keep normal ID detection, but send only this branch's ID to the nt35521 init "
                         "(black screen on this panel) so the screen tells whether the panel reports that ID")
    ap.add_argument("--timing", help="auto_mipi timing, sunxi convention: dclk,ht,hbp,hspw,vt,vbp,vspw (hbp/vbp include sync)")
    ap.add_argument("--dump-regs", action="store_true", help="read-only diagnostic: dump panel registers (pages 0-7) to the UART before init")
    ap.add_argument("--pre-delay-ms", type=int, default=0, help="delay before the first DCS command of the replaced routine")
    ap.add_argument("--keep-detect", action="store_true",
                    help="do not force the branch: keep normal ID detection (only the 1C routine/timing are replaced)")
    a = ap.parse_args()
    if a.ili9881_table and (a.branch != "ili9881_inx_f101a35" or not a.linux_source):
        sys.exit("--ili9881-table needs branch ili9881_inx_f101a35 and --linux-source")
    if os.path.exists(a.output):
        sys.exit("output exists; choose a new path")
    img = bytearray(open(a.image, "rb").read())
    it = items(img)
    poff, plen = it["melis_pkg_nor.fex"]
    voff, _ = it["Vmelis_pkg_nor.fex"]
    pkg = bytearray(img[poff:poff + plen])
    if wsum(pkg) != struct.unpack_from("<I", img, voff)[0]:
        sys.exit("input Vmelis mismatch")
    if pkg[0x40:0x4A] != b"melis-lzma":
        sys.exit("unexpected package layout")
    koff, klen = struct.unpack_from("<II", pkg, 0x80)
    # next item start bounds the space for the compressed kernel
    # item records: name at 0x40 + 0x170*i, (offset, length) at name + 0x40
    nxt = min(struct.unpack_from("<I", pkg, 0x80 + 0x170 * i)[0] for i in (1, 2))
    if pkg[0x1B0:0x1BC] != b"melis-config" or not koff + klen <= nxt:
        sys.exit("unexpected package item table")
    props = pkg[koff]; dic = struct.unpack_from("<I", pkg, koff + 1)[0]
    kern = bytearray(lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(bytes(pkg[koff:koff + klen])))
    if hashlib.sha256(kern).hexdigest() != KERNEL_SHA:
        sys.exit("kernel is not the 16.10 seller kernel")
    if a.diag_id:
        if a.branch == "nt35521" or a.ili9881_table or a.timing:
            sys.exit("--diag-id takes an ILI/JD9366 branch and no other changes")
        src = BRANCHES[a.branch]
        s = src - BASE
        if kern[s:s + 4] != BRANCH_HEAD[a.branch]:
            sys.exit("branch entry bytes differ")
        kern[s:s + 4] = jal_x0(src, BRANCHES["nt35521"])
        jump = f"{src:#x} -> {BRANCHES['nt35521']:#x} (diag-id)"
    elif a.keep_detect:
        if kern[SITE - BASE:SITE - BASE + 4] != SITE_BYTES:
            sys.exit("patch site bytes differ")
        jump = "none (ID detection kept)"
    else:
        s = SITE - BASE
        if kern[s:s + 4] != SITE_BYTES:
            sys.exit("patch site bytes differ")
        kern[s:s + 4] = jal_x0(SITE, BRANCHES[a.branch])
        jump = f"{SITE:#x} -> {BRANCHES[a.branch]:#x}"
    extra = {}
    if a.ili9881_table:
        f0, f1 = ILI_FN[0] - BASE, ILI_FN[1] - BASE
        if kern[f0:f0 + 4] != ILI_FN_HEAD or kern[f1 - 2:f1] != bytes.fromhex("8280"):
            sys.exit("vendor ILI routine bounds differ")
        table = linux_table(a.linux_source, a.ili9881_table)
        globals()["PRE_DELAY_MS"] = a.pre_delay_ms
        globals()["DUMP_REGS"] = a.dump_regs
        code, asm = build_ili_fn(table)
        kern[f0:f1] = code + b"\0" * (f1 - f0 - len(code))
        os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
        open(a.output + ".s", "w").write(asm)
        extra.update(table=a.ili9881_table, table_entries=len(table), code_len=len(code),
                     linux_source_sha256=hashlib.sha256(open(a.linux_source, "rb").read()).hexdigest())
    if a.timing:
        dclk, ht, hbp, hspw, vt, vbp, vspw = (int(x) for x in a.timing.split(","))
        cur = struct.unpack_from("<9H", kern, AUTO_MIPI_TIMING)
        if cur != AUTO_MIPI_TIMING_ORIG:
            sys.exit(f"auto_mipi timing differs: {cur}")
        new = (dclk, 800, 1280, ht, vt, hbp, vbp, hspw, vspw)
        if vbp - vspw <= 3:
            sys.exit("kernel rejects vbp - vspw <= 3 (check at 0x400dddc2)")
        if hbp <= hspw:
            sys.exit("hbp must be > hspw (sunxi convention: hbp includes the sync width; reported TCON hang otherwise)")
        struct.pack_into("<9H", kern, AUTO_MIPI_TIMING, *new)
        extra["timing"] = dict(zip("dclk x y ht vt hbp vbp hspw vspw".split(), new))
    lc = props % 9; lp = (props // 9) % 5; pb = props // 45
    comp = compress(bytes(kern), dic, lc, lp, pb)
    dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    if dec.decompress(comp) != bytes(kern) or not dec.eof or dec.unused_data:
        sys.exit("recompressed kernel does not round-trip")
    if koff + len(comp) > nxt:
        sys.exit(f"compressed kernel too large: {len(comp)} > {nxt - koff}")
    pkg[koff:nxt] = bytes(comp) + b"\0" * (nxt - koff - len(comp))
    struct.pack_into("<I", pkg, 0x84, len(comp))
    length = struct.unpack_from("<I", pkg, 0x24)[0]
    tmp = bytearray(pkg[:length]); struct.pack_into("<I", tmp, 0x14, STAMP)
    struct.pack_into("<I", pkg, 0x14, wsum(tmp))
    img[poff:poff + plen] = pkg
    struct.pack_into("<I", img, voff, wsum(pkg))
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    open(a.output, "wb").write(img)
    rep = {"source": a.image, "source_sha256": hashlib.sha256(open(a.image, "rb").read()).hexdigest(),
           "output": a.output, "output_sha256": hashlib.sha256(img).hexdigest(), "branch": a.branch,
           "jump": jump, "kernel_patched_sha256": hashlib.sha256(kern).hexdigest(),
           "compressed_len": len(comp), "original_compressed_len": klen, "space": nxt - koff, **extra}
    open(a.output + ".json", "w").write(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
