# Technical notes

## Hardware facts (from boot logs and board inspection)

| Item | Value |
|---|---|
| Board | `YD_F102_MIPI_V3.0` |
| SoC | Allwinner F102 (RISC-V), Melis RTOS with RT-Thread components |
| RAM | 128 MB DDR3 (the first parameter set fails the memory test and the second one is used: normal on this board) |
| Flash | SPI NOR, XMC XM25QH64C, 8 MB (JEDEC ID `0x204017`) |
| Touch controller | Silead GSL1680 |
| Display | 10.1-inch 800×1280 MIPI DSI panel, 4 lanes, RGB888; the interface is drawn at 1280×800 |
| Debug UART | UART2, pads `PE6 TX2`, `PE7 RX2`, `GND`, 115200 8N1, 3.3 V ([UART.md](UART.md)) |

## Firmware image

- `smartframe.img` is an Allwinner `IMAGEWTY` v0x300 container with 25 items (boot0, U-Boot, configuration, partition table, the kernel package `melis_pkg_nor.fex`, the data image `data_udisk.fex` and others).
- `data_udisk.fex` is a MinFS file system holding `startup.sh`, the interface module `mod/lvgl.mod`, codec modules, the splash `res/stalogo1.bin` and `res/res.tar.xz` (images, fonts, language tables, sounds).
- The kernel package contains the kernel compressed as LZMA (known size in the header, **no end-of-payload marker**), the embedded copy of `config_nor.fex` and a package checksum. Two sums protect it: the package's own `add_sum` (a 32-bit word sum computed with the stamp `0x5F0A6C39` in the field at `0x14`) and the container item `Vmelis_pkg_nor.fex` (the 32-bit word sum of the whole package). The build kit recomputes both. These are plain sums, not CRC32 and not signatures.
- The kernel slot is almost full: a recompressed kernel has to fit in about 552 960 bytes, with less than 1.3 KB to spare, which constrains how much code a patch can add.

## Panel detection and the screen problem

The kernel's `auto_mipi` driver reads the panel ID over DSI at boot and picks an init branch:

| Panel ID read | Branch |
|---|---|
| `93 65 04 00` | `jd9365da_h3_60hz` |
| `93 65 ff 00` | `boe_jd9365_h3_wxga` |
| `93 66 ff 00` | `m080-110b1-160` |
| `98 81 1c 00` | `ili9881_inx_f101a35` |
| `00 80 00 00` | `nt35521` |
| anything else | `s8036_ili9881_fc` |

The log of a variant B frame shows `mipi id read ok: num 1 [0x98 0x81 0x1c 0x0]` followed by `init ili9881_inx_f101a35`. The seller's init table of that branch does not suit the HT101D08S panel (static colour stripes). The fix replaces that branch's init function with the `linux_k101_im2byl02_init` ILI9881C table, keeps the seller's timing and keeps the automatic detection, so other panel IDs behave exactly as before.

### The auto_mipi timing table
Nine 16-bit values at offset `0x10E7F0` of the decompressed kernel, **in this order**: `dclk, x, y, ht, vt, hbp, vbp, hspw, vspw`. The kernel rejects a table with `vbp − vspw ≤ 3` ("vbp is too small, please readjust the timing parameters"). All nine panels registered in the seller's kernel satisfy `vbp − vspw > 3` and `hbp > hspw`; the build kit refuses to build otherwise.

## How the problem was solved (short history)

More than twenty images were tried on a variant B frame. What did not work and why it matters:

- The seller's own images (16 Oct, 29 Oct, 2 Nov) gave stripes or a black screen.
- Switching the panel driver among the nine registered ones: stripes (ILI9881 drivers) or black (JD9365 drivers).
- Several tables from open ILI9881 drivers were tried in the init slot. **The right table, K101, was among the first ones tried, but those first images were built with a bug in our own tool that stored the timing fields in the wrong order**, so the kernel received `vbp 8, hspw 21` instead of the intended values (a combination that its own timing check rejects), and the result looked like "no table fits". After the bug was found (16 Nov, thanks to the UART log message), a mismatching timing was no longer a variable.
- `lcd_dsi_if = 2` (burst) floods the log with `timeout` lines because frames stop completing; the right value is `0`.
- The decisive build used the seller's original timing together with the K101 table.

| Claim | Status |
|---|---|
| K101 table + the seller's timing gives a perfect picture on an HT101D08S frame | **verified on the device** |
| The earlier failures of that table came from the swapped timing fields | **verified** (the timing fields of those images were read back from their kernels) |
| The rule `hbp > hspw` (in the sunxi convention `hbp` includes the sync width) | consistent with all nine seller panels and with sunxi; a reported hang when violated was **not reproduced** by us; the build kit refuses such timing |
| The seller's table mismatches the glass in the gate-in-panel registers | plausible and supported by the register comparison, **not verified** against a datasheet |
| "The pixel PLL is stable only at 73 MHz" | **not confirmed**: images with 72, 70 and 68 MHz booted. 73 MHz is simply the seller's value and is kept |
| The HT101D08S glass belongs to the same family as `K101-IM2CYL02-L` | assumption only |

## Open questions

1. **The panel ID of a variant A frame.** It decides whether one image can serve both variants ([Identify your frame](IDENTIFY_YOUR_FRAME.md#one-image-for-both-variants)).
2. Whether the update can also be installed from a USB drive: the firmware appears to look for `epdk_img\smartframe.img` on a drive. This was **not tested**.
3. Slow photo-thumbnail generation (the thumbnail code is byte-identical to the seller's, the cause is unknown).

## Tools in this repository

- [`build_kit/`](../build_kit): builds the images; [BUILDING.md](BUILDING.md).
- [`analysis_tools/emulate_init_routine.py`](../analysis_tools/emulate_init_routine.py): extracts the register writes of a compiled init function (needs the `capstone` package).
- [`analysis_tools/add_seeed_x_tables.py`](../analysis_tools/add_seeed_x_tables.py): adds tables from the Seeed ILI9881x driver to the corpus.
- [`build_kit/tools/parse_regdump.py`](../build_kit/tools/parse_regdump.py): reads a panel register dump from a UART log (`--dump-regs` builds).
