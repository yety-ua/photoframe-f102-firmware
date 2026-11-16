# Reading the boot log (UART)

Optional. A USB-UART adapter gives you the frame's boot log: the panel ID, the flash chip model, the selected panel driver and any errors. It is the most reliable way to identify a panel ([Identify your frame](IDENTIFY_YOUR_FRAME.md)) or to diagnose a problem.

The adapter does **not** flash the firmware. Flashing is always done with PhoenixSuit over USB ([UPDATING.md](UPDATING.md)).

## Where the port is

On the back of the board (`YD_F102_MIPI_V3.0`), near the touch-controller chip and a flat-cable connector, there are labelled pads **`PE6 TX2`**, **`GND`**, **`PE7 RX2`**. From the firmware configuration (`[uart_para]`): UART2, 115200 baud, 8N1; the processor's pins are 3.3 V. Nearby pads `PE8 TX3` / `PE9 RX3` belong to UART3, which is not the one you need.

## What you need

- A USB-UART adapter, for example one based on the CH340G, set to **3.3 V** (never 5 V).
- Three thin wires, ideally soldered to the pads (a hand-held probe often loses contact during boot).
- A terminal program: PuTTY, Tera Term or any serial terminal.

## Wiring (frame switched off and unplugged)

Receiving only, which is enough for the boot log:

| Adapter | Board |
|---|---|
| `GND` | `GND` pad |
| `RXD` | `PE6 TX2` |
| `VCC` | **not connected** (the frame has its own power) |
| `TXD` | not connected |

TX goes to RX: the board's transmit pad connects to the adapter's receive pin. If the log is empty, check the ground, the solder contact, the COM port and the speed; as a last resort swap the signal wire to the other pad.

To type commands, also connect adapter `TXD` to `PE7 RX2`, but only after you have measured about 3.3 V on the adapter's TXD pin.

## Terminal settings

115200 baud, 8 data bits, no parity, 1 stop bit, flow control **none**. Enable logging to a file. In PuTTY: Session → Connection type Serial, Logging → "All session output".

## Capture a boot

1. Open the terminal with the frame off.
2. Power the frame on and wait 60–90 seconds. (If the frame is being flashed with the adapter attached, you will also see the flashing session and the first boot afterwards.)
3. Save the log file.

## What to look for

| Line | Meaning |
|---|---|
| `spinor flash id  : 0x…`, `spinor flash name: …` | flash chip (for example `0x204017`, `XM25QH64C`) |
| `mipi id read ok: num 1 [0x98 0x81 0x1c 0x0]` | the panel ID read at boot |
| `init ili9881_inx_f101a35` | the selected panel init branch (this branch is the one that was changed for variant B) |
| `use lcd[auto_mipi] drv timing para` | the driver's built-in timing is used |
| `vbp is too small…` | the timing table is invalid ([TECHNICAL_NOTES.md](TECHNICAL_NOTES.md)) |
| `timeout` repeated | the display pipeline stops completing frames (seen with `lcd_dsi_if 2`) |
| `create group home` | the interface started |

Examples: [`analysis/uart-logs`](../analysis/uart-logs).

## Console commands

After the boot the frame offers an RT-Thread shell. Read-only commands that are safe: `help`, `ps`, `list_thread`, `list_device`, `free`, `df`, `ls`, `pwd`, `date`, `cpu_clock_print`, `norflash_size`. Avoid commands that write or format (`format`, `mkfs`, `rm`, `mv`, `cp`, `mkdir`, `flash_lock`, `flash_unlock`, `m`, `p`, `insmod`, `uninsmod`) unless you know exactly what they do. `reboot` is harmless.
