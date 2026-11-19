/* Module 2 -- image metrics, from scratch (mirrors Module 1's metrics.py).
 *   psnr(a,b)  peak signal-to-noise ratio in dB (8-bit peak 255)
 *   ssim(a,b)  SIMPLE GLOBAL structural similarity (one window = whole image)
 * Both take Framebuffer instances (or {w,h,data}). */

export function psnr(a, b, peak = 255) {
  if (a.w !== b.w || a.h !== b.h) throw new Error(`psnr: size ${a.w}x${a.h} vs ${b.w}x${b.h}`);
  let se = 0;
  for (let i = 0; i < a.data.length; i++) {
    const d = a.data[i] - b.data[i];
    se += d * d;
  }
  const mse = se / a.data.length;
  return mse === 0 ? Infinity : 10 * Math.log10((peak * peak) / mse);
}

export function ssim(a, b, L = 255) {
  if (a.w !== b.w || a.h !== b.h) throw new Error(`ssim: size mismatch`);
  const n = a.data.length;
  let ma = 0, mb = 0;
  for (let i = 0; i < n; i++) { ma += a.data[i]; mb += b.data[i]; }
  ma /= n; mb /= n;
  let va = 0, vb = 0, cov = 0;
  for (let i = 0; i < n; i++) {
    const da = a.data[i] - ma, db = b.data[i] - mb;
    va += da * da; vb += db * db; cov += da * db;
  }
  va /= n; vb /= n; cov /= n;
  const c1 = (0.01 * L) ** 2, c2 = (0.03 * L) ** 2;
  return ((2 * ma * mb + c1) * (2 * cov + c2)) /
         ((ma * ma + mb * mb + c1) * (va + vb + c2));
}

/** count of exactly-equal pixels and max absolute channel difference */
export function pixelStats(a, b) {
  let identical = 0, maxAbs = 0;
  const px = a.w * a.h;
  for (let p = 0; p < px; p++) {
    const i = p * 3;
    const d0 = Math.abs(a.data[i] - b.data[i]);
    const d1 = Math.abs(a.data[i + 1] - b.data[i + 1]);
    const d2 = Math.abs(a.data[i + 2] - b.data[i + 2]);
    const m = Math.max(d0, d1, d2);
    if (m === 0) identical++;
    if (m > maxAbs) maxAbs = m;
  }
  return { identical, total: px, maxAbs };
}
