/**
 * viewer.js — Lab 3: renderer real-time Three.js (r128) untuk mymodel.obj + texture.png.
 *
 * Semua parameter scene disamakan dengan raster3d.py SCENES["mymodel"], supaya frame yang diekspor bisa
 * dibandingkan langsung dengan out/mymodel_raster.ppm (compare.py):
 *   kamera   PerspectiveCamera(fov 50, aspect 1, near 0.1, far 30), eye (0,1.2,3.8), target (0,0,0)
 *   model    rotasi y 35 derajat
 *   light    ambient 0.25 + directional 0.75 dari arah (0.5, 0.8, 0.6)   -> 0.25 + 0.75 * max(0, n.l)
 *   warna    texture di-decode sRGB -> linear, shading di linear, output di-encode sRGB
 *   latar    hitam (sama dengan raster3d.py)
 *   ukuran   canvas TETAP 512x512, setPixelRatio(1)
 *
 * Mode otomatis (dipakai tools/three_export.py lewat Chrome headless):
 *   ?export=1  setelah aset termuat, render pose default lalu tulis PPM base64 ke <pre id="ppm">
 *              dan hasil benchmark frame time ke <pre id="bench">.
 */
(function () {
  "use strict";
  const SIZE = 512;
  const EYE = [0.0, 1.2, 3.8];
  const TARGET = [0.0, 0.0, 0.0];
  const params = new URLSearchParams(location.search);
  const AUTO = params.get("export") === "1";
  const USE_TEX = params.get("tex") !== "0";     // ?tex=0 : abu-abu polos (eksperimen sumber selisih)
  const USE_AA = params.get("aa") !== "0";       // ?aa=0  : tanpa MSAA
  // ?model=nama.obj : model lain di folder web/ (eksperimen skala). Hanya nama file .obj sederhana.
  const MODEL = /^[\w-]+\.obj$/.test(params.get("model") || "") ? params.get("model") : "mymodel.obj";
  const T_START = performance.now();
  let loadMs = null;

  const stage = document.getElementById("stage");
  const status = document.getElementById("status");
  const frameLabel = document.getElementById("frame");

  function fail(msg) {
    status.textContent = msg;
    status.classList.add("error");
    status.style.display = "flex";
    document.getElementById("ppm").textContent = "ERROR: " + msg;
    if (AUTO && params.get("post") === "1") {
      fetch("/__result", { method: "POST", body: JSON.stringify({ error: msg }) });
    }
  }

  if (typeof THREE === "undefined" || !THREE.OBJLoader || !THREE.OrbitControls) {
    fail("Three.js gagal dimuat dari CDN. Periksa koneksi internet.");
    return;
  }

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x000000);

  const camera = new THREE.PerspectiveCamera(50, 1.0, 0.1, 30.0);
  camera.position.set(...EYE);

  const renderer = new THREE.WebGLRenderer({ antialias: USE_AA, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(SIZE, SIZE, false);          // ukuran buffer tetap; CSS hanya menskalakan tampilan
  renderer.outputEncoding = THREE.sRGBEncoding;  // colour management: encode sRGB di akhir
  stage.appendChild(renderer.domElement);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.target.set(...TARGET);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.update();

  scene.add(new THREE.AmbientLight(0xffffff, 0.25));
  const sun = new THREE.DirectionalLight(0xffffff, 0.75);
  sun.position.set(0.5, 0.8, 0.6);               // directional: hanya arah (posisi - target) yang dipakai
  scene.add(sun);

  let model = null;
  let texture = null;

  function resetCamera() {
    camera.position.set(...EYE);
    controls.target.set(...TARGET);
    controls.update();
  }

  function renderOnce() {
    renderer.render(scene, camera);
  }

  /** Baca framebuffer 512x512 dan susun PPM P6 (baris WebGL dimulai dari bawah, jadi dibalik). */
  function framePPM() {
    resetCamera();
    renderOnce();
    const gl = renderer.getContext();
    const rgba = new Uint8Array(SIZE * SIZE * 4);
    gl.readPixels(0, 0, SIZE, SIZE, gl.RGBA, gl.UNSIGNED_BYTE, rgba);
    const header = new TextEncoder().encode(`P6\n${SIZE} ${SIZE}\n255\n`);
    const out = new Uint8Array(header.length + SIZE * SIZE * 3);
    out.set(header, 0);
    let k = header.length;
    for (let y = SIZE - 1; y >= 0; y--) {
      for (let x = 0; x < SIZE; x++) {
        const i = (y * SIZE + x) * 4;
        out[k++] = rgba[i]; out[k++] = rgba[i + 1]; out[k++] = rgba[i + 2];
      }
    }
    return out;
  }

  function downloadPPM() {
    const blob = new Blob([framePPM()], { type: "image/x-portable-pixmap" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "mymodel_three.ppm";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  /** Frame time: N render berturut-turut, tiap render dipaksa selesai dengan readPixels 1 piksel. */
  function benchmark(n) {
    const gl = renderer.getContext();
    const px = new Uint8Array(4);
    const times = [];
    for (let i = 0; i < n + 10; i++) {
      model.rotation.y += 0.002;                       // sedikit gerak supaya tiap frame benar-benar dirender
      const t0 = performance.now();
      renderOnce();
      gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
      if (i >= 10) times.push(performance.now() - t0);  // 10 frame pertama = pemanasan
    }
    model.rotation.y = THREE.MathUtils.degToRad(35);
    times.sort((a, b) => a - b);
    const dbg = gl.getExtension("WEBGL_debug_renderer_info");
    return {
      frames: n,
      median_ms: times[Math.floor(n / 2)],
      p95_ms: times[Math.floor(n * 0.95)],
      gpu: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
      triangles: renderer.info.render.triangles,
      model: MODEL,
      load_ms: loadMs,
      three: THREE.REVISION,
      userAgent: navigator.userAgent,
    };
  }

  function toBase64(bytes) {
    let s = "";
    for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(s);
  }

  function onReady() {
    loadMs = performance.now() - T_START;           // unduh + parse OBJ + texture sampai siap render
    status.style.display = "none";
    if (AUTO) {
      const bench = benchmark(300);
      const ppm = toBase64(framePPM());
      document.getElementById("bench").textContent = JSON.stringify(bench);
      document.getElementById("ppm").textContent = ppm;
      if (params.get("post") === "1") {          // kirim balik ke tools/three_export.py
        fetch("/__result", { method: "POST", body: JSON.stringify({ bench, ppm }) });
      }
      return;
    }
    let last = performance.now(), frames = 0;
    (function loop() {
      requestAnimationFrame(loop);
      controls.update();
      renderOnce();
      frames++;
      const now = performance.now();
      if (now - last >= 1000) {
        frameLabel.textContent = `${Math.round(frames * 1000 / (now - last))} FPS · ${((now - last) / frames).toFixed(2)} ms/frame`;
        frames = 0; last = now;
      }
    })();
  }

  let pending = 2;
  const done = () => { if (--pending === 0) onReady(); };

  new THREE.TextureLoader().load("texture.png", (tex) => {
    tex.encoding = THREE.sRGBEncoding;     // texel di-decode sRGB -> linear sebelum shading
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    // flipY = true (default): PNG baris atas = v 1, sesuai origin UV OBJ di kiri-bawah
    texture = tex;
    if (model) applyMaterial();
    done();
  }, undefined, () => fail("texture.png tidak ditemukan. Jalankan: python3 make_model.py"));

  function applyMaterial() {
    model.traverse((c) => {
      // MeshLambertMaterial, FrontSide: winding CCW mymodel.obj harus benar (Lab 1) atau dinding hilang.
      if (c.isMesh) {
        c.material = USE_TEX ? new THREE.MeshLambertMaterial({ map: texture })
                             : new THREE.MeshLambertMaterial({ color: new THREE.Color(0.7, 0.7, 0.7) }); // linear 0.7 = raster3d
      }
    });
  }

  new THREE.OBJLoader().load(MODEL, (obj) => {
    model = obj;
    model.rotation.y = THREE.MathUtils.degToRad(35);
    if (texture) applyMaterial();
    scene.add(model);
    done();
  }, undefined, () => fail(MODEL + " tidak ditemukan di web/. Jalankan: python3 make_model.py"));

  document.getElementById("btn-reset").addEventListener("click", resetCamera);
  document.getElementById("btn-ppm").addEventListener("click", () => model && downloadPPM());
})();
