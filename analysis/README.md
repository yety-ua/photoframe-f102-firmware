# Analysis data

Material behind the statements in the documentation.

| Path | Content |
|---|---|
| [`uart-logs/variant-b_boot_success.log`](uart-logs/variant-b_boot_success.log) | UART log of a variant B frame running the custom variant B image: flashing session and a complete boot to the interface. Shows `mipi id read ok … 0x98 0x81 0x1c` and `create group home` |
| [`uart-logs/variant-b_lcd_dsi_if2_timeouts.log`](uart-logs/variant-b_lcd_dsi_if2_timeouts.log) | The same board with an experimental image that set `lcd_dsi_if` to 2: the log fills with `timeout` lines because frames stop completing |
| [`panel-init-difference/init_writes_stock_vs_k101.csv`](panel-init-difference/init_writes_stock_vs_k101.csv) | Every panel register written by the seller's init table and by the variant B table, with their values and a same/different status ([summary](../docs/PANEL_INIT_DIFFERENCE.md)) |

The logs are raw PuTTY captures (ANSI colour codes included). Photographs and logs from other frames are welcome; see [Identify your frame](../docs/IDENTIFY_YOUR_FRAME.md).
