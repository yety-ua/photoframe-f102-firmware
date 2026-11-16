# Updating the firmware (flashing guide)

This guide installs a `smartframe.img` image on the frame (10.1-inch Digital Calendar with Schedule Management, model HY-XKSZ-10.1, board YD_F102_MIPI_V3.0) with **PhoenixSuit**, the Allwinner flashing tool the seller supplies. It works for the custom mod images and for restoring the seller's original image. The procedure follows the seller's own instructions and has been used by the author many times on both known hardware variants.

## 0. Read this first

- **Pick the right image** for your panel: [Identify your frame](IDENTIFY_YOUR_FRAME.md). If you are unsure, flash the variant A image first.
- The seller's procedure uses **full erase** (`全盘擦除升级`). It wipes the frame's internal flash: settings and all stored data, and, according to the PhoenixSuit manual, also data such as the serial number. These tools cannot back that flash up. Do not flash if you cannot accept losing it.
- Do not unplug the cable, press Reset/Power or cut the power while the progress bar runs. 100% on the bar alone is not enough: wait for the final success message.
- The flashing mode itself (the processor's built-in loader) is independent of what is stored on the frame, so a bad image can be replaced again as long as the cable and driver work.
- Use at your own risk. This is an unofficial mod.

## 1. What you need

| Item | Notes |
|---|---|
| A Windows PC | PhoenixSuit is a Windows program. |
| A USB data cable with **USB-A plugs on both ends** | The seller calls it a double-ended data cable. A charge-only cable will not work. |
| The `smartframe.img` image | From [`firmware/`](../firmware). |
| PhoenixSuit and the USB driver | Included in this repository: [`flashing-tools/`](../flashing-tools) (unmodified copies of the seller's files). |
| The frame | In the seller's video the frame is connected only by the USB cable (no separate power adapter is visible in the frames we checked; the audio was not analysed). If your frame is not detected, see the troubleshooting table. |

Files from [`flashing-tools/`](../flashing-tools) that you will use (SHA-256 values are in [`flashing-tools/SHA256SUMS`](../flashing-tools/SHA256SUMS)):

| File | Purpose |
|---|---|
| `PhoenixSuit_V2.0.7.zip` | the flashing program |
| `usbdriver_V1.0.0.4.zip` | the USB driver for flashing mode |
| `seller_update_video.mp4` | the seller's demonstration of the cable connection and button press (optional, Chinese) |

Read the [safety note](../flashing-tools/README.md#safety-note) first: these files come from the seller and were not signed or scanned by this project.

## 2. Prepare the PC (once)

1. Create a simple working folder with a short ASCII path, for example `C:\PhotoFrame\`, and copy there the image you chose and the two zip files from `flashing-tools/` (download them from GitHub or clone the repository).
2. Unpack the USB driver archive and the PhoenixSuit archive completely (right-click, Extract All). Do not run PhoenixSuit from inside the zip file.
3. Install the USB driver: in the unpacked driver folder run `InstallUSBDrv.bat` (right-click, Run as administrator if Windows asks).
   - If Windows blocks the driver or the installation fails, stop and note the message. Do not disable Windows protection blindly; check that the unpacked folder is complete and try again.
4. Start `PhoenixSuit.exe` from the fully unpacked PhoenixSuit folder (keep its DLL and configuration files next to it). Do not confuse it with `PhoenixInstall.exe`.

## 3. Check the image

Before every flash compare the SHA-256 of the file with the table in [`firmware/SHA256SUMS`](../firmware/SHA256SUMS).

Windows (PowerShell):

```powershell
Get-FileHash C:\PhotoFrame\smartframe.img -Algorithm SHA256
```

macOS / Linux:

```bash
shasum -a 256 smartframe.img
```

If the value differs, do not flash that file.

## 4. Flash

PhoenixSuit's interface is partly in Chinese. The button names are given below.

1. Switch the frame **off** and unplug the USB cable from the frame.
2. In PhoenixSuit open the firmware update tab, labelled **`一键刷机`** (one-click flash).
3. Click **`浏览`** (Browse) and select your `smartframe.img`. Check that the path shown in the program is the file you intend to flash. Select the image file itself, not the `.rar` archive and not individual `.fex` files.
4. Select the mode **`全盘擦除升级`** (full erase upgrade), as the seller prescribes.
   - The other modes are `保留数据升级` (keep data) and `分区擦除升级` (partition erase). Their effect on this image has not been verified; do not substitute them.
5. Connect the PC end of the USB cable to the computer. Then **press and hold the Power button on the frame** and plug the other end of the cable into the frame's **USB-A port** (the port shown in the seller's video). Keep holding Power until PhoenixSuit detects the device, then release.
   - Windows installs/recognises a new USB device at this moment. This is the flashing mode.
6. PhoenixSuit may start straight away or show a confirmation. If it asks whether to erase the whole flash, check the image once more and confirm with **`是`** (Yes). Do not tick **`不再提示`** (do not ask again).
   - If your PhoenixSuit version needs it, click **`立即升级`** (Upgrade now).
7. Wait. During the process do not touch the cable or the frame. The tool reports success when the image is written and verified; then the frame restarts.
8. Close PhoenixSuit, unplug the USB cable from the frame and start the frame with its normal power.

## 5. First start

- The first boot after a full erase formats the data partition, so it takes a little longer. Messages such as "data damage, will reformat data" in the boot log are normal.
- Open **Settings → Language** and choose your language (the custom images add Ukrainian; English is available too).
- Check the basics: main menu, touch, brightness, volume, photo/video playback, clock, alarm. Change one harmless setting, power the frame off and on and check that the setting is kept.

## 6. If something goes wrong

| Symptom | What to try |
|---|---|
| PhoenixSuit does not detect the frame | Use a data cable (not charge-only), the same USB-A port as in the seller's video, another PC USB port, and repeat step 5 starting from a switched-off frame. Check Device Manager for an unknown USB device and reinstall the driver (step 2.3). |
| Flashing stops with an error | Write down the exact message and percentage. Replug and repeat from step 1. Endlessly repeating the erase is not a diagnosis; check cable, port and driver first. |
| Static colour stripes, no menu | Wrong hardware variant. Flash the other image: see [Identify your frame](IDENTIFY_YOUR_FRAME.md). |
| Black screen, backlight on | The system may still be starting (first boot is slower). If it stays black, flash the seller's stock image or the other variant and capture a [UART log](UART.md). |
| No picture and no backlight | Check the frame's power supply, then repeat the flash. Flashing mode works independently of the stored software. |
| Picture is fine but something looks wrong | Report it with a photo; see [Features and changes](FEATURES.md) for known limitations. |

## 7. Going back to the original firmware

Flash [`firmware/stock/seller-2026-10-16/smartframe.img`](../firmware/stock/seller-2026-10-16) with the same procedure. The original image works on variant A frames only; on variant B frames it shows stripes. The seller's later builds of 29 Oct and 2 Nov are in the same `firmware/stock/` folder; they use a fixed panel driver and are not verified on variant A (see [firmware/README.md](../firmware/README.md#the-sellers-later-builds-29-oct-and-2-nov-2026)). For a variant B frame the safe known-good image is the variant B custom image.

## 8. Optional: watch the boot log

A USB-UART adapter (CH340G or similar, 3.3 V) connected to the board's UART2 pads shows what the frame is doing, including the panel ID and the flash chip model. See [UART.md](UART.md).
