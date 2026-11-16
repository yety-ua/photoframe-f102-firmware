#!/usr/bin/env python3
"""Parse a PuTTY/UART boot log that contains the panel register dump (image built with --dump-regs).

Dump lines look like  'mipi id read ok: num 1006 [0xf2 0x1a 0x0 0x1]'  =  page = num-1000, then [reg value rc count].
Prints: how many registers were read, panel ID bytes, ILI9881D revision hint (page 6 F0..F3), non-zero counts per page,
and how well every table in the corpus matches the registers actually read from the panel. Writes <log>.dump.json and
<log>.dump.txt next to the log. Stdlib only. Usage: parse_regdump.py LOG [--corpus data/corpus.json]
"""
import argparse, json, os, re, sys

LINE = re.compile(r"mipi id read ok: num (\d+) \[0x([0-9a-fA-F]+) 0x([0-9a-fA-F]+) 0x([0-9a-fA-F]+) 0x([0-9a-fA-F]+)\]")


def load(path):
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", open(path, "rb").read().decode("latin-1")).replace("\r", "")
    dump, ids = {}, []
    for m in LINE.finditer(text):
        num, a, b, c, d = int(m.group(1)), *(int(x, 16) for x in m.groups()[1:])
        if num >= 1000:
            dump[(num - 1000, a)] = (b, c, d)        # last occurrence wins (log may hold several boots)
        else:
            ids.append((num, a, b, c, d))
    return dump, ids


def table_writes(packets):
    page, out = 0, {}
    for p in packets:
        if p[0] == 0xFF and len(p) == 4 and p[1:3] == [0x98, 0x81]:
            page = p[3]
        elif len(p) == 2:
            out[(page, p[0])] = p[1]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("log")
    ap.add_argument("--corpus", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "corpus.json"))
    a = ap.parse_args()
    dump, ids = load(a.log)
    if not dump:
        sys.exit("no register-dump lines (num >= 1000) found: was the --dump-regs image flashed and the log captured from power-on?")
    ok = {k: v for k, v in dump.items() if v[1] == 0 and v[2] == 1}
    print(f"dump lines: {len(dump)} registers, {len(ok)} read OK (rc=0, 1 byte), {len(dump) - len(ok)} failed/odd")
    print("ID reads before the dump (num [b0 b1 b2 b3]):", ids)
    g = lambda p, r: ok.get((p, r), (None,))[0]
    pid = [g(1, 0), g(1, 1), g(1, 2)]
    print("page 1 regs 00..02 (chip ID):", [None if x is None else f"{x:02x}" for x in pid])
    rev = [g(6, 0xF0 + i) for i in range(4)]
    print("page 6 regs F0..F3 (Seeed revision bytes):", [None if x is None else f"{x:02x}" for x in rev],
          "->", {0x0D: "ILI9881D02", 0x1A: "ILI9881D03"}.get(rev[2], "not D02/D03 (or unreadable)"))
    pages = sorted({p for p, _ in dump})
    for p in pages:
        vals = [ok[(p, r)][0] for r in range(256) if (p, r) in ok]
        print(f"page {p}: read {len(vals)}/256, non-zero {sum(1 for v in vals if v)}, distinct values {len(set(vals))}")
    lines = []
    for p in pages:
        lines.append(f"== page {p}")
        for r0 in range(0, 256, 16):
            lines.append(f"{r0:02x}: " + " ".join(f"{ok[(p, r0 + i)][0]:02x}" if (p, r0 + i) in ok else "--" for i in range(16)))
    base = os.path.splitext(a.log)[0]
    open(base + ".dump.txt", "w").write("\n".join(lines) + "\n")
    json.dump({f"{p}:{r:02x}": v for (p, r), v in sorted(dump.items())}, open(base + ".dump.json", "w"))
    print("wrote", base + ".dump.txt", "and", base + ".dump.json")
    if os.path.exists(a.corpus):
        corpus = json.load(open(a.corpus)); scores = []
        for name, t in corpus.items():
            w = table_writes(t["packets"]); cmp = [(k, v) for k, v in w.items() if k in ok]
            if cmp:
                same = sum(1 for k, v in cmp if ok[k][0] == v)
                scores.append((same / len(cmp), same, len(cmp), len(w), name))
        print("\ncorpus tables vs registers read from the panel (matches / comparable writes):")
        for r, same, n, tot, name in sorted(scores, reverse=True)[:10]:
            print(f"  {r:6.1%}  {same:4d}/{n:<4d} (table has {tot} writes)  {name}")
        print("note: registers at their reset default match tables that happen to write the default; a table that matches"
              " far more than the others suggests the panel's OTP/init resembles it.")


if __name__ == "__main__":
    main()
