#!/usr/bin/env python3
"""Add the Seeed ili9881x tables (ILI9881D02, ILI9881D03, ILI9881C05) and an 'OTP only' empty table to a panel corpus.

Multi-parameter writes (D03 gamma 0xA0/0xC0 with 20 bytes) are expanded to consecutive single-register writes
(reg+i <- byte i), the only form the replacement init routine supports. Page-0 0x10/0x11/0x28/0x29 are dropped
(the routine sends its own sleep-out/display-on). Source files are read as text only.
usage: add_seeed_x_tables.py CORPUS.json SEEED_ILI9881X.c OUTPUT.json
"""
import hashlib, json, re, sys

H = lambda s: int(s.strip(), 0)


def parse(src):
    out = {}
    for m in re.finditer(r"static void (ili9881\w+)_init\(struct mipi_dsi_device \*dsi\)\s*\{(.*?)\n\}", src, re.S):
        name, body = m.groups(); pk = []; page = None
        for line in body.splitlines():
            line = line.split("//")[0].strip()
            mm = re.match(r"ILI9881_PAGE\((\w+)\);", line)
            if mm:
                page = H(mm.group(1)); pk.append([0xFF, 0x98, 0x81, page]); continue
            mm = re.match(r"ILI9881_COMMAND\((.*)\);", line)
            if not mm:
                continue
            v = [H(x) for x in mm.group(1).split(",")]
            if len(v) == 1:                      # bare command (0x11 / 0x29)
                continue
            if page == 0 and v[0] in (0x10, 0x11, 0x28, 0x29):
                continue
            if len(v) == 2:
                pk.append(v)
            else:                                # multi-parameter: consecutive registers
                pk += [[v[0] + i, b] for i, b in enumerate(v[1:])]
        while pk and pk[-1][0] == 0xFF:
            pk.pop()
        out[name] = pk
    return out


def main():
    corpus, src_path, out_path = sys.argv[1:4]
    c = json.load(open(corpus)); raw = open(src_path, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    notes = {"ili9881d02": "Seeed ili9881x D02 (page6 F2=0x0D), 720x1280 source", "ili9881d03": "Seeed ili9881x D03 (page6 F2=0x1A), 720x1280 source, gamma expanded",
             "ili9881c05": "Seeed ili9881x C05 (ID 98 81 5C), 720x1280 source"}
    for k, pk in parse(raw.decode()).items():
        name = "seeed_" + k
        c[name] = {"packets": pk, "source": src_path.split("/")[-1], "sha256": sha, "n_packets": len(pk), "note": notes.get(k, "")}
    c["empty_otp_only"] = {"packets": [], "source": "none", "n_packets": 0, "note": "no table: page 0, TE, sleep out, display on only (tests OTP-programmed panel)"}
    json.dump(c, open(out_path, "w"), indent=1)
    print({k: len(v["packets"]) for k, v in c.items() if k.startswith(("seeed_ili9881", "empty"))})


if __name__ == "__main__":
    main()
