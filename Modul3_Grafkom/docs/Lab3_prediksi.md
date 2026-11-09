# Lab 3 langkah 3: prediksi TERTULIS sebelum pengukuran

Ditulis: 2026-11-04 14:42:53 WIB, sebelum hard shadow diimplementasikan dan sebelum pengukuran Lab 3.
File ini tidak diubah setelah pengukuran (cek tanggal modifikasinya dan DEVLOG).

**Catatan kejujuran:** waktu render *tanpa* shadow sudah sempat terlihat di Lab 2 (logs/lab2_render.txt:
raster mymodel 0.10 s, raytrace 2.74 s pada 512x512). Jadi prediksi rasio tanpa shadow bukan tebakan buta.
Yang benar-benar diprediksi di sini adalah efek menambah hard shadow dan perbandingan dengan Three.js.

Scene uji: mymodel.obj (432 segitiga) + lantai 2 segitiga di bawahnya, 512x512, light directional (0.5, 0.8, 0.6).
Sekitar 59 ribu dari 262 ribu piksel terkena pilar (Lab 2); lantai menambah piksel yang kena.

## (i) Frame time dan rasio
Penalaran biaya:
- Raster: biaya ~ (jumlah segitiga) + (jumlah fragment). Shadow map = satu pass raster tambahan dari arah
  light (depth saja) + satu lookup per fragment. Perkiraan: waktu raster naik ~1.5x sampai 2x.
- Ray trace: biaya ~ (jumlah ray) x (jumlah segitiga), tanpa struktur percepatan. Shadow = 1 ray tambahan per
  piksel yang kena ke arah light, diuji ke semua segitiga. Dengan lantai, hampir semua piksel bawah juga kena,
  jadi ray bayangan bisa sampai ~60% dari jumlah ray primer. Perkiraan: waktu raytrace naik ~1.5x.

| | prediksi tanpa shadow | prediksi dengan shadow |
|---|---|---|
| raster3d.py (NumPy) | ~0.12 s | ~0.2 s |
| raytrace.py (NumPy) | ~3 s | ~4.5 s |
| rasio raytrace / raster | ~25x | ~20x |
| Three.js (GPU, tanpa shadow) | ~0.5 ms/frame, sekitar 200x lebih cepat dari raster NumPy | |

## (ii) Kualitas shadow dan reflection
- **Shadow:** ray tracer lebih baik. Uji bayangan per piksel bersifat eksak (ray ke light kena atau tidak),
  tanpa resolusi peta dan tanpa bias. Shadow map di raster akan menunjukkan tepi bergerigi (aliasing akibat
  resolusi peta) dan butuh bias: terlalu kecil muncul shadow acne, terlalu besar bayangan terlepas
  (peter-panning). Prediksi: PSNR raster-shadow vs raytrace-shadow turun jauh dibanding tanpa shadow, dan
  selisihnya ada di tepi bayangan.
- **Reflection:** ray tracer jauh lebih baik. Pantulan = ray sekunder ke arah pantul, termasuk objek di luar
  layar. Raster hanya bisa memalsukannya (environment map statis, planar reflection = render ulang scene,
  screen-space reflection yang gagal untuk objek di luar layar).

## Keputusan yang diprediksi
- **Viewer real-time:** rasterisation (Three.js/GPU). Hanya raster yang masuk anggaran 16.7 ms/frame.
- **Beauty shot marketing:** ray tracing. Waktu render bebas (offline), kualitas shadow/reflection lebih penting.
