"""
transforms.py
Implementasi modul transformasi 3D affine, proyeksi, dan viewport.
Konvensi:
- Column vector: p' = M @ p (rantai matriks kanan ke kiri: P @ V @ M @ p)
- Right-handed coordinate system
- Kamera menghadap ke sumbu -z
- Clip / NDC space: x, y, z dalam [-1, 1], near plane di z = -1, far di z = +1
- Viewport: Membalik y (y=0 di atas, y=height di bawah)
"""

import math
import numpy as np

def identity():
    """Mengembalikan matriks identitas 4x4."""
    return np.eye(4, dtype=np.float64)

def translate(tx, ty, tz):
    """Matriks translasi 4x4."""
    M = np.eye(4, dtype=np.float64)
    M[0, 3] = tx
    M[1, 3] = ty
    M[2, 3] = tz
    return M

def scale(sx, sy, sz):
    """Matriks scaling 4x4."""
    M = np.eye(4, dtype=np.float64)
    M[0, 0] = sx
    M[1, 1] = sy
    M[2, 2] = sz
    return M

def rotate_x(angle_rad):
    """Rotasi mengelilingi sumbu X sebesar sudut radian."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    M = np.eye(4, dtype=np.float64)
    M[1, 1] = c
    M[1, 2] = -s
    M[2, 1] = s
    M[2, 2] = c
    return M

def rotate_y(angle_rad):
    """Rotasi mengelilingi sumbu Y sebesar sudut radian."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    M = np.eye(4, dtype=np.float64)
    M[0, 0] = c
    M[0, 2] = s
    M[2, 0] = -s
    M[2, 2] = c
    return M

def rotate_z(angle_rad):
    """Rotasi mengelilingi sumbu Z sebesar sudut radian."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    M = np.eye(4, dtype=np.float64)
    M[0, 0] = c
    M[0, 1] = -s
    M[1, 0] = s
    M[1, 1] = c
    return M

def look_at(eye, target, up):
    """
    Membangun matriks View (kamera).
    eye: (x, y, z) posisi kamera
    target: (x, y, z) titik tujuan pandang
    up: (x, y, z) vektor penunjuk atas

    Kamera menghadap ke arah -z di view space:
    z_axis = normalize(eye - target)  (arah pandang maju adalah -z_axis)
    x_axis = normalize(cross(up, z_axis)) (kanan)
    y_axis = cross(z_axis, x_axis) (atas aktual)
    """
    eye = np.array(eye, dtype=np.float64)
    target = np.array(target, dtype=np.float64)
    up = np.array(up, dtype=np.float64)

    # Vektor maju kamera (di view space menghadap -z, maka z_axis = eye - target)
    forward = eye - target
    norm_f = np.linalg.norm(forward)
    if norm_f == 0:
        z_axis = np.array([0.0, 0.0, 1.0])
    else:
        z_axis = forward / norm_f

    # Sumbu kanan (x)
    right = np.cross(up, z_axis)
    norm_r = np.linalg.norm(right)
    if norm_r == 0:
        x_axis = np.array([1.0, 0.0, 0.0])
    else:
        x_axis = right / norm_r

    # Sumbu atas tegak lurus (y)
    y_axis = np.cross(z_axis, x_axis)

    # Matriks rotasi orientasi kamera (baris adalah x, y, z kamera)
    R = np.eye(4, dtype=np.float64)
    R[0, 0:3] = x_axis
    R[1, 0:3] = y_axis
    R[2, 0:3] = z_axis

    # Matriks translasi posisi kamera
    T = translate(-eye[0], -eye[1], -eye[2])

    # View = R @ T
    return R @ T

def perspective(fov_y_rad, aspect, near, far):
    """
    Membangun matriks proyeksi perspektif standar OpenGL / NDC [-1, 1]^3.
    near plane dipetakan ke z_ndc = -1
    far plane dipetakan ke z_ndc = +1
    w_clip = -z_eye (karena kamera menghadap -z)
    """
    tan_half_fov = math.tan(fov_y_rad / 2.0)

    P = np.zeros((4, 4), dtype=np.float64)
    P[0, 0] = 1.0 / (aspect * tan_half_fov)
    P[1, 1] = 1.0 / tan_half_fov
    P[2, 2] = -(far + near) / (far - near)
    P[2, 3] = -(2.0 * far * near) / (far - near)
    P[3, 2] = -1.0  # w_clip = -z_view
    return P

def viewport(width, height):
    """
    Transformasi dari NDC [-1, 1]^2 ke koordinat layar piksel [0, width] x [0, height].
    Membalik y karena y layar bertambah ke bawah:
    x_screen = (x_ndc + 1) * 0.5 * width
    y_screen = (1 - y_ndc) * 0.5 * height
    z_screen = (z_ndc + 1) * 0.5  (skala depth [0, 1])
    """
    M = np.eye(4, dtype=np.float64)
    M[0, 0] = width / 2.0
    M[0, 3] = width / 2.0
    M[1, 1] = -height / 2.0
    M[1, 3] = height / 2.0
    M[2, 2] = 0.5
    M[2, 3] = 0.5
    return M


# ---------------------------------------------------------------------------
# Helper tambahan (Lab 2)
# ---------------------------------------------------------------------------
def rot_y_deg(angle_deg):
    """Pembungkus derajat. Nama berakhiran _deg supaya radian/derajat tidak tertukar (pitfall)."""
    return rotate_y(math.radians(angle_deg))


def perspective_deg(fov_y_deg, aspect, near, far):
    return perspective(math.radians(fov_y_deg), aspect, near, far)


def perspective_divide_2d(p3, d):
    """Proyeksi segitiga sebangun 'telanjang' (Contoh E1): pinhole di origin menghadap -z,
    bidang citra pada jarak d -> (d*x/|z|, d*y/|z|)."""
    x, y, z = p3[:3]
    return np.array([d * x / abs(z), d * y / abs(z)])


def to_homogeneous(points):
    points = np.asarray(points, dtype=np.float64)
    return np.c_[points, np.ones(len(points))]


def project(P, V, M, points):
    """points (N,3) -> (clip (N,4), ndc (N,3)). Satu perkalian MVP per vertex, lalu bagi w."""
    clip = (P @ V @ M @ to_homogeneous(points).T).T
    return clip, clip[:, :3] / clip[:, 3:4]


def viewport_points(ndc, width, height):
    """NDC (N,3) -> layar (N,3): x piksel, y piksel (ke bawah), depth = z NDC (tidak diubah)."""
    ndc = np.asarray(ndc, dtype=np.float64)
    x = (ndc[:, 0] + 1.0) * 0.5 * width
    y = (1.0 - ndc[:, 1]) * 0.5 * height
    return np.c_[x, y, ndc[:, 2]]


def orthographic(left, right, bottom, top, near, far):
    """Proyeksi ortografik gaya OpenGL: kotak [l,r]x[b,t]x[-near,-far] (view space) -> NDC [-1,1]^3.
    Tidak ada pembagian perspektif (w tetap 1). Dipakai untuk shadow map light directional."""
    M = np.eye(4, dtype=np.float64)
    M[0, 0] = 2.0 / (right - left)
    M[1, 1] = 2.0 / (top - bottom)
    M[2, 2] = -2.0 / (far - near)
    M[0, 3] = -(right + left) / (right - left)
    M[1, 3] = -(top + bottom) / (top - bottom)
    M[2, 3] = -(far + near) / (far - near)
    return M
