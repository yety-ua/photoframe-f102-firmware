# Firmware images

Every folder holds one file named `smartframe.img` (an Allwinner IMAGEWTY image, about 6 MB). Flash it with PhoenixSuit: [docs/UPDATING.md](../docs/UPDATING.md). Checksums: [`SHA256SUMS`](SHA256SUMS).

| Folder | What it is | Works on | SHA-256 |
|---|---|---|---|
| `stock/seller-2026-10-16` | The seller's original firmware (English, 15 language tables without Ukrainian), unmodified | hardware variant A | `f9ed6a46a22f82b71cb6fe63e1f3ce9ac780665fbb0c1967e694c43a7c593fa0` |
| `custom/variant-a_k101-im2cyl02-l` | Custom mod for panel `K101-IM2CYL02-L` (stock kernel and panel setup) | hardware variant A | `784eb0582048ad1a203c709ab5a0a38d32758380b527c8732ec7ac9d36036d81` |
| `custom/variant-b_ht101d08s` | Custom mod for panel `HT101D08S` / `JDH328DK0` (same mod plus a different panel init) | hardware variant B | `33c979a951969a9bc11d1043bcdebf07d3597e21359ef17ea8f766df2415f25b` |

Which variant is yours? See [Identify your frame](../docs/IDENTIFY_YOUR_FRAME.md).

## How to choose

- **You want the original software back, or a baseline for comparison:** `stock/…`. It only works on variant A frames.
- **You want the mod and your frame is variant A:** `custom/variant-a_…`.
- **You want the mod and your frame is variant B** (the seller's firmware showed stripes on it): `custom/variant-b_…`.
- **You do not know your variant:** flash `custom/variant-a_…` first; see [Method 2](../docs/IDENTIFY_YOUR_FRAME.md#method-2-try-the-safe-image-first-no-need-to-open-the-frame).

## About the stock image

`stock/seller-2026-10-16/smartframe.img` is the file the seller supplied (dated 16 Oct 2026, labelled by the seller `F102_English_800x1280MIPI_auto_mipi_gsensor_4M`). It is included unchanged for restoring the original software and as the reference the build kit compares kernels against. It belongs to the seller; see the rights note in the main [README](../README.md#rights-and-legal).

## How the custom images relate to each other and to the stock one

- The custom variant A image has **the seller's kernel and configuration unchanged**; it differs from the stock image only in the interface, language and resources.
- The custom variant B image is the same as custom variant A except for one block in the kernel (the panel init code for panel ID `98 81 1C`, 3766 bytes). Details: [PANEL_INIT_DIFFERENCE.md](../docs/PANEL_INIT_DIFFERENCE.md).
- You can recreate both custom images from the interface build with the build kit; see [BUILDING.md](../docs/BUILDING.md).
