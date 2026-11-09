# Baseline: 2x downscale vs our linear-correct reference


## relief.ppm

| candidate | PSNR vs ref | SSIM | mean abs diff | max abs diff | mean bias |
|---|---|---|---|---|---|
| ours naive (sRGB codes) | 21.5 dB | 0.962 | 20.25 | 42 | -20.25 |
| Pillow resize(BOX) | 21.7 dB | 0.963 | 19.74 | 41 | -19.74 |
| Pillow reduce(2) | 21.5 dB | 0.962 | 20.12 | 41 | -20.12 |
| Pillow BOX on linear (F) | inf | 1.000 | 0.00 | 0 | +0.00 |

## 1-px checker (E4)

| candidate | PSNR vs ref | SSIM | mean abs diff | max abs diff | mean bias |
|---|---|---|---|---|---|
| ours naive (sRGB codes) | 12.6 dB | 0.930 | 60.00 | 60 | -60.00 |
| Pillow resize(BOX) | 12.6 dB | 0.930 | 60.00 | 60 | -60.00 |
| Pillow reduce(2) | 12.6 dB | 0.930 | 60.00 | 60 | -60.00 |
| Pillow BOX on linear (F) | inf | 1.000 | 0.00 | 0 | +0.00 |

## checker.pgm

| candidate | PSNR vs ref | SSIM | mean abs diff | max abs diff | mean bias |
|---|---|---|---|---|---|
| ours naive (sRGB codes) | inf | 1.000 | 0.00 | 0 | +0.00 |
| Pillow resize(BOX) | inf | 1.000 | 0.00 | 0 | +0.00 |
| Pillow reduce(2) | inf | 1.000 | 0.00 | 0 | +0.00 |
| Pillow BOX on linear (F) | inf | 1.000 | 0.00 | 0 | +0.00 |
