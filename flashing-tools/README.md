# Flashing tools (from the seller's package)

Everything you need on the PC side to flash `smartframe.img` is in this folder. These are **unmodified copies of the files from the seller's update package** that came with the frame. Nothing here was changed; compare the SHA-256 values with [`SHA256SUMS`](SHA256SUMS).

| File | Size | What it is | SHA-256 |
|---|---|---|---|
| [`PhoenixSuit_V2.0.7.zip`](PhoenixSuit_V2.0.7.zip) | 48.9 MB | **PhoenixSuit V2.0.7**, the Allwinner flashing program (Windows). It also carries its own copy of the USB driver and a user manual PDF | `9705b2c0df51eb6554df2eb656e5a49993e0b48e4812f1f93e38fd321b94e55e` |
| [`usbdriver_V1.0.0.4.zip`](usbdriver_V1.0.0.4.zip) | 0.4 MB | **USB driver** V1.0.0.4 for the processor's flashing mode (`InstallUSBDrv.bat` + `UsbDriver/`) | `f4e41c34dc8cbe7a05a8ff18fef8a648caabf7b771ffed47914b66c5b1190b4f` |
| [`seller_update_video.mp4`](seller_update_video.mp4) | 13.3 MB | The seller's demonstration video (about 2 min 45 s, 960×544, Chinese) showing the update on a frame: selecting the image in PhoenixSuit, and plugging the USB cable into the frame's USB-A port while holding a button next to the port | `29de5cbc56e1fec3561583d8678b7b0cdf8cc0af11808f2452f710d8db258410` |
| [`seller_note.txt`](seller_note.txt) | 1 line | The seller's note, converted to UTF-8: "1. You need a double-ended USB data cable that can transfer data" (that is, a cable with a USB-A plug on both ends) | `21be99637296f76964f8a9b48a2217788525af018d3f149110c27b1dd92fc0bd` |

The zip files contain no other firmware. The firmware images are in [`../firmware`](../firmware).

## How to use them

The full procedure is in [../docs/UPDATING.md](../docs/UPDATING.md). In short: unpack both zip files, run `InstallUSBDrv.bat` from the driver archive once, start `PhoenixSuit.exe` from the unpacked PhoenixSuit folder, select the image, choose full-erase mode and enter the frame's flashing mode.

Verify the files before use:

```powershell
Get-FileHash .\PhoenixSuit_V2.0.7.zip -Algorithm SHA256
Get-FileHash .\usbdriver_V1.0.0.4.zip -Algorithm SHA256
```

## Safety note

- These programs and the driver come from the seller and are **not** signed or reviewed by this project. In the author's static check of the seller's package, many executables, including `PhoenixSuit.exe`, carried no embedded digital signature, and no antivirus scan was run. Nothing suspicious was found by looking at the package contents, but that is not a guarantee.
- The driver is a Windows kernel driver (`usbdrv.sys` with catalog files). Windows may warn that the publisher cannot be verified.
- Check the hashes above, scan the files with your antivirus, and if possible do the flashing on a PC you can afford to treat with care. The author used exactly these files for all flashing described in this repository.
- Do not run the other executables bundled inside the PhoenixSuit archive (for example `adb.exe`, `msiexec.exe`, `Dbgview.exe`, `UpdateVer*.exe`); flashing needs only `InstallUSBDrv.bat` and `PhoenixSuit.exe`.

## Rights

PhoenixSuit and the driver belong to their authors (Allwinner and the seller). They are included here only so that the guide is complete; this repository is private. See the rights note in the main [README](../README.md#rights-and-legal).
