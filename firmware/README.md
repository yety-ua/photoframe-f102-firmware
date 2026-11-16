# Firmware images

These images are for the 10.1-inch Digital Calendar with Schedule Management, model HY-XKSZ-10.1 (case label), board YD_F102_MIPI_V3.0. Every folder holds one file named `smartframe.img` (an Allwinner IMAGEWTY image, about 6 MB). Flash it with PhoenixSuit: [docs/UPDATING.md](../docs/UPDATING.md). Checksums: [`SHA256SUMS`](SHA256SUMS).

| Folder | What it is | Works on | SHA-256 |
|---|---|---|---|
| `stock/seller-2026-10-16` | The seller's original firmware (English, 15 language tables without Ukrainian), unmodified | hardware variant A (confirmed); variant B: stripes | `f9ed6a46a22f82b71cb6fe63e1f3ce9ac780665fbb0c1967e694c43a7c593fa0` |
| `stock/seller-2026-10-29` | The seller's later build of 29 Oct 2026: newer interface build with a Ukrainian language table; panel driver **fixed** to `boe_jd9365_h3_wxga_dsi_panel` (JD9365 panels) instead of auto-detection | variant B: black screen; variant A: **not tested** | `57be7bfb6468169d73e1ae27197c85b7aa359970b38253bc6dd38fc397b31c8f` |
| `stock/seller-2026-11-02` | The seller's later build of 2 Nov 2026: same kind of build, panel driver **fixed** to `inx_ili9881c_hy_s_dsi_panel` (INX ILI9881C panels) | variant B: colour stripes; variant A: **not tested** | `73befb007ad62b73d3d75a94b0562e3fc25e2afbbaa688e4e7aaddc00d0da998` |
| `custom/variant-a_k101-im2cyl02-l` | Custom mod for panel `K101-IM2CYL02-L` (stock kernel and panel setup) | hardware variant A | `784eb0582048ad1a203c709ab5a0a38d32758380b527c8732ec7ac9d36036d81` |
| `custom/variant-b_ht101d08s` | Custom mod for panel `HT101D08S` / `JDH328DK0` (same mod plus a different panel init) | hardware variant B | `33c979a951969a9bc11d1043bcdebf07d3597e21359ef17ea8f766df2415f25b` |

Which variant is yours? See [Identify your frame](../docs/IDENTIFY_YOUR_FRAME.md).

## How to choose

- **You want the original software back, or a baseline for comparison:** `stock/seller-2026-10-16`. It only works on variant A frames.
- **You want the mod and your frame is variant A:** `custom/variant-a_…`.
- **You want the mod and your frame is variant B** (the seller's firmware showed stripes on it): `custom/variant-b_…`.
- **You do not know your variant:** flash `custom/variant-a_…` first; see [Method 2](../docs/IDENTIFY_YOUR_FRAME.md#method-2-try-the-safe-image-first-no-need-to-open-the-frame).

## The seller's later builds (29 Oct and 2 Nov 2026)

Besides the original image the seller supplied two later builds. They differ from the 16 Oct image in the kernel package, both configuration files, the interface module and the resources; the visible difference we checked is that they add a **Ukrainian language table** (`Ukraine.bin`, 170 lines) to the 15 original tables. The interface looks the seller's way, not like this mod.

What to know before you flash one:

- Each of them **fixes the panel driver** instead of detecting the panel (see the table above). They are meant for frames whose panel matches that driver. On a mismatching panel you will get stripes or a black screen.
- On a variant B frame neither works (29 Oct: black screen; 2 Nov: colour stripes), which is why variant B needs the custom image.
- Neither was tested on a variant A frame, so it is **unknown** whether they work there. Flashing a wrong image is recoverable (the processor's flashing mode always works), but you will have to flash again.
- If you only want Ukrainian and one of these builds matches your panel, it is an alternative to the custom mod.

## About the stock image

`stock/seller-2026-10-16/smartframe.img` is the file the seller supplied first (dated 16 Oct 2026, labelled by the seller `F102_English_800x1280MIPI_auto_mipi_gsensor_4M`). It is included unchanged for restoring the original software and as the reference the build kit compares kernels against. It belongs to the seller; see the rights note in the main [README](../README.md#rights-and-legal).

## How the custom images relate to each other and to the stock one

- The custom variant A image has **the seller's kernel and configuration unchanged**; it differs from the stock image only in the interface, language and resources.
- The custom variant B image is the same as custom variant A except for one block in the kernel (the panel init code for panel ID `98 81 1C`, 3766 bytes). Details: [PANEL_INIT_DIFFERENCE.md](../docs/PANEL_INIT_DIFFERENCE.md).
- You can recreate both custom images from the interface build with the build kit; see [BUILDING.md](../docs/BUILDING.md).
