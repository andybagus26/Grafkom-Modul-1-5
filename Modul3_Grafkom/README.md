# Praktikum Grafika Komputer, Modul 3
**3D Transform, Proyeksi, Texture, dan Real-Time**

- **Nama**: Andy Bagus
- **NIM**: 20241337033
- **Program Studi**: Informatika, Universitas Muhammadiyah Surabaya

Implementasi pipeline 3D dari nol dengan NumPy: transformasi, proyeksi perspektif, rasterisasi z-buffer
dengan interpolasi perspective-correct, texture bilinear dan mipmap, ray tracing (Möller-Trumbore), serta
viewer real-time Three.js di folder `web/`.

## Toolchain
Dicatat otomatis pada 2026-11-04 (`logs/toolchain.txt`):

| Komponen | Versi |
|---|---|
| OS | macOS 27.2 (build 26B123), Darwin 27.2.0, arm64 |
| Python | 3.14.7 |
| NumPy | 2.5.4 |
| Pillow (cross-check saja) | 12.3.0 |
| Node / npm | v26.12.0 / 11.20.0 |
| Browser | Google Chrome 156.0.8078.74, Safari 27.2 |
| Three.js | r128 (CDN) |

## Konvensi (dipatok sekali, tidak dicampur)
- Column vector, pre-multiply: p' = M · p, rantai dibaca kanan ke kiri (P · V · M · p)
- World/view right-handed, kamera menghadap −z
- NDC [−1, 1]³ dengan near di z = −1 (NDC ini sendiri left-handed karena proyeksi membalik z)
- Viewport membalik y (y layar ke bawah)
- Winding CCW = front face
- Origin UV kiri-bawah (flip v satu kali saat load)

## Status

| Bagian | Status | Bukti |
|---|---|---|
| **Studi Pendahuluan** Q1–Q5 | ✅ Selesai | dikumpulkan terpisah; diagramnya dibuat `tools/figures_studi.py` |
| **Lab 1**: model, telusuran 6 space, kolom M/V, refleksi | ✅ Selesai | `logs/lab1_*.txt` |
| **Lab 2**: pipeline dari nol, 3 bug, E4, mipmap, culling | ✅ Selesai | `logs/lab2_*.txt` |
| **Lab 3**: Three.js, raster vs Three.js, prediksi + shadow, reproduksi | ✅ Selesai, sudah di GitHub Pages | `docs/Lab3_prediksi.md`, `logs/lab3_*` |

Laporan Lab 1–3, laporan Tugas Analisis, dan studi pendahuluan dikumpulkan terpisah, tidak lewat repo ini.

## Lab 1: cara mereproduksi

```bash
python3 generate_mymodel.py      # -> mymodel.obj (432 segitiga, UV, winding CCW)
python3 generate_texture.py      # -> texture.ppm (512x512, CC0, karya sendiri)
python3 validate_obj.py          # cek >=200 segitiga, UV, triangulated, winding konsisten
python3 worked_example.py        # telusuran vertex, kolom M/V, presisi depth, cek handedness
python3 tests.py                 # tes otomatis (exit 0 = lulus)
```

| File | Isi |
|---|---|
| `mymodel.obj` | Model pilar bertingkat milik sendiri (bukan `make_model.py`) |
| `texture.ppm` | Texture prosedural, lisensi CC0 |
| `logs/lab1_validate_obj.txt` | Validasi model sebelum/sesudah perbaikan winding |
| `logs/lab1_worked_example.txt` | Angka telusuran object→screen, kolom M/V, tabel presisi depth |
| `logs/lab1_raster_setelah_fix_winding.txt` | Jumlah fragment sebelum/sesudah perbaikan winding |
| `logs/lab1_tests.txt` | Output `tests.py` |
| `out/lab1_winding_sebelum_sesudah.png` | Render sebelum/sesudah perbaikan winding |


## Lab 2: cara mereproduksi

```bash
pip install -r requirements.txt   # numpy==2.5.4, pillow==12.3.0 (Pillow hanya untuk panel PNG)
python3 run_all_labs.py           # semua langkah Lab 1 + Lab 2, menulis ulang logs/ (~8 s)
```

Atau satu per satu:

| Perintah | Isi | Hasil kunci (log) |
|---|---|---|
| `python3 raster3d.py --scene temple` | candi, near clip, z-buffer, UV perspective-correct, Lambert | identik dengan `ref/temple_ref_512.ppm` (PSNR ∞) |
| `python3 raytrace.py --scene temple` | ray pinhole + Möller–Trumbore | vs raster: 69.8 dB, 3 piksel (jahitan wrap u = 1) |
| `python3 raster3d.py --scene mymodel` / `raytrace.py --scene mymodel` | model sendiri | raster vs raytrace: PSNR ∞ |
| `python3 broken_scene.py --all` | inside-out, zfight, stretched | SSIM 0.789→1.000, 0.764→0.991, 0.735→1.000 |
| `python3 perspective_check.py` | Contoh E4, lantai catur, texture berenang | u naif 0.5 vs benar 0.1 |
| `python3 mipmap_demo.py` | piramida mip 4 level, candi dari jauh | kelap-kelip turun 38× |
| `python3 culling_check.py` | back-face culling | fragment −26.5 % (mymodel), −20.5 % (candi) |
| `python3 tests.py` | E1–E5, Modul 2, near clip, z-buffer, frame referensi, raster vs raytrace | 27 tes lulus |

**Data:** `data/pusaka_model.obj` + `data/relief.ppm` dihasilkan oleh `make_model.py` repo starter; `ref/` berisi
frame referensi dari renderer starter (pembanding). Kode di folder ini ditulis ulang, bukan disalin dari starter.
Catatan: `data/pusaka_model.obj` ber-winding CW dari luar (inside-out); lihat Lab 2 bug 1.


## Lab 3: viewer real-time

```bash
python3 make_model.py          # membuat juga web/mymodel.obj + web/texture.png
npx serve web                  # buka http://localhost:3000
```

| Perintah | Isi | Hasil kunci |
|---|---|---|
| `python3 tools/three_export.py` | render viewer di Chrome headless, simpan `web/mymodel_three.ppm` + frame time | 0.60 ms/frame (Apple M1 Pro) |
| `python3 compare.py out/mymodel_raster.ppm web/mymodel_three.ppm` | raster NumPy vs Three.js, kamera sama | 33.8 dB, SSIM 0.996 |
| `python3 lab3_benchmark.py` | frame time + hard shadow (shadow map vs shadow ray) | raster 0.105 s, raytrace 2.42 s; shadow ×1.45 / ×1.52 |

Di browser: tombol **Ekspor PPM 512×512** mengunduh `mymodel_three.ppm`. Opsi URL `?tex=0`, `?aa=0`, dan
`?model=nama.obj` dipakai untuk eksperimen di laporan.

## Deploy ke GitHub Pages

**URL Pages:** https://andybagus26.github.io/Grafkom-Modul-1-5/Modul3_Grafkom/web/

Modul 1–5 ada di satu repo, https://github.com/andybagus26/Grafkom-Modul-1-5. Workflow-nya ada di root repo
(`.github/workflows/pages.yml`): setiap push ke `main` menjalankan `pip install -r requirements.txt`,
`make_model.py`, dan `tests.py` di folder ini, lalu menerbitkan seluruh repo sebagai satu situs. Aset viewer
(`web/mymodel.obj`, `web/texture.png`) tetap tidak di-commit, karena dibuat ulang di CI.

## Verified

**2026-11-04**, macOS 27.2 (Apple M1 Pro) / Python 3.14.7 / NumPy 2.5.4 / Chrome 156.0.8078.74 / Three.js r128:
- `python3 run_all_labs.py`: SEMUA LANGKAH OK (Lab 1–3, sekitar 40 s)
- `python3 tests.py`: 27/27 PASS
- clone bersih (simulasi lokal) → `pip install -r requirements.txt` → `python make_model.py` → `python tests.py`
  hijau → `npx serve web` menampilkan model (`logs/lab3_clean_clone.txt`)

**2026-11-10**, sama:
- clone bersih dari GitHub yang sebenarnya (`git clone https://github.com/andybagus26/Grafkom-Modul-1-5.git`) → venv baru → `pip install` → `make_model.py` →
  `tests.py`: 27 PASS, exit 0 (`logs/lab3_github_clone.txt`)
- viewer dibuka dari URL Pages di Chrome 156 headless: pilar bertexture tampil, tanpa error JS / HTTP ≥ 400
  (`out/lab3_pages_live.png`)
