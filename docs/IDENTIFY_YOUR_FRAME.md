# Identify your frame (hardware variants)

Frames built on the **YD_F102_MIPI_V3.0** board look identical from the outside and run the same software, but they are sold with **different LCD panels**. The seller's firmware picks the panel setup automatically by reading an ID from the panel, and for one known panel that setup is wrong. So the correct image depends on the panel, not on the frame's outside.

## Known variants

| | Variant A | Variant B |
|---|---|---|
| Panel marking | `K101-IM2CYL02-L` | `HT101D08S` / `JDH328DK0` (flex cable also marked `SY31P 2021.11.15`) |
| Panel ID read at boot (UART) | not captured yet | `98 81 1C 00` |
| Seller's original firmware | works | static colour stripes, no usable picture |
| Image to use | [`custom/variant-a_k101-im2cyl02-l`](../firmware/custom/variant-a_k101-im2cyl02-l) (or the stock image) | [`custom/variant-b_ht101d08s`](../firmware/custom/variant-b_ht101d08s) |

Both variants are 10.1-inch 800×1280 MIPI panels mounted in landscape; the interface is drawn at 1280×800. Other panels may exist on the same board. If yours is neither of the two, see [Other panels](#other-panels).

## How to tell which one you have

### Method 1: read the panel marking (certain)

1. Unplug the frame and open the back cover. Take care with the flat cables; do not pull on them.
2. Look at the panel's flex cable and the label on the back of the panel. Compare the printed marking with the table above.
3. Variant A frames carry `K101-IM2CYL02-L`; variant B frames carry `HT101D08S` / `JDH328DK0`.

### Method 2: try the safe image first (no need to open the frame)

Flash the **variant A** image first. This is the safe order, because variant A uses the unchanged seller kernel: on a variant B frame it just shows stripes and causes no harm.

| What you see after flashing variant A | Conclusion | Next step |
|---|---|---|
| A normal, stable picture | you have hardware variant A | done |
| Static or slowly appearing colour stripes, no readable menu | you probably have variant B | flash the variant B image |
| Black screen | unclear (possibly another panel) | see [Other panels](#other-panels) |

Do **not** start with the variant B image: its panel init is written for variant B and has not been tested on a variant A frame.

### Method 3: read the boot log with a UART adapter (optional)

With a USB-UART adapter you can read a line like this at boot (see [UART.md](UART.md)):

```
mipi id read ok: num 1 [0x98 0x81 0x1c 0x0]
```

- `98 81 1c`: the panel family of variant B. Use the variant B image.
- Anything else: please tell us (see below). The ID of a variant A panel has not been captured yet.

## One image for both variants?

A single image that works on both would be the ideal. It is **not available yet**, for this reason:

- The two images differ in one place only: the panel-init code that the seller's kernel runs for panels reporting ID `98 81 1C` ([details](PANEL_INIT_DIFFERENCE.md)). Everything else, including timing and the interface, is identical.
- The variant B image keeps the seller's automatic panel detection. So **if** a variant A panel reports a *different* ID than `98 81 1C`, it would never reach the changed code and the variant B image would behave on variant A exactly like the stock image, which makes it a universal image.
- **If** a variant A panel also reports `98 81 1C`, the two panels cannot be told apart by this ID, and a single image would have to read another register to decide. That would need a register dump from a variant A frame (the build kit has a tool for it, `--dump-regs`).

Which case applies is **unknown**, because nobody has captured the boot log of a variant A frame yet. Until then two images are provided. **How you can help:** capture the UART boot log of a variant A frame with the stock or custom variant A image, find the `mipi id read ok` lines and share them (an issue or a pull request with the log in [`analysis/uart-logs`](../analysis/uart-logs)).

## Other panels

If you have the same board but a panel that matches neither variant, or a variant that the steps above cannot place:

1. Do not keep flashing random images.
2. Capture the UART boot log ([UART.md](UART.md)) and the panel marking (photo of the flex cable).
3. Share them. With the panel ID and a working init table the build kit can produce a new variant ([BUILDING.md](BUILDING.md)).
