#!/usr/bin/env python3
"""Build one firmware variant from a base image (host-side only; never flashes anything).

Stages (each writes a NEW file; the base is never modified):
  1. kernel patch  : --table [--timing ...] [--pre-delay-ms N]   (force_auto_mipi_branch via apply_corpus_table)
                     or --timing alone (keeps the stock init routine)
  2. config values : --set key=value ...                          (set_config_u32; e.g. lcd_dsi_if=2)
  3. panel driver  : --driver NAME                                (set_lcd_driver; name must exist in the kernel)
Then verify_variant.py runs against the base, and SHA256SUMS + a manifest are written to out/<name>/.
Example:
  python tools\\make_variant.py --name v12f1 --table jieli_ac792_ili9881c_800x1280 --timing 72,908,56,8,1317,22,6
Timing is dclk,ht,hbp,hspw,vt,vbp,vspw (x=800, y=1280 fixed); the tool stores it in the kernel's own field order.

Per-frame builds (two frames, same board, different LCD panels; profiles in data/frames.json):
  python tools\\make_variant.py --frame 1 --name ui_v12 [--base NEW_UI_IMAGE.img]   frame 1: stock kernel, no panel patch
  python tools\\make_variant.py --frame 2 --name ui_v12 [--base NEW_UI_IMAGE.img]   frame 2: stock kernel + the proven panel recipe
--frame accepts any UI build as base as long as its kernel and config are the stock 16.10 ones; output goes to out/F<n>_<name>/.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, ".."))
BASE_DEFAULT = os.path.join(KIT, "..", "firmware", "F1_v11k_current_frame1", "smartframe.img")
BASE_SHA = "784eb0582048ad1a203c709ab5a0a38d32758380b527c8732ec7ac9d36036d81"
CORPUS = os.path.join(KIT, "data", "corpus.json")
FRAMES = os.path.join(KIT, "data", "frames.json")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run(*cmd):
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"step failed: {' '.join(cmd)}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", help="variant name (output folder out/<name>/)")
    ap.add_argument("--base", default=BASE_DEFAULT, help="base smartframe.img (default: v11k from ../firmware)")
    ap.add_argument("--table", help="table name from data/corpus.json (see --list-tables)")
    ap.add_argument("--timing", help="dclk,ht,hbp,hspw,vt,vbp,vspw")
    ap.add_argument("--pre-delay-ms", type=int, default=0)
    ap.add_argument("--dump-regs", action="store_true", help="read-only diagnostic: dump panel registers (pages 0-7) to the UART before init (needs --table)")
    ap.add_argument("--no-keep-detect", action="store_true", help="force the 98 81 1C branch instead of keeping ID auto-detect (frame 2 only!)")
    ap.add_argument("--set", nargs="*", default=[], metavar="key=value", help="numeric config keys, e.g. lcd_dsi_if=2")
    ap.add_argument("--driver", help="switch lcd_driver_name (name must be registered in the kernel)")
    ap.add_argument("--frame", choices=["1", "2"], help="build for a frame profile (data/frames.json): 1 = stock kernel, 2 = proven panel recipe")
    ap.add_argument("--list-tables", action="store_true")
    ap.add_argument("--allow-other-base", action="store_true", help="skip the v11k base hash check")
    a = ap.parse_args()
    if a.list_tables:
        c = json.load(open(CORPUS))
        for k, v in c.items():
            print(f"{k:42s} {len(v['packets']):4d} packets  {v.get('note', '')}")
        return
    if not a.name:
        sys.exit("--name is required")
    prof = None
    if a.frame:
        if any([a.table, a.timing, a.pre_delay_ms, a.set, a.driver, a.dump_regs, a.no_keep_detect]):
            sys.exit("--frame builds the frame's profile as is; do not combine it with patch options (experiments: run without --frame)")
        prof = json.load(open(FRAMES)); fr = prof["frames"][a.frame]
        if fr["recipe"]:
            a.table, a.timing = fr["recipe"]["table"], fr["recipe"]["timing"]
        a.allow_other_base = True          # any UI build is fine; the stock-kernel/config check below decides
    elif not any([a.table, a.timing, a.pre_delay_ms, a.set, a.driver]):
        sys.exit("nothing to change: give --table/--timing/--pre-delay-ms/--set/--driver (or --frame 1|2)")
    if a.dump_regs and not a.table:
        sys.exit("--dump-regs applies to a replaced init routine: use it together with --table")
    if a.pre_delay_ms and not a.table:
        sys.exit("--pre-delay-ms applies to a replaced init routine: use it together with --table")
    base = os.path.abspath(a.base)
    if not os.path.isfile(base):
        sys.exit(f"base image not found: {base}")
    if sha(base) != BASE_SHA and not a.allow_other_base:
        sys.exit(f"base sha256 {sha(base)} is not the frozen v11k ({BASE_SHA}); use --allow-other-base to override")
    out = os.path.join(KIT, "out", (f"F{a.frame}_" if a.frame else "") + a.name)
    if a.frame:
        stock = os.path.abspath(os.path.join(KIT, "..", prof["stock_image"]["path"]))
        if not os.path.isfile(stock) or sha(stock) != prof["stock_image"]["sha256"]:
            sys.exit(f"stock seller image missing or wrong hash: {stock}")
        chk = subprocess.run([sys.executable, os.path.join(HERE, "verify_variant.py"), base, "--frame", "1", "--stock", stock], capture_output=True, text=True)
        if chk.returncode:
            sys.exit("base is not a stock-kernel UI image (kernel/config already patched?), so a frame profile cannot be applied cleanly:\n" + chk.stdout[-800:])
    if os.path.exists(out):
        sys.exit(f"{out} exists; choose a new --name (nothing is overwritten)")
    os.makedirs(out)
    try:
        build(a, base, out)
    except BaseException:
        shutil.rmtree(out, ignore_errors=True)      # our own fresh folder only; never leave half-built variants
        raise


def build(a, base, out):
    stage_dir = os.path.join(out, "_stages"); os.makedirs(stage_dir)
    cur, n, log = base, 0, []
    if a.table or a.timing:
        n += 1; nxt = os.path.join(stage_dir, f"s{n}.img")
        extra = [] if a.no_keep_detect else ["--keep-detect"]
        if a.timing:
            if len(a.timing.split(",")) != 7:
                sys.exit("--timing needs 7 numbers: dclk,ht,hbp,hspw,vt,vbp,vspw")
            extra += ["--timing", a.timing]
        if a.pre_delay_ms:
            extra += ["--pre-delay-ms", str(a.pre_delay_ms)]
        if a.dump_regs:
            extra += ["--dump-regs"]
        if a.table:
            run(os.path.join(HERE, "apply_corpus_table.py"), cur, CORPUS, a.table, nxt, *extra)
        else:
            run(os.path.join(HERE, "force_auto_mipi_branch.py"), cur, "ili9881_inx_f101a35", "--output", nxt, *extra)
        cur = nxt; log.append(f"kernel patch: table={a.table} timing={a.timing} pre_delay={a.pre_delay_ms}")
    if a.set:
        n += 1; nxt = os.path.join(stage_dir, f"s{n}.img")
        run(os.path.join(HERE, "set_config_u32.py"), cur, *a.set, "--output", nxt)
        cur = nxt; log.append(f"config: {' '.join(a.set)}")
    if a.driver:
        n += 1; nxt = os.path.join(stage_dir, f"s{n}.img")
        run(os.path.join(HERE, "set_lcd_driver.py"), cur, a.driver, "--output", nxt)
        cur = nxt; log.append(f"driver: {a.driver}")
    final = os.path.join(out, "smartframe.img")
    shutil.copyfile(cur, final)
    shutil.rmtree(stage_dir)
    vcmd = [sys.executable, os.path.join(HERE, "verify_variant.py"), final, "--base", base]
    if a.frame:
        fr = json.load(open(FRAMES))["frames"][a.frame]
        stock = os.path.abspath(os.path.join(KIT, "..", json.load(open(FRAMES))["stock_image"]["path"]))
        vcmd += ["--frame", a.frame, "--stock", stock]
        if fr["recipe"]:
            vcmd += ["--recipe-timing", fr["recipe"]["timing"]]
    v = subprocess.run(vcmd, capture_output=True, text=True)
    open(os.path.join(out, "verify.txt"), "w").write(v.stdout + v.stderr)
    h = sha(final)
    open(os.path.join(out, "SHA256SUMS"), "w").write(f"{h}  smartframe.img\n")
    json.dump({"name": a.name, "frame": a.frame, "base": base, "base_sha256": sha(base), "steps": log, "sha256": h,
               "args": vars(a), "verify_exit": v.returncode}, open(os.path.join(out, "manifest.json"), "w"), indent=2)
    print(v.stdout)
    print(f"output  : {final}\nsha256  : {h}")
    if v.returncode:
        os.rename(final, final + ".FAILED_VERIFY_DO_NOT_FLASH")
        print("VERIFY FAILED: do not flash this image (renamed *.FAILED_VERIFY_DO_NOT_FLASH)")
        return
    if a.frame:
        fr = json.load(open(FRAMES))["frames"][a.frame]
        print(f"*** FLASH ONLY ON FRAME {a.frame}: panel {fr['panel']} ***")
    print("Check the hash before flashing:  Get-FileHash", final, "-Algorithm SHA256")


if __name__ == "__main__":
    main()
