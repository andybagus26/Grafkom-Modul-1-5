/* Module 2 -- the library-side render: the Pusaka3D floor plan with Three.js.
 *
 * Draws the SAME plan JSON that raster.mjs draws headless, at the SAME pixel
 * size, so `node compare.mjs out/plan_scratch.ppm out/plan_three.ppm` shows
 * where the library and the from-scratch rasteriser differ.
 *
 * The pipeline stages you still own even with a library: vertex winding,
 * canvas SIZE and pixelRatio, the colour space of every colour, and WHERE a
 * vertex lands relative to the pixel-centre grid.
 *
 * URL parameters (all optional):
 *   ?plan=../pusaka_plan.json   which plan to draw (same schema)
 *   ?offset=0.5                 shift LINE vertices by +1/2 px (default 0.5)
 *   ?fill=0                     outline only (default: silhouette filled)
 *   ?aa=0                       turn MSAA off (default on)
 *   ?halo=0                     no dark halo under the lines (the capture tool
 *                               uses this so the pixel diff compares like with
 *                               like; raster.mjs draws no halo)
 *   ?dump=1                     after rendering, write the framebuffer as a
 *                               base64 PPM into <pre id="dump"> so a headless
 *                               browser (tools/capture_three.mjs) can diff it
 *
 * Why offset = 0.5 for LINES but 0 for the FILL: in raster.mjs an integer
 * line endpoint (x,y) means "light pixel (x,y)", whose sample centre is
 * (x+.5,y+.5). A filled polygon edge at integer x is a pixel CORNER. WebGL
 * samples at pixel centres too, so a GL line whose vertices sit on integer
 * coordinates runs exactly between two pixel rows -- the half-pixel trap of
 * Direct3D 9 in one line. Lines get +1/2; fills keep their corners.
 */
import * as THREE from "three";

const q = new URLSearchParams(location.search);
const PLAN_URL = q.get("plan") || "../pusaka_plan.json";
const LINE_OFFSET = q.has("offset") ? +q.get("offset") : 0.5;
const AA = q.get("aa") !== "0";
const DUMP = q.get("dump") === "1";
const HALO = q.get("halo") !== "0" && !DUMP;

const W = 800, H = 600;
const canvas = document.getElementById("c");

// --- match raster.mjs exactly: no retina scaling, explicit size ---
const renderer = new THREE.WebGLRenderer({ canvas, antialias: AA, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.setClearColor(0x121216, 1);

// an orthographic camera in PIXEL space, y-down to match the framebuffer
const camera = new THREE.OrthographicCamera(0, W, 0, H, -10, 10);
const scene = new THREE.Scene();

// viridis 5-step ramp -- identical to plan.mjs CATEGORY_RGB
const CATEGORY = {
  wall:   0x440154,
  cella:  0x3b528b,
  stair:  0x21918c,
  shrine: 0x5ec962,
  axis:   0xfde725,
};
const LABEL = { wall: "dinding / wall", cella: "cella (ruang utama)", stair: "tangga / stair",
  shrine: "candi perwara / shrine", axis: "sumbu / axis" };
const MARKER = { wall: "■", cella: "◆", stair: "▲", shrine: "●", axis: "✚" };

let plan, world2screen, group;

function makeWorldToScreen(p) {
  const s = p.scale_px_per_m, [ox, oy] = p.origin_m;
  return ([xm, ym]) => [Math.round((xm + ox) * s), Math.round(H - 1 - (ym + oy) * s)];
}

function build(fillSilhouette) {
  if (group) scene.remove(group);
  group = new THREE.Group();

  if (fillSilhouette && plan.silhouette) {
    const shape = new THREE.Shape();
    plan.silhouette.points.map(world2screen).forEach(([x, y], i) => {
      i === 0 ? shape.moveTo(x, y) : shape.lineTo(x, y);
    });
    const geo = new THREE.ShapeGeometry(shape);
    const mat = new THREE.MeshBasicMaterial({ color: 0xe6ecf5, side: THREE.DoubleSide });
    group.add(new THREE.Mesh(geo, mat));
  }

  // Contrast: a luminance-ramp palette cannot contrast with ONE background at
  // both ends (yellow on the light fill is ~1.06:1, purple on the dark page
  // ~1.2:1; WCAG 1.4.11 wants 3:1 for graphics). So, for DISPLAY only, every
  // line gets a 1-px dark halo drawn underneath (4 offset copies).
  if (HALO)
    for (const pl of plan.polylines)
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const pts = pl.points.map(world2screen)
          .map(([x, y]) => new THREE.Vector3(x + LINE_OFFSET + dx, y + LINE_OFFSET + dy, 0.5));
        if (pl.closed) pts.push(pts[0].clone());
        group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
          new THREE.LineBasicMaterial({ color: 0x15151c })));
      }

  for (const pl of plan.polylines) {
    const pts = pl.points.map(world2screen)
      .map(([x, y]) => new THREE.Vector3(x + LINE_OFFSET, y + LINE_OFFSET, 1));
    if (pl.closed) pts.push(pts[0].clone());
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const mat = new THREE.LineBasicMaterial({ color: CATEGORY[pl.category] ?? 0xffffff });
    group.add(new THREE.Line(geo, mat));
  }
  scene.add(group);
  renderer.render(scene, camera);
  placeMarkers();
}

// marker glyphs ON the plan (HTML overlay -- not part of the framebuffer, so
// the pixel diff is unaffected): a second, non-colour channel per category
function placeMarkers() {
  const layer = document.getElementById("markers");
  layer.innerHTML = "";
  const seen = new Set();
  for (const pl of plan.polylines) {
    const pts = pl.points.map(world2screen);
    const cx = pts.reduce((a, p) => a + p[0], 0) / pts.length;
    const cy = pts.reduce((a, p) => a + p[1], 0) / pts.length;
    const id = `${pl.category}:${Math.round(cx / 40)}:${Math.round(cy / 40)}`;
    if (seen.has(id)) continue;
    seen.add(id);
    const m = document.createElement("span");
    m.className = "mk";
    m.textContent = MARKER[pl.category] || "?";
    m.title = `${pl.id} (${LABEL[pl.category] || pl.category})`;
    m.style.left = `${(cx / W) * 100}%`;
    m.style.top = `${(cy / H) * 100}%`;
    m.style.color = "#" + (CATEGORY[pl.category] ?? 0xffffff).toString(16).padStart(6, "0");
    layer.appendChild(m);
  }
}

function buildLegend() {
  const rows = document.getElementById("rows");
  rows.innerHTML = "";
  for (const [cat, hex] of Object.entries(CATEGORY)) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML =
      `<span class="swatch" style="background:#${hex.toString(16).padStart(6, "0")}"></span>` +
      `<span class="marker">${MARKER[cat]}</span><span>${LABEL[cat]}</span>`;
    rows.appendChild(row);
  }
}

function framebufferPPM() {
  renderer.render(scene, camera);
  const gl = renderer.getContext();
  const px = new Uint8Array(W * H * 4);
  gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, px);
  // gl.readPixels is bottom-up; flip to top-down and drop alpha
  const body = new Uint8Array(W * H * 3);
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const src = ((H - 1 - y) * W + x) * 4, dst = (y * W + x) * 3;
      body[dst] = px[src]; body[dst + 1] = px[src + 1]; body[dst + 2] = px[src + 2];
    }
  const header = new TextEncoder().encode(`P6\n${W} ${H}\n255\n`);
  const all = new Uint8Array(header.length + body.length);
  all.set(header); all.set(body, header.length);
  return all;
}

function exportPPM() {
  const blob = new Blob([framebufferPPM()], { type: "application/octet-stream" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "plan_three.ppm";
  a.click();
}

function dumpPPM() {
  const bytes = framebufferPPM();
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  const pre = document.createElement("pre");
  pre.id = "dump";
  pre.dataset.three = THREE.REVISION;
  pre.dataset.renderer = (() => {
    const gl = renderer.getContext();
    const ext = gl.getExtension("WEBGL_debug_renderer_info");
    return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
  })();
  pre.textContent = btoa(bin);
  document.body.appendChild(pre);
}

function applyFilters() {
  const wrap = document.getElementById("wrap");
  wrap.classList.toggle("cvd-deuteranopia", document.getElementById("cvd").checked);
  wrap.classList.toggle("cvd-protanopia", document.getElementById("cvd2").checked);
  wrap.classList.toggle("cvd-grayscale", document.getElementById("gray").checked);
}

fetch(PLAN_URL)
  .then((r) => r.json())
  .then((p) => {
    plan = p;
    world2screen = makeWorldToScreen(plan);
    document.getElementById("planname").textContent = plan.name;
    buildLegend();
    const fillBox = document.getElementById("fill");
    if (q.get("fill") === "0") fillBox.checked = false;
    build(fillBox.checked);
    fillBox.addEventListener("change", (e) => build(e.target.checked));
    for (const id of ["cvd", "cvd2", "gray"]) {
      const box = document.getElementById(id);
      if (q.get(id) === "1") box.checked = true;
      box.addEventListener("change", applyFilters);
    }
    applyFilters();
    document.getElementById("export").addEventListener("click", exportPPM);
    if (DUMP) dumpPPM();
  })
  .catch((err) => {
    document.getElementById("view").insertAdjacentHTML(
      "beforeend",
      `<p style="color:#f66">Could not load ${PLAN_URL}: ${err}. Serve the repo root, e.g. <code>npx serve .</code>, and open <code>/web/</code>.</p>`
    );
  });
