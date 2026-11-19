"""Module 1 -- memory & bandwidth budget calculator.

Reproduces:
  Example E6 : 1920x1080 RGB888 frame = 6_220_800 B ~= 6 MB / 5.93 MiB;
               10 s @ 30 fps = 1_866_240_000 B ~= 1.87 GB / 1.74 GiB;
               bandwidth ~= 178 MiB/s ~= 1.49 Gbit/s
  Example E7 : 4096x4096 RGBA8 = 64 MiB; with mips *4/3 ~= 85.3 MiB;
               8 GiB / 85.3 MiB ~= 96 atlases
  section "Refresh rate": 24/60/120/144 Hz -> 41.7 / 16.7 / 8.3 / 6.9 ms

Run:
  python budget.py                       # prints the canonical E6/E7 numbers
  python budget.py --wh 4000 3000 --fps 30 --seconds 10
  python budget.py --set data/           # per-image + set totals from headers
"""
from __future__ import annotations

import argparse
import glob
import os

MB = 10 ** 6
MiB = 2 ** 20
GB = 10 ** 9
GiB = 2 ** 30


def bytes_per_frame(w: int, h: int, bpp: int) -> int:
    """bpp = bits per pixel = channels * bit_depth (RGB888=24, RGBA8=32)."""
    return w * h * bpp // 8


def mip_chain_bytes(base_bytes: int) -> float:
    return base_bytes * 4 / 3


def frame_ms(hz: float) -> float:
    return 1000.0 / hz


def _fmt(nbytes: float) -> str:
    return (f"{nbytes:,.0f} B  =  {nbytes / MB:.3f} MB  =  {nbytes / MiB:.3f} MiB"
            f"  =  {nbytes / GiB:.4f} GiB")


def canonical() -> None:
    print("== Example E6: one 1920x1080 RGB888 frame, then 10 s @ 30 fps ==")
    bpf = bytes_per_frame(1920, 1080, 24)
    print(f"  pixels            : {1920 * 1080:,}")
    print(f"  bytes / frame     : {_fmt(bpf)}")          # 6_220_800
    clip = bpf * 30 * 10
    print(f"  10 s @ 30 fps     : {_fmt(clip)}")          # 1_866_240_000
    bw = bpf * 30
    print(f"  bandwidth         : {bw / MiB:.1f} MiB/s  =  {bw * 8 / GB:.2f} Gbit/s")
    print(f"  (H.264 ~8 Mbit/s -> ~{bw * 8 / 8e6:.0f}x smaller than uncompressed)")

    print("\n== Example E7: 4096x4096 RGBA8 texture atlas ==")
    base = bytes_per_frame(4096, 4096, 32)
    print(f"  no mips           : {base / MiB:.1f} MiB")           # 64
    print(f"  full mip chain    : {mip_chain_bytes(base) / MiB:.1f} MiB")  # 85.3
    fit = 8 * GiB / mip_chain_bytes(base)
    print(f"  fit in 8 GiB VRAM : ~{fit:.0f} atlases (before geometry/buffers/targets)")
    print(f"  200 atlases       : {200 * mip_chain_bytes(base) / GiB:.1f} GiB "
          f"(> 2x an 8 GiB card -> compression + streaming)")

    print("\n== Refresh rate -> per-frame time budget ==")
    for hz in (24, 60, 120, 144):
        print(f"  {hz:3d} Hz : {frame_ms(hz):5.1f} ms/frame")


def custom(w: int, h: int, bpp: int, fps: int, seconds: int) -> None:
    bpf = bytes_per_frame(w, h, bpp)
    print(f"{w}x{h}, {bpp} bpp:")
    print(f"  bytes / frame : {_fmt(bpf)}")
    if seconds:
        print(f"  {seconds} s @ {fps} fps : {_fmt(bpf * fps * seconds)}")
        bw = bpf * fps
        print(f"  bandwidth     : {bw / MB:.1f} MB/s  =  {bw * 8 / MB:.1f} Mbit/s")


def from_set(folder: str) -> None:
    from ppm_io import read_header
    files = sorted(glob.glob(os.path.join(folder, "*.ppm")) +
                   glob.glob(os.path.join(folder, "*.pgm")))
    total_dec = 0
    total_disk = 0
    print(f"{'file':22s} {'WxH':>12s} {'decoded B':>12s} {'on-disk B':>12s} {'ratio':>7s}")
    for f in files:
        w, h, ch = read_header(f)
        dec = w * h * ch
        disk = os.path.getsize(f)
        total_dec += dec
        total_disk += disk
        print(f"{os.path.basename(f):22s} {f'{w}x{h}':>12s} {dec:>12,} {disk:>12,} "
              f"{dec / disk:>6.2f}x")
    print(f"{'-' * 68}")
    print(f"{'SET TOTAL':22s} {'':>12s} {total_dec:>12,} {total_disk:>12,} "
          f"{total_dec / max(total_disk, 1):>6.2f}x")
    print(f"decoded working set: {total_dec / MiB:.2f} MiB   "
          f"(at 4000x3000 RGB each: {len(files) * 4000 * 3000 * 3 / MiB:.0f} MiB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wh", nargs=2, type=int, metavar=("W", "H"))
    ap.add_argument("--bpp", type=int, default=24)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--seconds", type=int, default=10)
    ap.add_argument("--set")
    args = ap.parse_args()
    if args.set:
        from_set(args.set)
    elif args.wh:
        custom(args.wh[0], args.wh[1], args.bpp, args.fps, args.seconds)
    else:
        canonical()


if __name__ == "__main__":
    main()
