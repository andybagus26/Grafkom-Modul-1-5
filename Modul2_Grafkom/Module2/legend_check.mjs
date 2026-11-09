/* Module 2 -- is the 5-category legend still distinguishable under CVD?
 * Same Brettel/Vienot-style matrices as Module 1 cvd.py and as the SVG
 * <feColorMatrix> filters in web/index.html. SVG filters default to
 * color-interpolation-filters="linearRGB", i.e. they apply the matrix to
 * LINEAR light -- exactly what we do here: decode, matrix, encode.
 *   node legend_check.mjs                                                */
import { srgbToLinear, linearToSrgb } from "./raster.mjs";
import { CATEGORY_RGB } from "./plan.mjs";

export const MATS = {
  deuteranopia: [[0.625, 0.375, 0], [0.7, 0.3, 0], [0, 0.3, 0.7]],
  protanopia: [[0.567, 0.433, 0], [0.558, 0.442, 0], [0, 0.242, 0.758]],
};

export function simulate(rgb, kind) {
  const l = rgb.map((c) => srgbToLinear(c / 255));
  if (kind === "grayscale") {
    const y = 0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2];
    return [0, 1, 2].map(() => Math.round(linearToSrgb(y) * 255));
  }
  const m = MATS[kind];
  return m.map((row) => Math.round(linearToSrgb(row[0] * l[0] + row[1] * l[1] + row[2] * l[2]) * 255));
}

export function legendCheck(colors = CATEGORY_RGB) {
  const names = Object.keys(colors);
  return ["normal", "deuteranopia", "protanopia", "grayscale"].map((kind) => {
    const sim = names.map((n) => (kind === "normal" ? colors[n] : simulate(colors[n], kind)));
    let min = Infinity, pair = "";
    for (let i = 0; i < sim.length; i++)
      for (let j = i + 1; j < sim.length; j++) {
        const d = Math.hypot(...sim[i].map((v, k) => v - sim[j][k]));
        if (d < min) { min = d; pair = `${names[i]}/${names[j]}`; }
      }
    return { kind, min: +min.toFixed(1), pair, sim };
  });
}

if (process.argv[1] && process.argv[1].endsWith("legend_check.mjs")) {
  for (const r of legendCheck())
    console.log(`${r.kind.padEnd(13)} min pair distance ${String(r.min).padStart(6)}  (closest: ${r.pair})  ` +
      r.sim.map((c) => `rgb(${c})`).join(" "));
  const bad = { wall: [200, 40, 40], cella: [40, 170, 40], stair: [210, 150, 30], shrine: [150, 90, 40], axis: [90, 160, 40] };
  console.log("\nfor contrast, a red/green palette:");
  for (const r of legendCheck(bad)) console.log(`${r.kind.padEnd(13)} min pair distance ${String(r.min).padStart(6)}  (closest: ${r.pair})`);
}
