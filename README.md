# Bead sorting machine

## Hardware

- 1x RP2040-zero
- 1x TCS34725 color sensor module
- 1x H2010/LM393 IR optocoupler
- 2x 28BYJ-48 Stepper motors
- 2x tact switches

## Firmware

Flash the RP2040 with micropython (e.g. WAVESHARE_RP2040_ZERO-20260406-v1.28.0.uf2).

## Pinout

| Pin  | Function          |
|------|-------------------|
| GP0  | TCS34725 SDA      |
| GP1  | TCS34725 SCL      |
| GP2  | TCS34725 LED      |
| GP3  | TCS34725 INT      |
| GP4  | Back/pause Button |
| GP5  | Start/stop Button |
| GP9  | Disc Motor 1      |
| GP10 | Disc Motor 2      |
| GP11 | Disc Motor 3      |
| GP12 | Disc Motor 4      |
| GP13 | H2010 IR          |
| GP26 | Flipper Motor 1   |
| GP27 | Flipper Motor 2   |
| GP28 | Flipper Motor 3   |
| GP29 | Flipper Motor 4   |
