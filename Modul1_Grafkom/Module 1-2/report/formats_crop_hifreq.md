# Format comparison -- crop_hifreq.ppm

decoded original = 49,152 bytes

| format | bytes | ratio | PSNR vs original |
|---|---|---|---|
| PNG | 38,264 | 1.28x | inf |
| WebP-lossless | 18,008 | 2.73x | inf |
| JPG q92 | 12,223 | 4.02x | 30.9 dB |
| WebP q92 | 12,408 | 3.96x | 31.5 dB |
| JPG q75 | 7,994 | 6.15x | 26.9 dB |
| WebP q75 | 8,486 | 5.79x | 29.9 dB |
| JPG q60 | 6,633 | 7.41x | 24.5 dB |
| JPG q40 | 5,628 | 8.73x | 22.1 dB |
| AVIF q75 | 5,894 | 8.34x | 30.5 dB |
| AVIF q40 | 1,721 | 28.56x | 23.2 dB |
