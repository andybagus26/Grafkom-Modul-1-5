# Lab 1 -- input, budget, decode vs on-disk

Input: **no own photos were available -> fallback `make data`** (21 deterministic synthetic images, `data/manifest.csv`). The budget below assumes a typical 12 MP phone camera (4000x3000) and a 15-image capture set, the Lab 1 minimum.

## Budget at the real resolution

```
bytes / decoded image (RGB888) = 4000 x 3000 x 3 = 36,000,000 B = 36.00 MB (10^6) = 34.33 MiB (2^20)
working set, 15 images         = 540,000,000 B = 515.0 MiB (2^20)
flythrough 10 s @ 30 fps        = 10,800,000,000 B = 10.80 GB (10^9) = 10.06 GiB (2^30)
bandwidth                       = 1,080,000,000 B/s = 1080.0 MB/s = 8640.0 Mbit/s (10^6)
```

## Decode vs on-disk (3 images)

| image | content | decoded B | on-disk B | format | effective ratio |
|---|---|---|---|---|---|
| crop_smooth.ppm (PPM as stored) | plain sky-like gradient | 41,772 | 41,787 | raw PPM | 1.00x |
| crop_smooth.ppm -> JPEG q92 | plain sky-like gradient | 41,772 | 1,791 | JPEG (camera-like) | 23.3x |
| silhouette.pgm (PPM as stored) | flat temple silhouette | 196,608 | 65,551 | raw PPM | 3.00x |
| silhouette.pgm -> JPEG q92 | flat temple silhouette | 196,608 | 4,095 | JPEG (camera-like) | 48.0x |
| relief.ppm (PPM as stored) | busy carved relief (foliage-like) | 196,608 | 196,623 | raw PPM | 1.00x |
| relief.ppm -> JPEG q92 | busy carved relief (foliage-like) | 196,608 | 46,942 | JPEG (camera-like) | 4.2x |
