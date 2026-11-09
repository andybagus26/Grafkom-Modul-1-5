"""Build gapura_bentar.glb + gapura_bentar.json -- my own model for Lab 3
(option a): a procedural, low-poly CANDI BENTAR (split gateway) in the style of
Gapura Wringin Lawang, Trowulan (Mojokerto, East Java; Majapahit, 14th c.),
with 6 bilingual tap-to-learn hotspots.

Scale. The real gate is about 15.5 m tall on a 13 m x 11.5 m footprint with a
3.5 m passage (sources in the hotspot text and README). A 15.5 m object is
useless on a table, so this model is a fixed 1:50 SCALE MODEL: 0.31 m tall,
0.26 m x 0.23 m, passage 0.07 m. index.html keeps ar-scale="fixed", and the
scale is stated to the user in a hotspot, so nobody mistakes it for life size.

Geometry. Only boxes (box() from make_temple_glb.py: 24 unshared vertices,
flat normals, CCW-from-outside winding). Each half is a stack of shrinking
boxes whose INNER face stays on the plane x = +/-0.035 -- that flat, sheer
inner face is what makes a candi bentar look like one candi cut in two.

Hotspots are computed from the same PARTS table that builds the mesh (centre of
a named face, pushed 1 mm out along its normal), so a hotspot cannot drift off
the model when a dimension changes -- the "floating hotspot" failure in the
module's Case Study.

Provenance: geometry authored by me (Andy Bagus, 2026), procedural, no
third-party mesh, no AI-generated geometry; released CC0. Proportions only
loosely follow the published overall dimensions -- it is NOT a survey-accurate
replica of the monument.

Run: python make_gapura_glb.py -> assets/gapura_bentar.glb + assets/gapura_bentar.json
"""
from __future__ import annotations

import os

from make_temple_glb import OUT_DIR, write_glb, write_hotspots

SCALE = 1 / 50                     # model metres per real metre
GAP = 0.035                        # half of the 0.07 m passage (3.5 m real)

BRICK = (0.62, 0.29, 0.20, 1.0)    # Majapahit red brick (bata merah)
BRICK_D = (0.55, 0.25, 0.18, 1.0)
BRICK_L = (0.68, 0.34, 0.24, 1.0)
STONE = (0.42, 0.42, 0.40, 1.0)    # andesite steps

# one half (x > 0) as (name, x_out, y_lo, y_hi, z_half, colour); inner face at x = GAP
_HALF = [
    ("kaki",    0.130, 0.012, 0.070, 0.100, BRICK_D),
    ("badan",   0.115, 0.070, 0.160, 0.085, BRICK),
    ("pelipit", 0.122, 0.160, 0.172, 0.092, BRICK_L),
    ("atap1",   0.105, 0.172, 0.215, 0.075, BRICK),
    ("atap2",   0.090, 0.215, 0.250, 0.058, BRICK_L),
    ("atap3",   0.075, 0.250, 0.280, 0.040, BRICK),
    ("puncak",  0.060, 0.280, 0.310, 0.022, BRICK_L),
]


def _box_spec(x0, x1, y0, y1, z0, z1, color):
    return dict(kind="box", center=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                half=((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2), color=color)


def build_parts():
    parts = {"batur": _box_spec(-0.130, 0.130, 0.0, 0.012, -0.115, 0.115, BRICK_D)}
    for side, sgn in (("timur", +1), ("barat", -1)):
        for name, xo, y0, y1, zh, col in _HALF:
            xa, xb = sorted((sgn * GAP, sgn * xo))
            parts[f"{name}_{side}"] = _box_spec(xa, xb, y0, y1, -zh, zh, col)
    # andesite steps at both ends of the passage
    parts["tangga_utara"] = _box_spec(-GAP, GAP, 0.0, 0.006, 0.115, 0.135, STONE)
    parts["tangga_selatan"] = _box_spec(-GAP, GAP, 0.0, 0.006, -0.135, -0.115, STONE)
    return parts


PARTS = build_parts()


def face_point(part, axis, sign, along=None):
    """Centre of the face of PARTS[part] whose outward normal is sign*axis,
    lifted 1 mm off the surface. `along` optionally overrides other coords
    (dict axis -> value) to slide the point within the face."""
    c, h = PARTS[part]["center"], PARTS[part]["half"]
    p = list(c)
    p[axis] = c[axis] + sign * (h[axis] + 0.001)
    for ax, v in (along or {}).items():
        p[ax] = v
    n = [0.0, 0.0, 0.0]
    n[axis] = float(sign)
    return [round(v, 4) for v in p], n


def build_hotspots():
    X, Y, Z = 0, 1, 2
    spots = []

    def add(id_, part, axis, sign, along, name_en, name_id, text_en, text_id):
        pos, nrm = face_point(part, axis, sign, along)
        spots.append(dict(id=id_, part=part, position=pos, normal=nrm, name_en=name_en,
                          name_id=name_id, text_en=text_en, text_id=text_id))

    add("celah", "badan_timur", X, -1, {Y: 0.115}, "The split (lawang)", "Celah Gapura (lawang)",
        "A candi bentar is a gateway built like one temple sliced down the middle: two mirror-image "
        "halves with sheer, flat inner faces and NO roof joining them over the path. A roofed gate "
        "that closes over the passage is a different type, the paduraksa (Gapura Bajang Ratu, also "
        "in Trowulan, is one). The model's passage is 7 cm = 3.5 m at real size.",
        "Candi bentar adalah gapura yang dibangun seperti satu candi yang dibelah dua: dua belahan "
        "kembar-cermin dengan sisi dalam yang tegak dan rata, TANPA atap yang menyatukan keduanya di "
        "atas jalan. Gapura yang beratap menutup jalan adalah tipe lain, paduraksa (contohnya Gapura "
        "Bajang Ratu, juga di Trowulan). Celah model ini 7 cm = 3,5 m pada ukuran sebenarnya.")
    add("bata", "badan_barat", Z, +1, {X: -0.075}, "Red brick (bata merah)", "Bata Merah",
        "Wringin Lawang is built mostly of fired red brick, the typical material of Majapahit "
        "architecture around its capital at Trowulan -- unlike the andesite stone of Central "
        "Javanese temples such as Prambanan or Borobudur.",
        "Wringin Lawang sebagian besar dibangun dari bata merah yang dibakar, bahan khas arsitektur "
        "Majapahit di sekitar ibu kotanya di Trowulan -- berbeda dengan batu andesit candi-candi Jawa "
        "Tengah seperti Prambanan atau Borobudur.")
    add("atap", "atap2_timur", Z, +1, {X: 0.0625}, "Stepped upper part", "Atap Bertingkat",
        "Each half rises in shrinking steps like the roof of a candi. Seen from the front, the two "
        "halves together outline one complete temple silhouette with its centre cut out -- the path "
        "itself is the missing middle.",
        "Setiap belahan naik bertingkat-tingkat dan mengecil seperti atap candi. Dari depan, kedua "
        "belahan bersama-sama membentuk siluet satu candi utuh yang bagian tengahnya terpotong -- "
        "jalan itulah bagian tengah yang hilang.")
    add("tangga", "tangga_utara", Y, +1, None, "Stone steps", "Anak Tangga Batu",
        "Although the gate itself is brick, its steps are stone. Steps and thresholds take the most "
        "wear from feet, so a harder material is used exactly where the load is.",
        "Meskipun gapuranya dari bata, anak tangganya dari batu. Tangga dan ambang paling sering "
        "terinjak, jadi bahan yang lebih keras dipakai tepat di bagian yang paling menanggung beban.")
    add("skala", "kaki_timur", Z, +1, {X: 0.0825}, "Size: 1:50 scale model", "Ukuran: Model Skala 1:50",
        "The real gate is about 15.5 m tall on a footprint of roughly 13 m x 11.5 m. This AR model is "
        "a fixed 1:50 scale model (31 cm tall) so it fits on a table; at 1:1 it would be as tall as a "
        "five-storey building.",
        "Gapura aslinya setinggi sekitar 15,5 m dengan denah kira-kira 13 m x 11,5 m. Model AR ini "
        "adalah model skala 1:50 yang tetap (tinggi 31 cm) agar muat di atas meja; pada skala 1:1 "
        "tingginya setara gedung lima lantai.")
    add("nama", "puncak_barat", Y, +1, None, "Name and purpose", "Nama dan Fungsi",
        "'Wringin Lawang' means 'banyan gate', after a banyan (beringin) tree that once grew beside "
        "it. Its original purpose is still debated: some scholars see it as an entrance to the "
        "Majapahit capital, others -- pointing to old wells nearby -- as the gate of a residential "
        "compound.",
        "'Wringin Lawang' berarti 'gapura beringin', dari pohon beringin yang dahulu tumbuh di "
        "dekatnya. Fungsi aslinya masih diperdebatkan: sebagian ahli menganggapnya pintu masuk ibu "
        "kota Majapahit, sebagian lain -- berdasarkan sumur-sumur kuno di sekitarnya -- menganggapnya "
        "gapura sebuah kompleks hunian.")
    return spots


HOTSPOTS = build_hotspots()

SOURCES = [
    "Wikipedia, 'Trowulan' (section Wringin Lawang), https://en.wikipedia.org/wiki/Trowulan",
    "beritajatim.com, article on Candi Wringin Lawang (height 15.50 m, footprint 13 x 11.5 m, brick body, "
    "stone steps, banyan-tree name, two proposed functions), https://beritajatim.com/?p=1098816",
    "detik.com Jatim, '5 Situs Bersejarah Trowulan Bukti Kejayaan Majapahit' (14th century), "
    "https://www.detik.com/jatim/budaya/d-8038359/5-situs-bersejarah-trowulan-bukti-kejayaan-majapahit",
]

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    glb = os.path.join(OUT_DIR, "gapura_bentar.glb")
    js = os.path.join(OUT_DIR, "gapura_bentar.json")
    write_glb(glb, PARTS, generator="Module5 make_gapura_glb.py (Andy Bagus, procedural, deterministic, CC0)")
    write_hotspots(js, HOTSPOTS, model="gapura_bentar.glb",
                   comment="Candi bentar in the style of Gapura Wringin Lawang (Trowulan, Majapahit). "
                           "1:50 scale model, procedural, authored by Andy Bagus, CC0. Not a survey-accurate replica.",
                   extra={"scale": "1:50", "sources": SOURCES})
    print(f"wrote {glb} ({os.path.getsize(glb) / 1024:.1f} KB, {len(PARTS)} parts)")
    print(f"wrote {js} ({len(HOTSPOTS)} hotspots)")
