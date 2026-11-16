#!/usr/bin/env python3
"""Apply one table from the panel corpus (work/panel-lab-*/corpus.json) as the ili9881_inx_f101a35
(ID 98 81 1C) init routine of the 16.10 seller kernel. Host-side only; reuses force_auto_mipi_branch."""
import importlib.util, json, os, sys

here = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("fab", os.path.join(here, "force_auto_mipi_branch.py"))
fab = importlib.util.module_from_spec(sp); sp.loader.exec_module(fab)


def corpus_table(path, name):
    pk = json.load(open(path))[name]["packets"]
    out = []
    for p in pk:
        if p[0] == 0xFF:
            if p[1:3] != [0x98, 0x81] or len(p) != 4:
                sys.exit(f"unexpected 0xFF packet {p}")
            out.append((0xFF, p[3]))
        elif len(p) == 2:
            out.append((p[0], p[1]))
        else:
            sys.exit(f"unsupported packet {p}")
    return out


if __name__ == "__main__":
    # usage: apply_corpus_table.py IMAGE CORPUS.json TABLE OUTPUT [extra force args]
    img, corpus, name, out, *extra = sys.argv[1:]
    fab.linux_table = lambda p, n: corpus_table(p, n)
    sys.argv = ["force", img, "ili9881_inx_f101a35", "--output", out,
                "--linux-source", corpus, "--ili9881-table", name, *extra]
    fab.main()
