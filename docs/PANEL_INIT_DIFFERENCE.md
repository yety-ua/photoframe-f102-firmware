# What differs between the two custom images (screen side)

**Summary:** the custom variant A and variant B images differ in **one block of the kernel**: the panel-initialisation code that runs when the panel reports ID `98 81 1C`. Timing, DSI mode, configuration, the automatic panel detection and the whole interface are identical.

## What was compared

`firmware/custom/variant-a_k101-im2cyl02-l` (SHA-256 `784eb058…6d81`) against `firmware/custom/variant-b_ht101d08s` (`33c979a9…f25b`), checked byte by byte on a Mac.

- Only two items of the image container differ: the kernel package `melis_pkg_nor.fex` (the compressed kernel; 548 259 differing bytes because the kernel was recompressed) and its checksum `Vmelis_pkg_nor.fex`. The interface (`data_udisk`), `config_nor.fex` and every other item are identical.
- After decompression the two kernels have the same size and differ in **3766 bytes inside one contiguous range, `0x810AE…0x81F93`**. That is the init function of the seller's branch `ili9881_inx_f101a35`, which `auto_mipi` selects for panel ID `98 81 1C`.
- The `auto_mipi` timing table (`0x10E7F0`) is identical: `dclk 73 MHz, ht 890, hbp 25, hspw 20, vt 1340, vbp 20, vspw 4` (61.21 Hz).
- DSI settings are identical: `lcd_dsi_if 0` (video mode), 4 lanes, RGB888.

Which branch a *variant A* panel takes is **not known** because its panel ID has not been captured. If it also reports `98 81 1C`, the variant A image uses the seller's table on the left side of the comparison below; if it reports another ID, the changed block is never executed on it.

## Seller's table versus the table used for variant B

The seller's init function is compiled code, so it was run in a small emulator (`analysis_tools/emulate_init_routine.py`) to extract the DCS register writes: 196 commands, no unknown calls and no reads of unset memory. The variant B table is `linux_k101_im2byl02_init` from the Linux driver `panel-ilitek-ili9881c.c`. The complete list of registers is in [`analysis/panel-init-difference/init_writes_stock_vs_k101.csv`](../analysis/panel-init-difference/init_writes_stock_vs_k101.csv).

The seller's table writes 188 distinct registers, the variant B table 187. They share 180 registers: **79 have the same value, 101 differ**.

| Page | Common | Same | Different | Only seller's | Only variant B |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 1 | 0 |
| 1 | 47 | 6 | 41 | 1 | 4 |
| 3 | 125 | 68 | 57 | 1 | 2 |
| 4 | 8 | 5 | 3 | 5 | 1 |

- **Page 3** (gate-in-panel row scanning): 57 of 125 common registers differ.
- **Page 1** (power, VCOM, inversion and gamma): 41 of 47 differ, including `0x31`, `0x40`, `0x50`, `0x51`, `0x53`, `0x60` and both gamma curves (`0xA0…0xB2`, `0xC0…0xD2`). Register roles follow the common ILI9881C register map and were not checked against this panel's datasheet.
- **Page 4** (power): `0x6E`, `0x6F` and `0x8D` differ.
- Only in the seller's table: `0:35=00, 1:55=88, 3:45=00, 4:00=80, 4:21=30, 4:35=1f, 4:88=0b, 4:b5=07`.
- Only in the variant B table: `1:43=66, 1:61=01, 1:62=0c, 1:63=00, 3:11=00, 3:29=03, 4:3b=c0`.
- Both then finish the same way: page 0, `0x35`, sleep-out `0x11`, 120 ms, display-on `0x29`, switch to high-speed mode.

The seller's table is almost identical to the JieLi AC792 ILI9881C table (186 of 188 registers equal). That is why trying the JieLi table in place of the seller's gave the same kind of broken picture.

## Practical conclusion

For the HT101D08S panel the registers that decide whether the picture is correct are the gate-in-panel scan settings (page 3) and the power and gamma settings (pages 1 and 4), not the timing or the DSI mode. The images therefore stay separate until the panel ID of a variant A frame is known. See [Identify your frame](IDENTIFY_YOUR_FRAME.md#one-image-for-both-variants).
