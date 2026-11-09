/* Module 2 -- figures for the pre-study and report, as hand-written SVG.
 * Pixel grids are filled from the REAL rasteriser output (raster.mjs), so a
 * figure cannot disagree with the code.     node figures_m2.mjs -> figures/ */
import { mkdirSync, writeFileSync } from "node:fs";
import { lineBresenham, triangle, edge } from "./raster.mjs";

mkdirSync("figures", { recursive: true });
const F = 'font-family="Helvetica,Arial,sans-serif"';
const svg = (w, h, b) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}"><rect width="${w}" height="${h}" fill="#fff"/>${b}</svg>`;
const t = (x, y, s, o = {}) => `<text x="${x}" y="${y}" font-size="${o.size || 12}" fill="${o.fill || "#222"}" text-anchor="${o.a || "start"}" ${o.bold ? 'font-weight="bold"' : ""} ${F}>${s}</text>`;
// wrap a caption into lines of at most n characters
const cap = (x, y, str, n = 80) => {
  const words = str.split(" "), lines = [""];
  for (const w of words) (lines[lines.length - 1] + " " + w).trim().length > n ? lines.push(w) : (lines[lines.length - 1] = (lines[lines.length - 1] + " " + w).trim());
  return lines.map((l, i) => t(x, y + i * 14, l, { size: 11, fill: "#444" })).join("");
};
const rect = (x, y, w, h, fill, stroke = "none", extra = "") => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" stroke="${stroke}" ${extra}/>`;
const line = (x1, y1, x2, y2, c = "#222", w = 1, extra = "") => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${c}" stroke-width="${w}" ${extra}/>`;
const AR = '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f4e79"/></marker></defs>';

// grid helper: cells (n x m), cell size s, origin (ox,oy); lit = [[x,y,colour]]
function grid(n, m, s, ox, oy, lit = [], centres = true) {
  let b = "";
  for (const [x, y, c] of lit) b += rect(ox + x * s, oy + y * s, s, s, c);
  for (let i = 0; i <= n; i++) b += line(ox + i * s, oy, ox + i * s, oy + m * s, "#bbb");
  for (let j = 0; j <= m; j++) b += line(ox, oy + j * s, ox + n * s, oy + j * s, "#bbb");
  for (let i = 0; i < n; i++) b += t(ox + i * s + s / 2, oy - 4, i, { size: 10, a: "middle", fill: "#777" });
  for (let j = 0; j < m; j++) b += t(ox - 5, oy + j * s + s / 2 + 3, j, { size: 10, a: "end", fill: "#777" });
  if (centres) for (let i = 0; i < n; i++) for (let j = 0; j < m; j++)
    b += `<circle cx="${ox + i * s + s / 2}" cy="${oy + j * s + s / 2}" r="1.6" fill="#999"/>`;
  return b;
}

// 1. pipeline -------------------------------------------------------------
{
  const st = [
    ["1 · Application", "scene: vertex, warna, transform", "kode kita"],
    ["2 · Vertex processing", "vertex → posisi layar (pixel)", "PROGRAMMABLE (vertex shader)"],
    ["3 · Primitive assembly & clipping", "vertex → garis/segitiga, potong di tepi layar", "fixed"],
    ["4 · Rasterisation", "primitif → fragment (pixel yang ditutupi)", "fixed  ← raster.mjs"],
    ["5 · Fragment shading", "fragment → warna", "PROGRAMMABLE (fragment shader)"],
    ["6 · Per-fragment ops", "depth test, blending, stencil", "fixed (dikonfigurasi)"],
    ["7 · Framebuffer", "grid pixel akhir → layar / PNG", "memori"],
  ];
  let b = AR;
  st.forEach(([n, io, k], i) => {
    const y = 14 + i * 58, prog = k.startsWith("PROG"), mine = n.startsWith("4");
    b += rect(20, y, 560, 44, prog ? "#e8f1fb" : mine ? "#fff1e0" : "#f4f4f4", prog ? "#2e75b6" : mine ? "#e07b00" : "#999", 'rx="6"');
    b += t(32, y + 18, n, { bold: true, size: 13 }) + t(32, y + 35, io, { size: 12, fill: "#444" });
    b += t(570, y + 27, k, { size: 11, a: "end", fill: prog ? "#1f4e79" : mine ? "#b35900" : "#666", bold: prog || mine });
    if (i < st.length - 1) b += line(300, y + 44, 300, y + 56, "#1f4e79", 1.6, 'marker-end="url(#a)"');
  });
  writeFileSync("figures/fig_pipeline.svg", svg(600, 420, b));
}

// 2. forward vs backward ----------------------------------------------------
{
  let b = AR + t(20, 22, "Forward (object-order): untuk tiap SEGITIGA → pixel yang ditutupinya", { bold: true });
  b += grid(12, 8, 18, 30, 40, [], false);
  const tri = [[1, 1], [9, 2], [4, 7]].map(([x, y]) => [30 + x * 18, 40 + y * 18]);
  b += `<polygon points="${tri.map((p) => p.join(",")).join(" ")}" fill="#f6c28b" fill-opacity=".6" stroke="#e07b00" stroke-width="2"/>`;
  b += t(270, 110, "loop: segitiga × pixel di dalamnya", { size: 11, fill: "#444" });
  b += t(20, 210, "Backward (image-order): untuk tiap PIXEL → tembak ray, cari hit terdekat", { bold: true });
  b += grid(12, 8, 18, 30, 228, [[6, 3, "#cfe2f3"]], false);
  b += `<circle cx="${30 + 6.5 * 18}" cy="${228 + 3.5 * 18}" r="3" fill="#1f4e79"/>`;
  b += line(30 + 6.5 * 18, 228 + 3.5 * 18, 420, 300, "#1f4e79", 1.5, 'marker-end="url(#a)" stroke-dasharray="5 3"');
  b += `<circle cx="450" cy="300" r="24" fill="#d9ead3" stroke="#38761d"/>` + t(450, 340, "objek", { a: "middle", size: 11 });
  b += t(270, 380, "loop: pixel × objek (biaya intersection)", { size: 11, fill: "#444" });
  writeFileSync("figures/fig_fwd_bwd.svg", svg(520, 395, b));
}

// 3. sample centre (E1) -----------------------------------------------------
{
  const s = 34;
  const centre = [[1, 1], [2, 1], [1, 2], [2, 2]].map(([x, y]) => [x, y, "#9fc5e8"]);
  const corner = [];
  for (let y = 1; y <= 3; y++) for (let x = 1; x <= 3; x++) corner.push([x, y, "#f4b183"]);
  let b = t(20, 20, "(a) aturan pusat: 2×2", { bold: true }) + grid(6, 6, s, 30, 40, centre);
  b += rect(30 + s, 40 + s, 2 * s, 2 * s, "none", "#1f4e79", 'stroke-width="2.5"');
  b += t(280, 20, "(b) uji sudut [1,3] tertutup: 3×3", { bold: true }) + grid(6, 6, s, 290, 40, corner);
  b += rect(290 + s, 40 + s, 2 * s, 2 * s, "none", "#1f4e79", 'stroke-width="2.5"');
  for (let y = 1; y <= 3; y++) for (let x = 1; x <= 3; x++) b += `<circle cx="${290 + x * s}" cy="${40 + y * s}" r="3.5" fill="#c55a11"/>`;
  b += cap(30, 268, "Kotak biru = rectangle x∈[1,3), y∈[1,3); titik abu-abu = pusat sampel (x+½, y+½); titik oranye = sudut pixel yang diuji.", 85);
  writeFileSync("figures/fig_sample_centre.svg", svg(520, 296, b));
}

// 4. line E2/E3 ---------------------------------------------------------------
{
  const s = 40, ox = 30, oy = 30;
  const px = lineBresenham(2, 1, 9, 5).map(([x, y]) => [x, y, "#f9cb9c"]);
  let b = grid(11, 7, s, ox, oy, px);
  b += line(ox + 2.5 * s, oy + 1.5 * s, ox + 9.5 * s, oy + 5.5 * s, "#1f4e79", 2.2);
  const D = [1, -5, 3, -3, 5, -1, 7, 1];
  px.forEach(([x, y], i) => { b += t(ox + x * s + s / 2, oy + y * s + s - 6, `D=${D[i]}`, { size: 10, a: "middle", fill: "#7f3f00" }); });
  b += cap(ox, oy + 7 * s + 22, "(2,1)→(9,5): Δx=7, Δy=4. Pixel oranye = hasil lineBresenham() (sama dengan DDA); garis biru = garis ideal antar pusat pixel; D = variabel keputusan saat pixel di-plot.", 78);
  writeFileSync("figures/fig_line.svg", svg(500, 354, b));
}

// 5. triangle E4 ------------------------------------------------------------
{
  const s = 40, ox = 30, oy = 30, A = [1, 1], B = [6, 2], C = [3, 7];
  const lit = [];
  triangle({ w: 9, h: 9 }, A, B, C, null, { onFragment: (x, y) => lit.push([x, y, "#d9ead3"]) });
  let b = grid(9, 9, s, ox, oy, lit);
  const P = (p) => [ox + p[0] * s, oy + p[1] * s];
  b += `<polygon points="${[A, B, C].map((p) => P(p).join(",")).join(" ")}" fill="none" stroke="#38761d" stroke-width="2.5"/>`;
  for (const [n, p] of [["A(1,1)", A], ["B(6,2)", B], ["C(3,7)", C]]) b += `<circle cx="${P(p)[0]}" cy="${P(p)[1]}" r="4" fill="#38761d"/>` + t(P(p)[0] + 6, P(p)[1] - 6, n, { bold: true, size: 12 });
  for (const [n, p, inside] of [["P1(3,3)", [3, 3], true], ["P2(5,5)", [5, 5], false], ["P3(1,4)", [1, 4], false]]) {
    const v = [edge(...A, ...B, ...p), edge(...B, ...C, ...p), edge(...C, ...A, ...p)];
    b += `<circle cx="${P(p)[0]}" cy="${P(p)[1]}" r="5" fill="${inside ? "#1f4e79" : "#c00000"}"/>` +
      t(P(p)[0] + 7, P(p)[1] + 14, `${n} (${v.join(", ")})`, { size: 11, fill: inside ? "#1f4e79" : "#c00000" });
  }
  b += cap(ox, oy + 9 * s + 22, "Hijau = pixel yang dinyalakan triangle() (14 px). Angka di titik = (E_AB, E_BC, E_CA); total E_AB(C) = 28.", 66);
  writeFileSync("figures/fig_triangle.svg", svg(430, 434, b));
}

// 6. top-left square --------------------------------------------------------
{
  const s = 26, T1 = [[2, 2], [8, 2], [8, 8]], T2 = [[2, 2], [8, 8], [2, 8]];
  const panel = (ox, title, opts) => {
    const cnt = new Map();
    for (const [T, c] of [[T1, "#f6b26b"], [T2, "#9fc5e8"]])
      triangle({ w: 10, h: 10 }, ...T, null, { ...opts, onFragment: (x, y) => cnt.set(`${x},${y}`, [...(cnt.get(`${x},${y}`) || []), c]) });
    const lit = [];
    for (const [k, cs] of cnt) { const [x, y] = k.split(",").map(Number); lit.push([x, y, cs.length > 1 ? "#cc0000" : cs[0]]); }
    for (let i = 2; i < 8; i++) if (!cnt.has(`${i},${i}`)) lit.push([i, i, "#00d0e0"]);
    let b = t(ox, 18, title, { bold: true, size: 12 }) + grid(10, 10, s, ox + 10, 34, lit, false);
    b += line(ox + 10 + 2 * s, 34 + 2 * s, ox + 10 + 8 * s, 34 + 8 * s, "#222", 1.5, 'stroke-dasharray="4 3"');
    return b;
  };
  let b = panel(10, "≥ 0 tanpa aturan: 6 ganda (merah)", { topLeft: false });
  b += panel(300, "> 0 tanpa aturan: 6 celah (cyan)", { topLeft: false, strictGreater: true });
  b += panel(590, "aturan top-left: 0 ganda, 0 celah", { topLeft: true });
  b += t(20, 318, "Oranye = T1 (2,2)(8,2)(8,8); biru = T2 (2,2)(8,8)(2,8). Dengan aturan yang benar, diagonal y = x (edge KIRI T1) dimiliki T1.", { size: 11, fill: "#444" });
  writeFileSync("figures/fig_topleft.svg", svg(880, 330, b));
}

// 7. half-pixel blit -----------------------------------------------------------
{
  const s = 60;
  const panel = (ox, title, sx, sy, note) => {
    let b = t(ox, 18, title, { bold: true, size: 12 });
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) b += rect(ox + 10 + i * s, 30 + j * s, s, s, ((i + j) & 1) ? "#fff" : "#333", "#888");
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) b += `<circle cx="${ox + 10 + i * s + s / 2}" cy="${30 + j * s + s / 2}" r="3" fill="#2e75b6"/>`;
    b += `<circle cx="${ox + 10 + sx * s}" cy="${30 + sy * s}" r="8" fill="#e07b00" stroke="#fff" stroke-width="2"/>`;
    b += t(ox + 10, 30 + 3 * s + 22, note, { size: 11, fill: "#444" });
    return b;
  };
  let b = panel(10, "Sampel di pusat texel (dengan offset −½)", 1.5, 1.5, "1 texel, bobot 1 → salinan eksak");
  b += panel(260, "Sampel di sudut texel (D3D9 tanpa offset)", 2, 2, "4 texel, bobot ¼ → blur (128)");
  b += t(10, 268, "Kotak = texel sumber; titik biru = pusat texel; titik oranye = posisi sampel pixel output.", { size: 11, fill: "#444" });
  writeFileSync("figures/fig_halfpixel.svg", svg(500, 280, b));
}
console.log("wrote figures/fig_{pipeline,fwd_bwd,sample_centre,line,triangle,topleft,halfpixel}.svg");
