"""
worked_example.py
Lab 1: telusuran satu vertex dari mymodel.obj melewati enam space:
    Object -> World -> View -> Clip -> NDC -> Screen
ditambah:
    - langkah antara (intermediate) untuk dicocokkan dengan hitungan tangan,
    - telusuran kolom matriks M dan V (Lab 1 langkah 4),
    - analisis presisi depth 1/z dengan near/far milik scene ini (Lab 1 langkah 6a),
    - cek handedness otomatis (Lab 1 langkah 6d).

Semua angka di laporan Lab 1 diambil dari output skrip ini (logs/lab1_worked_example.txt).
Jalankan: python3 worked_example.py | tee logs/lab1_worked_example.txt
"""

import math
import numpy as np
import transforms

np.set_printoptions(precision=4, suppress=True)

# ---------------------------------------------------------------------------
# Parameter scene Lab 1 (dipatok di sini supaya satu sumber kebenaran)
# ---------------------------------------------------------------------------
OBJ_PATH = "mymodel.obj"
VERTEX_INDEX = 1                     # indeks OBJ berbasis 1: vertex pertama = cincin dasar, segmen 0
ROT_Y_DEG = 30.0
TRANSLATION = (0.0, 0.5, -1.0)
EYE = (0.0, 1.5, 3.5)
TARGET = (0.0, 0.5, -1.0)
UP = (0.0, 1.0, 0.0)
FOV_Y_DEG = 60.0
WIDTH, HEIGHT = 512, 512
NEAR, FAR = 0.1, 20.0


def load_positions(path):
    pos = []
    with open(path) as f:
        for line in f:
            p = line.split()
            if p and p[0] == "v":
                pos.append([float(p[1]), float(p[2]), float(p[3])])
    return np.asarray(pos, dtype=np.float64)


def fmt(v, n=4):
    return "[" + ", ".join(f"{x:.{n}f}" for x in v) + "]"


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def build_matrices():
    M = transforms.translate(*TRANSLATION) @ transforms.rotate_y(math.radians(ROT_Y_DEG))
    V = transforms.look_at(EYE, TARGET, UP)
    P = transforms.perspective(math.radians(FOV_Y_DEG), WIDTH / HEIGHT, NEAR, FAR)
    Vp = transforms.viewport(WIDTH, HEIGHT)
    return M, V, P, Vp


def trace_vertex(positions, M, V, P, Vp):
    section("1. TELUSURAN SATU VERTEX (object -> world -> view -> clip -> NDC -> screen)")
    p_obj = np.append(positions[VERTEX_INDEX - 1], 1.0)
    print(f"Vertex #{VERTEX_INDEX} dari {OBJ_PATH} (baris 'v' ke-{VERTEX_INDEX})")
    print(f"1. Object (p_obj)   : {fmt(p_obj)}")

    # --- Langkah antara untuk hitungan tangan: object -> world ---
    c, s = math.cos(math.radians(ROT_Y_DEG)), math.sin(math.radians(ROT_Y_DEG))
    x, y, z = p_obj[:3]
    rx, ry, rz = c * x + s * z, y, -s * x + c * z
    print(f"   [tangan] cos30={c:.6f}, sin30={s:.6f}")
    print(f"   [tangan] R_y(30): x'= c*x + s*z = {rx:.6f}; y'= y = {ry:.6f}; z'= -s*x + c*z = {rz:.6f}")
    print(f"   [tangan] + T{TRANSLATION} -> ({rx + TRANSLATION[0]:.6f}, {ry + TRANSLATION[1]:.6f}, {rz + TRANSLATION[2]:.6f})")
    p_world = M @ p_obj
    print(f"2. World (p_world)  : {fmt(p_world)}")

    # --- Langkah antara untuk hitungan tangan: world -> view ---
    eye, target, up = map(np.asarray, (EYE, TARGET, UP))
    f = eye - target
    zc = f / np.linalg.norm(f)
    xc = np.cross(up, zc); xc /= np.linalg.norm(xc)
    yc = np.cross(zc, xc)
    d = p_world[:3] - eye
    print(f"   [tangan] eye - target = {fmt(f, 6)}, |.| = {np.linalg.norm(f):.6f}")
    print(f"   [tangan] z_cam = {fmt(zc, 6)}  x_cam = {fmt(xc, 6)}  y_cam = {fmt(yc, 6)}")
    print(f"   [tangan] p_world - eye = {fmt(d, 6)}")
    print(f"   [tangan] view = (x_cam.d, y_cam.d, z_cam.d) = ({xc @ d:.6f}, {yc @ d:.6f}, {zc @ d:.6f})")
    p_view = V @ p_world
    print(f"3. View (p_view)    : {fmt(p_view)}   (z < 0: di depan kamera)")

    p_clip = P @ p_view
    print(f"4. Clip (p_clip)    : {fmt(p_clip)}   (w_clip = -z_view = {-p_view[2]:.4f})")
    inside = all(-p_clip[3] <= p_clip[k] <= p_clip[3] for k in range(3))
    print(f"   lolos uji clip -w <= x,y,z <= w ? {inside}")

    p_ndc = p_clip / p_clip[3]
    print(f"5. NDC (p_ndc)      : {fmt(p_ndc[:3])}   (di dalam [-1,1]^3 ? {bool(np.all(np.abs(p_ndc[:3]) <= 1))})")

    p_scr = Vp @ p_ndc
    print(f"6. Screen           : x = {p_scr[0]:.2f} px, y = {p_scr[1]:.2f} px, depth = {p_scr[2]:.4f}"
          f"  (canvas {WIDTH}x{HEIGHT}, y ke bawah)")

    # Cek silang: rantai penuh dalam satu matriks harus memberi hasil identik
    full = P @ V @ M @ p_obj
    print(f"   cek silang P@V@M@p = {fmt(full)}  selisih maks dengan langkah-demi-langkah = "
          f"{np.max(np.abs(full - p_clip)):.2e}")
    return p_view


def read_columns(M, V):
    section("2. MEMBACA KOLOM MATRIKS (Lab 1 langkah 4)")
    print("Matriks model M = T(0, 0.5, -1) @ R_y(30 deg):")
    print(M)
    names = ["+x lokal", "+y lokal", "+z lokal"]
    for k in range(3):
        print(f"- kolom {k}: {names[k]} model pergi ke arah world {fmt(M[:3, k])}")
    print(f"- kolom 3: origin model (0,0,0) mendarat di world {fmt(M[:3, 3])}")
    print(f"  det(M[:3,:3]) = {np.linalg.det(M[:3, :3]):.6f}  (+1 = rotasi murni, tidak ada cermin)")

    print("\nMatriks view V = look_at(eye=(0,1.5,3.5), target=(0,0.5,-1), up=(0,1,0)):")
    print(V)
    world_axes = ["+x world", "+y world", "+z world"]
    for k in range(3):
        print(f"- kolom {k}: {world_axes[k]} dilihat kamera sebagai arah view {fmt(V[:3, k])}")
    print(f"- kolom 3: origin world (0,0,0) berada di view {fmt(V[:3, 3])}")
    print("  Baris V[:3,:3] = sumbu kamera (kanan, atas, belakang) dinyatakan dalam world:")
    for k, n in enumerate(["x_cam (kanan)", "y_cam (atas)", "z_cam (belakang, kamera melihat ke -z_cam)"]):
        print(f"    baris {k}: {n} = {fmt(V[k, :3])}")
    Vinv = np.linalg.inv(V)
    print(f"  inv(V) kolom 3 = posisi kamera di world {fmt(Vinv[:3, 3])}  (harus = eye {EYE})")

    MV = V @ M
    print(f"\nGabungan V@M: origin MODEL di view space = {fmt(MV[:3, 3])}")
    print(f"  jarak origin model ke kamera = {np.linalg.norm(MV[:3, 3]):.4f}"
          f"  (cek: |eye - (0,0.5,-1)| = {np.linalg.norm(np.subtract(EYE, TRANSLATION)):.4f})")


def depth_precision(positions, M, V):
    section("3. PRESISI DEPTH 1/z (Lab 1 langkah 6a)")
    pv = (V @ M @ np.c_[positions, np.ones(len(positions))].T).T
    dist = -pv[:, 2]
    zmin, zmax = dist.min(), dist.max()
    print(f"Jarak view (-z_view) seluruh vertex model: {zmin:.4f} .. {zmax:.4f}")

    def window_depth(zd, n, f):
        """depth jendela [0,1] (konvensi GL: z_ndc lalu (z+1)/2) untuk jarak positif zd."""
        z_ndc = (f + n) / (f - n) - 2.0 * f * n / ((f - n) * zd)
        return 0.5 * (z_ndc + 1.0)

    def step_world(zd, n, f, bits=24):
        """lebar satu langkah depth buffer integer di world unit pada jarak zd:
        dz ~= d_step / (d depth/d z) dengan d depth/dz = f n / ((f - n) z^2)."""
        d_step = 1.0 / (2 ** bits - 1)
        return d_step * (f - n) * zd ** 2 / (f * n)

    print(f"\n{'near':>6} {'far':>6} | {'depth@zmin':>11} {'depth@zmax':>11} {'rentang dipakai':>16} | "
          f"{'langkah24b@zmin':>16} {'langkah24b@zmax':>16} {'langkah16b@zmax':>16}")
    for n, f in [(NEAR, FAR), (0.01, FAR), (1.0, FAR), (NEAR, 1000.0)]:
        d0, d1 = window_depth(zmin, n, f), window_depth(zmax, n, f)
        print(f"{n:6.2f} {f:6.0f} | {d0:11.6f} {d1:11.6f} {d1 - d0:16.6f} | "
              f"{step_world(zmin, n, f):16.3e} {step_world(zmax, n, f):16.3e} {step_world(zmax, n, f, 16):16.3e}")
    half = 2.0 * NEAR * FAR / (FAR + NEAR)
    print(f"\nDengan near={NEAR}, far={FAR}: setengah rentang depth [0, 0.5] sudah habis di jarak "
          f"{half:.4f} (= 2nf/(f+n)).")
    print("Interpretasi: depth ~ 1/z, jadi resolusi menumpuk dekat near plane. Near 10x lebih kecil")
    print("membuat langkah depth di jarak model ~10x lebih kasar; far praktis tidak berpengaruh.")


def handedness_checks(M, V, P, Vp):
    section("4. CEK HANDEDNESS OTOMATIS (Lab 1 langkah 6d)")
    ok = True
    dM = np.linalg.det(M[:3, :3])
    dV = np.linalg.det(V[:3, :3])
    print(f"- det(M[:3,:3]) = {dM:+.6f}  -> {'OK' if dM > 0 else 'GAGAL: model dicerminkan'}")
    print(f"- det(V[:3,:3]) = {dV:+.6f}  -> {'OK' if dV > 0 else 'GAGAL: basis kamera left-handed'}")
    ok &= dM > 0 and dV > 0

    # Titik uji: sedikit ke KANAN dan ke ATAS dari target, dilihat kamera. Harus muncul di
    # kanan-atas layar (x > W/2, y < H/2 karena y layar ke bawah). Kalau handedness terbalik
    # di salah satu tahap (cross(up, z) tertukar, P[3,2] = +1, viewport tidak membalik y),
    # setidaknya satu tanda di sini ikut terbalik.
    probe = np.array([TARGET[0] + 0.3, TARGET[1] + 0.3, TARGET[2], 1.0])
    s = Vp @ ((P @ V @ probe) / (P @ V @ probe)[3])
    right_ok, up_ok = s[0] > WIDTH / 2, s[1] < HEIGHT / 2
    print(f"- titik uji (+x,+y dari target) -> layar ({s[0]:.1f}, {s[1]:.1f}): "
          f"kanan={'OK' if right_ok else 'GAGAL'}, atas={'OK' if up_ok else 'GAGAL'}")
    ok &= right_ok and up_ok

    # Segitiga CCW di world (dilihat dari kamera) harus punya area bertanda positif di NDC.
    tri = [np.array([*TARGET, 1.0]) + np.array(o) for o in ([0, 0, 0, 0], [0.5, 0, 0, 0], [0, 0.5, 0, 0])]
    ndc = [(P @ V @ t)[:2] / (P @ V @ t)[3] for t in tri]
    area = (ndc[1][0] - ndc[0][0]) * (ndc[2][1] - ndc[0][1]) - (ndc[1][1] - ndc[0][1]) * (ndc[2][0] - ndc[0][0])
    print(f"- segitiga CCW menghadap kamera: area bertanda di NDC = {area:+.6f} -> "
          f"{'OK (front face)' if area > 0 else 'GAGAL: winding terbalik'}")
    ok &= area > 0
    print(f"HASIL CEK HANDEDNESS: {'LULUS' if ok else 'GAGAL'}")
    return ok


def main():
    positions = load_positions(OBJ_PATH)
    M, V, P, Vp = build_matrices()
    print("LAB 1: SPACE TRACING - mymodel.obj")
    print(f"Scene: R_y({ROT_Y_DEG:g} deg) lalu T{TRANSLATION}; kamera eye={EYE} target={TARGET} up={UP};")
    print(f"       fov_y={FOV_Y_DEG:g} deg, aspect={WIDTH}/{HEIGHT}, near={NEAR}, far={FAR}")
    trace_vertex(positions, M, V, P, Vp)
    read_columns(M, V)
    depth_precision(positions, M, V)
    handedness_checks(M, V, P, Vp)


if __name__ == "__main__":
    main()
