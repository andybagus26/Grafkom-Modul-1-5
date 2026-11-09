"""
objio.py
Loader Wavefront OBJ minimal dari nol: v, vt, f (format a, a/b, a/b/c, a//c, indeks negatif),
poligon ditriangulasi dengan fan.

Origin UV: OBJ/OpenGL menaruh (0,0) di KIRI-BAWAH, sedangkan baris pertama berkas citra ada di ATAS.
v dibalik SATU KALI di sini (flip_v=True), jadi kode lain cukup memakai v_img = koordinat baris
citra ternormalisasi dan tidak perlu memikirkannya lagi (pitfall "origin UV terbalik").
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class Mesh:
    positions: np.ndarray            # (V, 3)
    uvs: np.ndarray                  # (T, 2), v sudah dalam konvensi baris citra jika flip_v
    faces: np.ndarray                # (F, 3) indeks posisi
    face_uvs: np.ndarray | None      # (F, 3) indeks uv, atau None

    @property
    def n_tris(self):
        return len(self.faces)

    def triangle_uvs(self):
        if self.face_uvs is None:
            return np.zeros((len(self.faces), 3, 2))
        return self.uvs[self.face_uvs]

    def flipped_winding(self):
        """Salinan mesh dengan urutan vertex tiap segitiga dibalik (dipakai bug inside-out)."""
        return Mesh(self.positions, self.uvs, self.faces[:, ::-1].copy(),
                    None if self.face_uvs is None else self.face_uvs[:, ::-1].copy())


def _index(token, n_pos, n_uv):
    parts = (token.split("/") + ["", ""])[:3]
    p = int(parts[0])
    p = p - 1 if p > 0 else n_pos + p
    t = None
    if parts[1]:
        t = int(parts[1])
        t = t - 1 if t > 0 else n_uv + t
    return p, t


def load_obj(path, flip_v=True):
    pos, uvs, faces, fuv = [], [], [], []
    with open(path) as f:
        for line in f:
            s = line.split()
            if not s:
                continue
            if s[0] == "v":
                pos.append([float(x) for x in s[1:4]])
            elif s[0] == "vt":
                u, v = float(s[1]), float(s[2])
                uvs.append([u, 1.0 - v if flip_v else v])
            elif s[0] == "f":
                idx = [_index(t, len(pos), len(uvs)) for t in s[1:]]
                for k in range(1, len(idx) - 1):
                    faces.append([idx[0][0], idx[k][0], idx[k + 1][0]])
                    if idx[0][1] is not None:
                        fuv.append([idx[0][1], idx[k][1], idx[k + 1][1]])
    return Mesh(np.asarray(pos, float),
                np.asarray(uvs, float).reshape(-1, 2),
                np.asarray(faces, np.int64).reshape(-1, 3),
                np.asarray(fuv, np.int64) if len(fuv) == len(faces) and fuv else None)
