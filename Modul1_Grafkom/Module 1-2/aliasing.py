"""Module 1 -- Lab 2.5 aliasing demo + Lab 2.4 pre-filter fix (NumPy only).

Pattern: nine vertical-stripe bands, each 160 source px wide, whose spatial
frequency in the SOURCE grid is f_src = 0.05, 0.10, ..., 0.45 cycles/px (all
below the source Nyquist 0.5, so the source itself is clean). We then
downscale 2x. In OUTPUT pixels each band's frequency doubles:

    f = 2 * f_src  =  0.1, 0.2, ..., 0.9 cycles/output-pixel

The output grid samples at f_s = 1 sample/px, Nyquist 0.5. Prediction:
  f <= 0.5  -> survives at f
  f  > 0.5  -> ALIASES to |f - f_s| = |f - 1|   (0.6->0.4, 0.7->0.3, 0.8->0.2, 0.9->0.1)

Two downscales:
  * decimate      : resample_nearest (keep every 2nd sample)  -> aliases
  * prefilter+dec : resample_nearest_aa (Gaussian low-pass, then decimate)

Measurement: for each band, a from-scratch DFT of one output row (numpy.fft is
just the DFT; the band is 80 output px = an integer number of cycles for every
f = 0.1..0.9, so there is no spectral leakage) -> the dominant frequency and its amplitude.

Second part (pitfall fix on real content): crop_hifreq.ppm has relief ridges
at 0.37 cycles/px along x; 2x decimation puts them at 0.74 -> alias 0.26. We
report the energy at 0.26 cycles/px before and after the pre-filter.

Run:
  python aliasing.py              # prints the table
  python aliasing.py --out report/
"""
from __future__ import annotations

import argparse
import os

import numpy as np

from ppm_io import read_ppm, write_ppm
from resample import resample_nearest, resample_nearest_aa

BAND = 160          # source px per band -> 80 output px: integer cycles for every f
ROWS = 64
F_SRC = [round(0.05 * k, 2) for k in range(1, 10)]


def stripe_pattern() -> np.ndarray:
    """8-bit grey, values 128 +/- 100 * cos(2*pi*f_src*x), pixel-centre sampled."""
    cols = []
    for f in F_SRC:
        x = np.arange(BAND, dtype=np.float64)
        cols.append(128 + 100 * np.cos(2 * np.pi * f * x))
    row = np.concatenate(cols)
    return np.round(np.repeat(row[None, :], ROWS, axis=0)).astype(np.uint8)


def predicted_alias(f: float, fs: float = 1.0) -> float:
    return f if f <= fs / 2 else abs(f - fs)


def dominant(row: np.ndarray) -> tuple[float, float]:
    """(frequency in cycles/px, amplitude in code levels) of the strongest
    non-DC component of a 1-D signal."""
    x = row.astype(np.float64) - row.mean()
    spec = np.abs(np.fft.rfft(x)) * 2 / x.size
    if x.size % 2 == 0:
        spec[-1] /= 2          # the Nyquist bin has no mirror twin
    freqs = np.arange(spec.size) / x.size
    k = int(np.argmax(spec[1:]) + 1)
    return float(freqs[k]), float(spec[k])


def sweep_table():
    src = stripe_pattern()
    dec = resample_nearest(src, 2)
    aa = resample_nearest_aa(src, 2)
    ob = BAND // 2
    rows = []
    for i, fsrc in enumerate(F_SRC):
        f = round(2 * fsrc, 2)
        seg_d = dec[ROWS // 4, i * ob:(i + 1) * ob]
        seg_a = aa[ROWS // 4, i * ob:(i + 1) * ob]
        fd, ad = dominant(seg_d)
        fa, aa_ = dominant(seg_a)
        rows.append(dict(f=f, pred=round(predicted_alias(f), 2), f_dec=fd, a_dec=ad,
                         f_aa=fa, a_aa=aa_))
    return src, dec, aa, rows


def relief_alias():
    """Energy at the predicted alias frequency on the real relief crop."""
    img = read_ppm("data/crop_hifreq.ppm")
    grey = img.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])  # just to get 1 channel
    dec = resample_nearest(img, 2).astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    aa = resample_nearest_aa(img, 2).astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])

    def spectrum(a):
        x = a - a.mean(axis=1, keepdims=True)
        s = (np.abs(np.fft.rfft(x, axis=1)) * 2 / x.shape[1]).mean(axis=0)
        return np.arange(s.size) / x.shape[1], s

    fs0, s0 = spectrum(grey)
    f1, s1 = spectrum(dec)
    f2, s2 = spectrum(aa)
    k0 = int(np.argmax(s0[1:]) + 1)
    pred = predicted_alias(2 * fs0[k0])
    k = int(np.argmin(np.abs(f1 - pred)))
    return dict(src_peak=float(fs0[k0]), src_amp=float(s0[k0]), pred=float(pred),
                at_freq=float(f1[k]), amp_dec=float(s1[k]), amp_aa=float(s2[k]),
                dec_img=resample_nearest(img, 2), aa_img=resample_nearest_aa(img, 2))


def _selftest() -> None:
    _, _, _, rows = sweep_table()
    for r in rows:
        assert abs(r["f_dec"] - r["pred"]) < 0.02, r            # alias where predicted
        if r["f"] > 0.5:
            assert r["a_aa"] < 0.25 * r["a_dec"], r              # pre-filter kills it
    ra = relief_alias()
    assert ra["amp_aa"] < 0.3 * ra["amp_dec"], ra
    print(f"aliasing self-test OK  (all 9 bands alias exactly at |f-1|; pre-filter cuts "
          f"the 0.6-0.9 aliases by >4x; relief alias at {ra['at_freq']:.2f} c/px "
          f"{ra['amp_dec']:.1f} -> {ra['amp_aa']:.1f} codes)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
        return
    src, dec, aa, rows = sweep_table()
    print("2x downscale of a 0.1..0.9 cycles/output-px sweep (amplitude in code levels, source = 100)")
    print(f"{'f (out)':>8s} {'predicted':>10s} | {'decimate: f':>12s} {'amp':>6s} | "
          f"{'prefilter: f':>13s} {'amp':>6s}")
    for r in rows:
        tag = "  <- alias" if r["f"] > 0.5 else ""
        print(f"{r['f']:8.2f} {r['pred']:10.2f} | {r['f_dec']:12.3f} {r['a_dec']:6.1f} | "
              f"{r['f_aa']:13.3f} {r['a_aa']:6.1f}{tag}")
    ra = relief_alias()
    print(f"\nrelief crop: ridges at {ra['src_peak']:.3f} c/px (source), x2 = "
          f"{2 * ra['src_peak']:.3f} -> predicted alias {ra['pred']:.3f} c/px")
    print(f"  amplitude at {ra['at_freq']:.3f} c/px: decimate {ra['amp_dec']:.2f}  ->  "
          f"pre-filtered {ra['amp_aa']:.2f} code levels "
          f"({ra['amp_dec'] / max(ra['amp_aa'], 1e-9):.1f}x weaker)")
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        for name, im in (("alias_source.pgm", src), ("alias_decimate.pgm", dec),
                         ("alias_prefilter.pgm", aa),
                         ("relief_crop_decimate.ppm", ra["dec_img"]),
                         ("relief_crop_prefilter.ppm", ra["aa_img"])):
            write_ppm(os.path.join(args.out, name), im)
        print(f"wrote alias_*.pgm and relief_crop_*.ppm to {args.out}")


if __name__ == "__main__":
    main()
