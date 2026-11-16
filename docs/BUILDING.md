# Building images (build kit)

`build_kit/` builds hardware-variant images from an **interface image** (an image that has the seller's kernel and configuration), entirely in Python. It never flashes anything. The same tools run on Windows, macOS and Linux.

What it does **not** do: change the interface itself (icons, language tables, the interface module, the splash). Those parts of an image are produced by separate tools that are not part of this repository; here you start from a finished interface image such as `firmware/custom/variant-a_k101-im2cyl02-l/smartframe.img`.

## One-time setup

1. **Python 3.8 or newer** (64-bit).
2. **liblzma 5.4 or newer**: the only external dependency. The kernel must be recompressed in the LZMA1EXT format (known size, no end marker), which Python's own `lzma` module cannot write.
   - On macOS: `brew install xz` is enough; Linux: the system `liblzma.so.5` (≥ 5.4) is found automatically.
   - On Windows: if Git for Windows provides `C:\Program Files\Git\mingw64\bin\liblzma-5.dll`, it is found automatically. Otherwise download an official xz build for Windows from the xz project's releases page (`xz-<version>-windows.zip`), take `bin_x86-64\liblzma.dll` (or `bin_i686` for 32-bit Python) and put it into `build_kit\bin\`, or point `LZMA_DLL` at it. Use release 5.4.x or 5.6.3 and newer; **do not use 5.6.0 or 5.6.1** (compromised releases). Check the SHA-256 against the release page.
3. Check the setup:
   ```
   python build_kit/tools/check_env.py
   ```
   It must end with `RESULT  : READY`.
4. Run the self-test (it rebuilds known images and compares their hashes):
   ```
   python build_kit/tools/selftest_build.py
   ```
   `RESULT: PASS`. A `WARN` means the bytes differ only because another liblzma version compressed the kernel differently; the images are still valid.

## Build per hardware variant (the normal way)

```
python build_kit/tools/make_variant.py --variant a --name my_build --base my_interface_image.img
python build_kit/tools/make_variant.py --variant b --name my_build --base my_interface_image.img
```

Without `--base` the custom variant A image from `firmware/custom/` is used. Output goes to `build_kit/out/variant-a_<name>/` and `build_kit/out/variant-b_<name>/` with `smartframe.img`, `SHA256SUMS`, `manifest.json` and `verify.txt`.

- **Variant A** = the interface image as it is. The tool only checks that the kernel and configuration are the seller's unmodified ones.
- **Variant B** = the same image with the panel init table `linux_k101_im2byl02_init` and the seller's timing `73,890,25,20,1340,20,4`.
- The check needs the seller's original image as the kernel reference: `firmware/stock/seller-2026-10-16/smartframe.img` (SHA-256 `f9ed6a46…93fa0`).
- A base that already has a patched kernel is rejected.
- The last output line is `*** FLASH ONLY ON VARIANT A/B: panel … ***`. Check the hash before flashing:
  ```
  Get-FileHash build_kit\out\variant-b_my_build\smartframe.img -Algorithm SHA256
  ```
  A `PASS` from the tool only means the structure is correct; whether the image boots is something only the frame shows.

## Experiments (without `--variant`)

| Operation | Option | What changes |
|---|---|---|
| Init table | `--table NAME` | The init routine for panel ID `98 81 1C` (tables in `data/corpus.json`; list with `--list-tables`) |
| Timing | `--timing dclk,ht,hbp,hspw,vt,vbp,vspw` | The `auto_mipi` timing table (x = 800, y = 1280 fixed) |
| Pre-delay | `--pre-delay-ms N` | A pause before the first table command (with `--table`) |
| Config values | `--set key=value ...` | Numeric configuration keys, e.g. `lcd_dsi_if=0` |
| Panel driver | `--driver NAME` | `lcd_driver_name` (the name must be registered in the kernel) |
| Register dump | `--dump-regs` (with `--table`) | Reads panel pages 0–7 over DSI and prints them to the UART before the init; parse with `build_kit/tools/parse_regdump.py LOG` |

Experiment builds are for variant B hardware and for developing new variants; change **one** parameter at a time so that the result on the device can be interpreted. The tools refuse timings with `vbp − vspw ≤ 3` or `hbp ≤ hspw`. `--no-keep-detect` forces the table for any panel and is meant for a single known panel only.

Example: rebuild the variant B image from the variant A image by hand:
```
python build_kit/tools/make_variant.py --name by_hand --table linux_k101_im2byl02_init --timing 73,890,25,20,1340,20,4
```

## Adding a table

Add an entry to `build_kit/data/corpus.json`: `"name": {"packets": [[255,152,129,PAGE], [REG, VALUE], ...], "note": "..."}`. Numbers are decimal; every command carries exactly one parameter; a page switch is `[255,152,129,N]`. Multi-byte writes have to be expanded into consecutive registers.

## Tools

| Tool | Purpose |
|---|---|
| `make_variant.py` | the wrapper described above |
| `verify_variant.py` | independent structural check (sums, kernel, configuration, timing, variant profile) |
| `check_env.py`, `selftest_build.py` | environment check and self-test |
| `force_auto_mipi_branch.py`, `apply_corpus_table.py` | kernel patching (init routine and timing) |
| `set_config_u32.py`, `set_lcd_driver.py` | configuration edits (both copies, with sums recomputed) |
| `rv32asm.py` | small RISC-V assembler used to build the init routine, byte-identical to LLVM's output for this code |
| `parse_regdump.py` | reads a register dump from a UART log and compares it with the corpus tables |

Hardware variant profiles live in `build_kit/data/frames.json`.
