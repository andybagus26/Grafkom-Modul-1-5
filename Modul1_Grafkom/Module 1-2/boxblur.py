"""Module 1 -- box blur from scratch (NumPy only).

Job: average each pixel with its neighbours. Two variants:
  box_blur_2x2_downscale : non-overlapping 2x2 average -> half size (E1)
  box_blur_3x3           : overlapping 3x3 average, same size (edge-replicated)

Reproduces: Example E1 -- on the running patch, the 2x2 result is
  [[  6, 22, 38, 54],
   [ 22, 38, 54, 70],
   [ 38, 54, 70, 86],
   [ 54, 70, 86,102]]   and the patch mean is 54.

NOTE: these blur on the values AS GIVEN. For colour images you almost always
want to decode to linear first -- see resample.py.

Run:  python boxblur.py --selftest
"""
from __future__ import annotations

import sys
import numpy as np

from ppm_io import read_ppm


def box_blur_2x2_downscale(img: np.ndarray) -> np.ndarray:
    """Non-overlapping 2x2 mean. H and W must be even. Promotes to float so
    uint8 addition cannot wrap (a real pitfall)."""
    f = img.astype(np.float64)
    h, w = f.shape[:2]
    if h % 2 or w % 2:
        raise ValueError(f"need even dimensions, got {h}x{w}")
    if f.ndim == 2:
        f = f.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))
    else:
        f = f.reshape(h // 2, 2, w // 2, 2, f.shape[2]).mean(axis=(1, 3))
    return np.round(f).astype(np.uint8)


def box_blur_2x2_downscale_uint8_buggy(img: np.ndarray) -> np.ndarray:
    """PITFALL DEMO ONLY: sums the four samples while still in uint8, so any
    block whose sum exceeds 255 wraps modulo 256. Kept so the test can show
    the wrap that the float64 promotion above prevents."""
    a = img[0::2, 0::2]; b = img[0::2, 1::2]; c = img[1::2, 0::2]; d = img[1::2, 1::2]
    with np.errstate(over="ignore"):
        s = (a + b + c + d)                      # uint8 + uint8 -> uint8 (wraps!)
    return (s // 4).astype(np.uint8)


def assert_no_wrap(result_u8: np.ndarray, img: np.ndarray) -> None:
    """Overflow guard: a box average can never leave [min(img), max(img)].
    A wrapped sum lands far below the block minimum, so this catches it."""
    lo, hi = int(img.min()), int(img.max())
    if result_u8.min() < lo or result_u8.max() > hi:
        raise OverflowError(f"box result [{result_u8.min()},{result_u8.max()}] "
                            f"outside input range [{lo},{hi}] -- uint8 wraparound?")


def box_blur_3x3(img: np.ndarray) -> np.ndarray:
    """Overlapping 3x3 mean, same output size, edges replicated."""
    f = img.astype(np.float64)
    pad = ((1, 1), (1, 1)) + (((0, 0),) if f.ndim == 3 else ())
    g = np.pad(f, pad, mode="edge")
    acc = np.zeros_like(f)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            acc += g[dy:dy + f.shape[0], dx:dx + f.shape[1]]
    return np.round(acc / 9.0).astype(np.uint8)


def _selftest() -> None:
    from make_data import running_patch
    P = running_patch()
    assert int(round(P.mean())) == 54, f"patch mean {P.mean()} != 54"

    expected = np.array([[6, 22, 38, 54],
                         [22, 38, 54, 70],
                         [38, 54, 70, 86],
                         [54, 70, 86, 102]], dtype=np.uint8)
    got = box_blur_2x2_downscale(P)
    assert np.array_equal(got, expected), f"2x2 blur\n{got}\n!=\n{expected}"

    # 3x3 blur of a constant image is that constant
    c = np.full((6, 6), 77, dtype=np.uint8)
    assert np.array_equal(box_blur_3x3(c), c), "3x3 blur changed a constant"
    # 3x3 blur vs a hand-computed neighbour mean at an interior pixel of P
    r, c = 3, 4
    hand = int(np.floor(P[r - 1:r + 2, c - 1:c + 2].astype(np.float64).mean() + 0.5))
    assert int(box_blur_3x3(P)[r, c]) == hand, "3x3 blur != hand neighbour mean"

    # overflow pitfall: bright block wraps in uint8, not in the float path
    bright = np.array([[200, 250], [250, 250]], dtype=np.uint8)
    wrapped = int(box_blur_2x2_downscale_uint8_buggy(bright)[0, 0])
    correct = int(box_blur_2x2_downscale(bright)[0, 0])
    assert correct == 238 and wrapped != 238, (correct, wrapped)
    try:
        assert_no_wrap(box_blur_2x2_downscale_uint8_buggy(bright), bright)
        raise AssertionError("overflow guard did not fire")
    except OverflowError:
        pass
    print(f"boxblur self-test OK  (mean=54; 2x2 result matches Example E1; "
          f"3x3 at P[{r},{c}] = {hand} = hand mean; uint8 sum wraps to {wrapped}, "
          f"float path gives {correct}, guard fires)")


if __name__ == "__main__":
    if "--selftest" in sys.argv or len(sys.argv) == 1:
        _selftest()
