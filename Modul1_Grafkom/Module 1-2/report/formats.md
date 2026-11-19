# Format policy (Lab 3.3)

Every line is backed by a number from `format_compare.py` (report/formats_crop_*.md) or Example E6.

| use | format | quality | why (measured) |
|---|---|---|---|
| Archive (master copy) | WebP lossless (PNG if a tool cannot read WebP) | lossless | exact (PSNR inf) and 18,008 B vs PNG 38,264 B on the relief crop (2.73x vs 1.28x); chisel marks cannot come back from a lossy master |
| Web hero image | WebP q~90 (AVIF where supported, JPG q92 fallback in <picture>) | q 90-92 | relief: WebP q92 31.5 dB at 3.96x; smooth: WebP q92 48.3 dB at 82.23x |
| Thumbnail | JPG q75 of a LINEAR-correct downscale | q 75 | universal decoder; relief JPG q75 26.9 dB at 6.15x -- the ringing is below what a ~128 px thumbnail can show |
| Texture source for Module 3 | PNG / WebP lossless, power-of-two, sRGB-tagged | lossless | the GPU re-compresses to BCn/ASTC and builds mips; feeding it JPEG stacks two lossy stages (JPG q40 on the relief is only 22.1 dB) |
| Flythrough video (Module 4) | MP4 / H.264 (AV1 if the target supports it) | CRF ~20 | 10 s @ 30 fps of 1080p is 1.87 GB uncompressed (E6) vs ~10 MB at 8 Mbit/s; only a video codec exploits frame-to-frame redundancy |

Why the archive answer differs from the cheapest answer: the cheapest relief encode measured is AVIF q40 (1,721 B, 28.56x) but it is 23.2 dB -- the ridges are smeared for ever. An archive is paid for once and read by every later module; bytes are cheap, lost detail is not.
