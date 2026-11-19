# Praktikum Grafika Komputer, Modul 1–5

Andy Bagus · NIM 20241337033 · S1 Informatika, Universitas Muhammadiyah Surabaya

Situs (GitHub Pages): https://andybagus26.github.io/Grafkom-Modul-1-5/

| Modul | Folder | Yang bisa dibuka di browser |
|---|---|---|
| 1 | `Modul1_Grafkom/Module 1-2/` | `report/report.html` (Lab 3) |
| 2 | `Modul2_Grafkom/Module2/` | `web/`: viewer denah (Three.js) |
| 3 | `Modul3_Grafkom/` | `web/`: viewer model bangunan (Three.js) |
| 4 | `Modul4_Grafkom/Module4/` | `build/web/`: proyek Godot (ekspor Web) |
| 5 | `Modul5_Grafkom/Module5/` | `ar_app/`: aplikasi AR (`<model-viewer>`) |

Tiap folder punya README sendiri: cara menjalankan, tabel unit, tes, dan
penyimpangan dari rencana modul. Laporan dan studi pendahuluan dikumpulkan
terpisah, tidak lewat repo ini.

Deploy: `.github/workflows/pages.yml` berjalan di setiap push ke `main`. Workflow
ini membuat ulang aset viewer Modul 3 (`make_model.py`), menjalankan tes Modul 3,
lalu menerbitkan seluruh repo sebagai satu situs. `index.html` di root menautkan
semua modul.

PDF modul dari dosen (`Module*_ID.pdf`, `Module5_EN.pdf`) sengaja tidak ikut repo
karena itu materi pengajar.
