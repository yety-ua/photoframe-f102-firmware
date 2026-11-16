# Прошивка для фоторамок YD_F102_MIPI_V3.0 (Allwinner F102, Melis RTOS)

> **English summary.** Custom firmware images (light UI theme, Ukrainian language) for two photo frames built on the same board (`YD_F102_MIPI_V3.0`, Allwinner F102) but with **different LCD panels**. The images differ only in the panel-init code for panel ID `98 81 1C`. Includes the build tools (pure Python), the panel-table corpus, UART/flashing notes and the analysis behind the frame-2 fix. **Private repository: see "Права" before changing visibility.**

## Які образи для якої рамки

| | Рамка 1 | Рамка 2 |
|---|---|---|
| LCD-панель | `K101-IM2CYL02-L` | `HT101D08S` / `JDH328DK0` (шлейф `SY31P 2021.11.15`) |
| ID панелі (UART) | не знято | `98 81 1C 00` |
| Образ | [`firmware/F1_v11k_current_frame1/smartframe.img`](firmware/F1_v11k_current_frame1) | [`firmware/F2_RELEASE_k101_stock_timing/smartframe.img`](firmware/F2_RELEASE_k101_stock_timing) |
| SHA-256 | `784eb0582048ad1a203c709ab5a0a38d32758380b527c8732ec7ac9d36036d81` | `33c979a951969a9bc11d1043bcdebf07d3597e21359ef17ea8f766df2415f25b` |
| Статус | працює на пристрої | працює на пристрої (16.11.2026) |
| Ядро | заводське 16.10 без змін | заводське 16.10 + інша ініціалізація панелі |

**Образ однієї рамки не можна шити в іншу.** Контрольні суми: [`firmware/SHA256SUMS`](firmware/SHA256SUMS).

```bash
cd firmware && shasum -a 256 -c SHA256SUMS        # macOS / Linux
```
```powershell
Get-FileHash firmware\F2_RELEASE_k101_stock_timing\smartframe.img -Algorithm SHA256   # Windows
```

## Що в образі
Світла тема «жорстка тінь», українська мова замість російської, власна заставка, плитки головного екрана 208×192, виправлені календар, будильник і годинник. Інтерфейс однаковий для обох рамок.

## Чим відрізняються образи (екран)
Лише кодом ініціалізації панелі ILI9881 для ID `98 81 1C`: одна ділянка ядра (3766 байтів). Таймінг, режим DSI, конфіг і весь інтерфейс однакові. Заводська таблиця й таблиця K101 розходяться в 101 із 180 спільних регістрів (GIP, живлення, гама). Розбір: [`docs/FRAMES_SCREEN_DIFF.md`](docs/FRAMES_SCREEN_DIFF.md), дані: [`analysis/frame-screen-diff`](analysis/frame-screen-diff).

Рецепт рамки 2: таблиця `linux_k101_im2byl02_init` + заводський таймінг `dclk 73, ht 890, hbp 25, hspw 20, vt 1340, vbp 20, vspw 4` (61,21 Гц).

## Документація
- [`docs/FRAMES.md`](docs/FRAMES.md): довідник про обидві рамки, історія, що перевірено, відкриті питання.
- [`docs/FLASHING.md`](docs/FLASHING.md): як прошити (PhoenixSuit, Windows).
- [`docs/UART.md`](docs/UART.md): журнал завантаження через CH340G (UART2).
- [`build_kit/README_BUILD.md`](build_kit/README_BUILD.md): збирання образів.
- [`analysis/uart-logs`](analysis/uart-logs): журнал успішного запуску рамки 2 і журнал, що показує чому `lcd_dsi_if=2` не підходить.

## Збирання образів
Чистий Python (потрібен лише `liblzma` ≥ 5.4 для стиснення ядра в форматі LZMA1EXT). Окремий образ на кожну рамку:

```powershell
python build_kit\tools\check_env.py
python build_kit\tools\make_variant.py --frame 1 --name <версія> --base <образ інтерфейсу>
python build_kit\tools\make_variant.py --frame 2 --name <версія> --base <образ інтерфейсу>
```
Результат: `build_kit/out/F1_<версія>/` і `build_kit/out/F2_<версія>/`. Профіль перевіряє, що база має заводське ядро, і для рамки 2 накладає рецепт. Для режиму `--frame` потрібен заводський образ продавця (див. нижче), покладений у `firmware/A_stock_seller_2026-10-16/smartframe.img`.

## Чого тут немає
- Образу продавця `smartframe.img` (16.10.2026, SHA-256 `f9ed6a46a22f82b71cb6fe63e1f3ce9ac780665fbb0c1967e694c43a7c593fa0`), PhoenixSuit і USB-драйвера: це файли продавця, їх не розповсюджуємо. Образ потрібен лише для перевірок `--frame` і самотесту.
- Зміни інтерфейсу (PNG, `lvgl.mod`, мови, заставка) збираються окремо на Mac і сюди не входять; тут лише готові образи.

## Статус і відкриті питання
1. Знати ID панелі рамки 1 (UART-журнал): якщо він теж `98 81 1C`, патч рамки 2 їй зашкодить; якщо інший, обидва образи можна об'єднати.
2. Перший новий образ інтерфейсу з профілем рамки 2 потрібно перевірити на пристрої.
3. Повільні мініатюри фото (код мініатюр заводський).

## Права
Репозиторій **приватний**. Образи є похідними від прошивки продавця (ядро, застосунок, ресурси), тому перед будь-яким відкриттям репозиторію потрібно з'ясувати права на розповсюдження цих файлів. Власна ліцензія на код у `build_kit` і `analysis_tools` не обрана. Таблиці ініціалізації в `build_kit/data/corpus.json` походять із відкритих драйверів (Linux, Seeed, JieLi/Tuya, Allwinner BSP, CanMV, Milk-V тощо) під їхніми ліцензіями; джерела вказані в полях `source`.
