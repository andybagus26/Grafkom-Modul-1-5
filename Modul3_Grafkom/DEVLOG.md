# Developer Log (DEVLOG) - Modul 3 Grafika Komputer

## [2026-11-01] - Tahap 0: Inisialisasi Environment & Struktur Proyek
- Menyiapkan direktori proyek: `docs/`, `reference/`, `logs/`, `out/`, `ref/`, `web/`.
- Memindahkan `Module3_ID.pdf` ke dalam folder `docs/`.
- Menyiapkan `README.md` dan aturan konvensi (Right-handed, column vector, pre-multiply, NDC $[-1, 1]^3$).

## [2026-11-01] - Tahap B (Lab 1): Model 3D Sendiri & Validasi
- Dibuat generator model parametrik `generate_mymodel.py` (Pilar/Monument bertingkat).
- Validasi via `validate_obj.py`:
  - Vertices: 227
  - UVs: 227
  - Triangles: 432 segitiga (lolos syarat >= 200).
  - Triangulated & UV mapping lengkap (0 non-triangles, 0 missing UV).
  - Bounding Box: X [-0.8, 0.8], Y [-1.2, 1.2], Z [-0.8, 0.8].
- Dibuat generator tekstur prosedural `generate_texture.py`: menghasilkan `texture.ppm` 512x512 motif batu marmer bertingkat (Lisensi CC0 karya sendiri).

## [2026-11-01] - Lab 1: Space Tracing & Transformasi Pipeline (VERIFIED)
- Menjalankan `worked_example.py` dan menyimpan hasil nyata ke `logs/lab1_worked_example.txt`.
- Data penelusuran titik `p_obj = [0.8, -1.2, 0.0, 1.0]`:
  - $p_{\text{world}} = [0.6928, -0.7000, -1.4000, 1.0000]$ (setelah rotasi Y 30° dan translasi)
  - $p_{\text{view}} = [0.6928, -1.0847, -5.2606, 1.0000]$ ($z_{\text{view}} < 0$, di depan kamera)
  - $p_{\text{clip}} = [1.2000, -1.8787, 5.1124, 5.2606]$ ($w_{\text{clip}} = -z_{\text{view}} = 5.2606$)
  - $p_{\text{ndc}} = [0.2281, -0.3571, 0.9718]$ (berada di dalam $[-1, 1]^3$)
  - $p_{\text{screen}} = (x = 314.40\text{ px}, y = 347.42\text{ px}, \text{depth} = 0.9859)$ pada canvas $512 \times 512$.
- Analisis makna fisis kolom matriks $M$:
  - Kolom 0, 1, 2: Basis arah sumbu lokal X, Y, Z objek yang terproyeksi di ruang World.
  - Kolom 3: Posisi titik origin $(0,0,0)$ lokal objek di ruang World $(0, 0.5, -1.0)$.

## [2026-11-03] - Lab 2: Software Pipeline & Ray Tracer (VERIFIED)
- Menyiapkan modul software rasterizer `raster3d.py`:
  - Near-plane clipping, perspective divide (/w), dan viewport transform dengan pembalikan sumbu y.
  - Rasterisasi berbasis fungsi sisi (edge function) 2D dengan koordinat barisentrik dan aturan top-left tie breaking.
  - Depth buffering (z-buffer) dengan inisialisasi infinity.
  - Interpolasi atribut tekstur yang benar secara perspektif (perspective-correct: $u/w, v/w, 1/w$).
  - Bilinear texture sampling dan Lambertian diffuse shading dengan satu directional light.
- Implementasi algoritma Möller-Trumbore pada `raytrace.py` untuk perpotongan sinar-segitiga analitik.
- Menyiapkan analisis perbaikan 3 bug klasik di `broken_scene.py`:
  - Bug 1 (Inside-Out): Perbaikan arah winding face CCW.
  - Bug 2 (Z-Fighting): Penyesuaian rasio near/far plane untuk memelihara presisi depth 1/z.
  - Bug 3 (Stretched): Integrasi rasio aspek canvas secara dinamis pada matriks proyeksi.

## [2026-11-04] - Lab 3: Real-Time WebGL Viewer & Publish
- Membangun viewer interaktif Three.js di direktori `web/` (`index.html`, `viewer.js`).
- Generator tekstur prosedural berbasis HTML5 Canvas 512x512 identik dengan `generate_texture.py`.
- Kamera diselaraskan dengan parameter rasterizer (FOV 50°, eye (0, 1.2, 3.8), target (0, 0, 0), rotasi Y 35°).
- Penambahan kontrol orbit interaktif (OrbitControls), tombol reset kamera, dan tombol snapshot evaluasi 512x512.
- Analisis komparasi frame time dan trade-off arsitektur: Rasterizer (real-time interactive) vs Ray Tracer (offline physical accuracy).

## [2026-11-04] Lab 1: penyelesaian dan perbaikan
- **Bug winding ditemukan:** semua 384 segitiga sisi `mymodel.obj` menghadap ke DALAM (CW dari luar), sedangkan
  48 segitiga cap menghadap ke luar. Penyebabnya: theta naik dari +x ke +z, sehingga dari luar arah seg+1 adalah ke kiri.
  Perbaikan di `generate_mymodel.py`: A->C->B dan A->D->C.
- **Validator diperluas** (`validate_obj.py`): cek pasangan edge berarah setelah vertex di-weld, plus signed volume.
  Model lama: 48 edge ganda, signed volume tetap positif (0.9954). Jadi signed volume saja tidak cukup.
  Model baru: 0 edge ganda, 0 edge terbuka, volume 2.1850.
- Dampak di `raster3d.py` (backface culling): 186 -> 198 segitiga lolos, 41 794 -> 60 136 fragment.
  Render sebelum/sesudah: `out/lab1_winding_sebelum_sesudah.png`. Entri Lab 2/3 sebelumnya dibuat dengan model lama,
  jadi angka render Lab 2 dan Lab 3 harus diukur ulang.
- Klaim lama di `broken_scene.py` ("Winding konsisten di mymodel.obj") sebelumnya TIDAK benar. Sekarang sudah benar.
- `worked_example.py` diperluas: langkah antara untuk hitungan tangan object->world->view (cocok 6 desimal), telusuran kolom V,
  tabel presisi depth 1/z (near/far 0.1/20 vs 0.01, 1.0, far 1000), dan cek handedness otomatis.
- `tests.py` dibuat: 9 tes, termasuk 3 uji negatif (cermin model, cermin kamera, viewport tanpa flip y). 9/9 PASS.
- `logs/toolchain.txt` dilengkapi: NumPy 2.5.4, Pillow 12.3.0, npm, Chrome 156.0.8078.74, Safari 27.2, Three.js r128, tanggal.
- Laporan Lab 1: `docs/Lab1_Laporan.md` (langkah 5 memakai LearnOpenGL; langkah 6 memakai Reed 2015 dan Microsoft Learn).

## [2026-11-04] Lab 2: audit, penulisan ulang, dan verifikasi nyata
- **Koreksi entri 2026-11-03:** entri itu menulis "VERIFIED", padahal saat diaudit `raytrace.py` belum pernah selesai
  dijalankan (loop Python piksel x segitiga, tidak ada output di out/), `broken_scene.py` hanya mencetak teks,
  near clipping belum ada (hanya membuang segitiga yang seluruhnya di belakang near), top-left rule terbalik, dan
  belum ada E4, mipmap, maupun pengukuran culling.
- Repo starter ditemukan di ~/Downloads/Module3 dan dijalankan di salinan scratch untuk menghasilkan
  data/pusaka_model.obj, data/relief.ppm, ref/temple_ref.ppm (160), dan ref/temple_ref_512.ppm.
  Angka pembanding starter disimpan di logs/lab2_starter_pembanding.txt.
- Ditulis ulang: raster3d.py (Sutherland–Hodgman di clip space, top-left rule, linear light, mipmap trilinear,
  mode naif, culling, depth N-bit), raytrace.py (vektorisasi), broken_scene.py, compare.py; modul baru objio.py,
  ppm_io.py, colorspace.py, metrics.py, perspective_check.py, mipmap_demo.py, culling_check.py; tests.py diperluas.
- Hasil: raster candi identik byte dengan referensi (160 dan 512). Raster vs raytrace 69.8 dB (3 piksel di jahitan
  wrap u=1). Top-left rule menghemat 3 582 fragment ganda tanpa mengubah citra.
- **Temuan:** OBJ candi starter inside-out (signed volume -2.9764); demo inside-out starter terbalik.
- **Temuan di modul:** E1 urutan terbalik tertulis (4,3,-4), yang benar (5,3,-3); Contoh Terpandu memakai aspect=1 untuk frame 800x600.
- Bug: inside-out SSIM 0.789->1.000; zfight 20 336->744 piksel salah, SSIM 0.764->0.991; stretched SSIM 0.735->1.000.
- E4 0.5 vs 0.1, galat UV naif sampai 5.6 kotak saat kamera bergerak. Mipmap: kelap-kelip turun 38x, +17.9 dB ke kebenaran.
- Culling: fragment -26.5 % (mymodel), -20.5 % (candi), citra identik.
- Laporan: docs/Lab2_Laporan.md. tests.py: 27/27 PASS. run_all_labs.py: SEMUA LANGKAH OK.

## [2026-11-04] Lab 3: viewer, perbandingan, prediksi, shadow, reproduksi
- **Viewer diperbaiki:** versi lama memuat `../mymodel.obj` (di luar web/), jadi di `npx serve web`/Pages akan 404 dan
  diam-diam menampilkan silinder pengganti. Texture lama tiruan JS tanpa sRGB; ekspor lama PNG. Sekarang aset dibuat
  `make_model.py` ke web/, texture sRGB, canvas tetap 512x512 + setPixelRatio(1), ekspor PPM, dan error terlihat jelas.
- tools/three_export.py: Chrome headless (GPU Apple M1 Pro via ANGLE Metal), hasil di-POST balik (waktu nyata).
- raster vs Three.js: 33.8 dB / SSIM 0.9957. Sumber selisih dipisah: tanpa texture + tanpa MSAA 52.2 dB (bagian dalam
  tepat +1 kode = round vs floor; cakupan beda 2 piksel); konvensi pusat texel + mipmap menjelaskan selisih texture
  (34.75 -> 42.31 dB); MSAA menambah 640 piksel tepi.
- Prediksi ditulis dulu (docs/Lab3_prediksi.md, 14:42:53), baru shadow diimplementasikan: shadow map ortografik di
  raster3d.py, shadow ray di raytrace.py, plus lantai (add_ground).
- Terukur: raster 0.105 s, +shadow 0.152 s; raytrace 2.42 s, +shadow 3.68 s; Three.js 0.60 ms.
  Pengukuran pertama shadow raytrace x2.12 = inefisiensi implementasi (occluded() per face); setelah digabung x1.52
  sesuai prediksi, citra identik. Bias 0 = acne di ~60k piksel; bias 4 texel @2048 = 47.9 dB vs raytrace.
- Skala 200k segitiga: Three.js 1.10 ms/frame (load 291 ms); raster3d 18.2 s; raytrace ~17 menit (ekstrapolasi).
- Reproduksi: clone bersih + venv + make_model + tests hijau + npx serve web, transkrip di logs/lab3_clean_clone.txt.
- Disiapkan .gitignore + workflow Pages. Deploy BELUM: butuh repo GitHub milik Andy (langkah di README).

## 2026-11-10: deploy GitHub Pages
- Modul 1–5 digabung ke satu repo (https://github.com/andybagus26/Grafkom-Modul-1-5). Workflow Pages dipindah ke root repo (GitHub hanya menjalankan
  workflow di `.github/` root); ia tetap membuat aset viewer dengan make_model.py dan menjalankan tests.py dulu.
- `.gitignore`: `*.pdf` diganti `Module3_ID.pdf`, supaya PDF laporan ikut repo tetapi PDF modul dosen tidak.
- URL: https://andybagus26.github.io/Grafkom-Modul-1-5/Modul3_Grafkom/web/. Dibuka di Chrome headless: model tampil, tanpa error.
- Clone bersih dari GitHub: tests.py 27 PASS (logs/lab3_github_clone.txt).
