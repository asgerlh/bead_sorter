# Bead sorting machine

## Hardware

RP2040-zero
TCS34725 color sensor module
2x 28BYJ-48 Stepper motors

## Firmware

Flash the RP2040 with micropython (e.g. WAVESHARE_RP2040_ZERO-20260406-v1.28.0.uf2).

## Pinout

| Pin  | Function        |
|------|-----------------|
| GP0  | TCS34725 SDA    |
| GP1  | TCS34725 SCL    |
| GP2  | TCS34725 LED    |
| GP4  | Back Button     |
| GP5  | Start Button    |
| GP9  | Disc Motor 1    |
| GP10 | Disc Motor 2    |
| GP11 | Disc Motor 3    |
| GP12 | Disc Motor 4    |
| GP26 | Flipper Motor 1 |
| GP27 | Flipper Motor 2 |
| GP28 | Flipper Motor 3 |
| GP29 | Flipper Motor 4 |