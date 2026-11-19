// Pusaka3D AR Explainer -- Module 5 (extended by Andy Bagus, 20241337033).
// Loads a model's hotspot JSON, injects <model-viewer> hotspot slots, and
// drives the info panel, language toggle, a quiz mode, and a model switcher
// (my Gapura Wringin Lawang-style candi bentar, or the module's temple).
// Vanilla JS, no framework, no build step -- serve over http(s), not file://
// (the JSON fetch needs a real origin).
//
// Changes vs the starter app.js (see README "Notes on fixes"):
//  * the language toggle now re-renders the OPEN info panel and the quiz
//    banner (before, an open panel stayed in the old language until the
//    hotspot was tapped again -- verify_ar_app.py hid this by re-tapping);
//  * model switcher + per-model camera framing (?model=gapura|pusaka);
//  * all UI strings follow the language, not just hotspot text;
//  * the unused, never-attached annotation <div> was removed.

(function () {
  "use strict";

  const MODELS = {
    gapura: {
      src: "assets/gapura_bentar.glb",
      hotspots: "assets/gapura_bentar.json",
      orbit: "30deg 72deg 0.85m",
      alt_en: "A 1:50 procedural model of a candi bentar (split gateway) in the style of Gapura Wringin Lawang, Trowulan",
      alt_id: "Model prosedural skala 1:50 sebuah candi bentar (gapura terbelah) bergaya Gapura Wringin Lawang, Trowulan",
      label_en: "Candi bentar (1:50)",
      label_id: "Candi bentar (1:50)",
    },
    pusaka: {
      src: "assets/pusaka_temple.glb",
      hotspots: "assets/hotspots.json",
      orbit: "35deg 75deg 1.2m",
      alt_en: "A procedurally generated candi (temple) model with a stepped base, body, roof, and a stupa finial",
      alt_id: "Model candi prosedural dengan kaki bertingkat, tubuh, atap, dan puncak stupa",
      label_en: "Module temple",
      label_id: "Candi modul",
    },
  };

  const UI = {
    en: { quizOff: "Quiz mode: off", quizOn: "Quiz mode: on", lang: "EN / ID", ar: "View in your space (AR)",
          prompt: "Tap the part named:", correct: "Correct!", wrong: "Not quite",
          wrongText: (got, want) => `That was the ${got}. Looking for the ${want}.`,
          loading: "Loading the model…", model: "Model" },
    id: { quizOff: "Mode kuis: mati", quizOn: "Mode kuis: aktif", lang: "ID / EN", ar: "Lihat di ruanganmu (AR)",
          prompt: "Ketuk bagian bernama:", correct: "Benar!", wrong: "Belum tepat",
          wrongText: (got, want) => `Itu adalah ${got}. Yang dicari adalah ${want}.`,
          loading: "Memuat model…", model: "Model" },
  };

  const $ = (id) => document.getElementById(id);
  const viewer = $("viewer");
  const infoPanel = $("info-panel");
  const infoTitle = $("info-title");
  const infoText = $("info-text");
  const langToggle = $("lang-toggle");
  const quizToggle = $("quiz-toggle");
  const quizBanner = $("quiz-banner");
  const quizPrompt = $("quiz-prompt-text");
  const quizTargetEl = $("quiz-target");
  const quizScoreEl = $("quiz-score");
  const modelSelect = $("model-select");
  const arButton = $("ar-button");

  let lang = "en";              // "en" | "id"
  let quizMode = false;
  let hotspots = [];
  let quizTarget = null;
  let quizScore = { correct: 0, attempts: 0 };
  // what the info panel is showing, so a language switch can re-render it:
  // {kind: "info", hotspot} or {kind: "quiz", hotspot, ok}
  let panelState = null;
  let modelKey = "gapura";

  const t = (hotspot, field) => hotspot[`${field}_${lang}`];

  function renderPanel() {
    if (!panelState) { infoPanel.hidden = true; return; }
    const h = panelState.hotspot;
    if (panelState.kind === "info") {
      infoTitle.textContent = t(h, "name");
      infoText.textContent = t(h, "text");
    } else if (panelState.ok) {
      infoTitle.textContent = UI[lang].correct;
      infoText.textContent = `${t(h, "name")} -- ${t(h, "text")}`;
    } else {
      infoTitle.textContent = UI[lang].wrong;
      infoText.textContent = UI[lang].wrongText(t(h, "name"), t(panelState.wanted, "name"));
    }
    infoPanel.hidden = false;
  }

  function hideInfo() { panelState = null; renderPanel(); }

  function renderChrome() {
    document.documentElement.lang = lang;
    langToggle.textContent = UI[lang].lang;
    quizToggle.textContent = quizMode ? UI[lang].quizOn : UI[lang].quizOff;
    arButton.textContent = UI[lang].ar;
    quizPrompt.textContent = UI[lang].prompt;
    if (quizTarget) quizTargetEl.textContent = t(quizTarget, "name");
    quizScoreEl.textContent = `${quizScore.correct}/${quizScore.attempts}`;
    viewer.alt = MODELS[modelKey][`alt_${lang}`];
    for (const opt of modelSelect.options) opt.textContent = MODELS[opt.value][`label_${lang}`];
    for (const b of viewer.querySelectorAll(".hotspot")) {
      const h = hotspots.find((x) => `hotspot-${x.id}` === b.slot);
      if (h) { b.setAttribute("aria-label", t(h, "name")); b.title = t(h, "name"); }
    }
  }

  function pickNewQuizTarget() {
    if (hotspots.length === 0) return;
    const others = hotspots.filter((h) => h !== quizTarget);
    quizTarget = others[Math.floor(Math.random() * others.length)] || hotspots[0];
    renderChrome();
  }

  function handleHotspotClick(hotspot) {
    if (!quizMode) {
      panelState = { kind: "info", hotspot };
    } else {
      quizScore.attempts += 1;
      const ok = hotspot.id === quizTarget.id;
      if (ok) quizScore.correct += 1;
      panelState = { kind: "quiz", hotspot, ok, wanted: quizTarget };
      pickNewQuizTarget();
    }
    renderPanel();
  }

  function buildHotspotButton(hotspot) {
    const button = document.createElement("button");
    button.slot = `hotspot-${hotspot.id}`;
    button.className = "hotspot";
    button.dataset.position = hotspot.position.map((v) => `${v}m`).join(" ");
    button.dataset.normal = hotspot.normal.map((v) => `${v}m`).join(" ");
    button.dataset.id = hotspot.id;
    // With data-visibility-attribute="visible", model-viewer toggles a
    // data-visible attribute on the hotspot from its occlusion/facing test
    // (without it, no attribute is ever set). style.css dims hidden ones.
    button.dataset.visibilityAttribute = "visible";
    button.textContent = "+";
    button.addEventListener("click", () => handleHotspotClick(hotspot));
    return button;
  }

  // ---- real occlusion test --------------------------------------------------
  const OCCLUSION_MARGIN = 0.005;     // metres; the anchors sit 1 mm off the surface

  function cameraPosition() {
    // model-viewer's orbit: theta about +y measured from +z toward +x,
    // phi measured down from +y, around the camera target.
    const o = viewer.getCameraOrbit();
    const c = viewer.getCameraTarget();
    const s = Math.sin(o.phi);
    return [c.x + o.radius * s * Math.sin(o.theta), c.y + o.radius * Math.cos(o.phi),
            c.z + o.radius * s * Math.cos(o.theta)];
  }

  const dist = (a, b) => Math.hypot(a[0] - b.x, a[1] - b.y, a[2] - b.z);

  function hotspotOccluded(button, cam, rect) {
    const q = viewer.queryHotspot(button.slot);
    if (!q || !q.facingCamera) return false;      // model-viewer already hides it
    const hit = viewer.positionAndNormalFromPoint(rect.left + q.canvasPosition.x,
                                                  rect.top + q.canvasPosition.y);
    if (!hit) return false;
    return dist(cam, hit.position) < dist(cam, q.position) - OCCLUSION_MARGIN;
  }

  let occlusionQueued = false;
  function updateOcclusion() {
    occlusionQueued = false;
    if (!viewer.loaded) return;
    const cam = cameraPosition();
    const rect = viewer.getBoundingClientRect();
    for (const b of viewer.querySelectorAll(".hotspot")) {
      b.classList.toggle("occluded", hotspotOccluded(b, cam, rect));
    }
  }
  function queueOcclusion() {
    if (!occlusionQueued) { occlusionQueued = true; requestAnimationFrame(updateOcclusion); }
  }
  viewer.addEventListener("camera-change", queueOcclusion);
  viewer.addEventListener("load", queueOcclusion);
  window.addEventListener("resize", queueOcclusion);

  function loadModel(key) {
    modelKey = MODELS[key] ? key : "gapura";
    const m = MODELS[modelKey];
    modelSelect.value = modelKey;
    viewer.querySelectorAll(".hotspot").forEach((el) => el.remove());
    hotspots = [];
    quizTarget = null;
    hideInfo();
    viewer.cameraOrbit = m.orbit;
    viewer.src = m.src;
    return fetch(m.hotspots)
      .then((res) => { if (!res.ok) throw new Error(`${m.hotspots}: HTTP ${res.status}`); return res.json(); })
      .then((data) => {
        hotspots = data.hotspots;
        hotspots.forEach((h) => viewer.appendChild(buildHotspotButton(h)));
        pickNewQuizTarget();
        queueOcclusion();
        document.body.dataset.model = modelKey;          // hook for verify_ar_app.py
        document.body.dataset.hotspots = String(hotspots.length);
      })
      .catch((err) => {
        console.error("Could not load the hotspot file -- run make_temple_glb.py / make_gapura_glb.py first.", err);
      });
  }

  langToggle.addEventListener("click", () => {
    lang = lang === "en" ? "id" : "en";
    renderChrome();
    renderPanel();          // re-render an OPEN panel in the new language
  });

  quizToggle.addEventListener("click", () => {
    quizMode = !quizMode;
    quizToggle.setAttribute("aria-pressed", String(quizMode));
    quizBanner.hidden = !quizMode;
    hideInfo();
    if (quizMode) {
      quizScore = { correct: 0, attempts: 0 };
      pickNewQuizTarget();
    }
    renderChrome();
  });

  modelSelect.addEventListener("change", () => {
    const url = new URL(window.location.href);
    url.searchParams.set("model", modelSelect.value);
    history.replaceState(null, "", url);
    loadModel(modelSelect.value);
  });

  $("info-close").addEventListener("click", hideInfo);

  // The script is at the end of <body>, so the DOM is already parsed.
  const params = new URLSearchParams(window.location.search);
  if (params.get("lang") === "id") lang = "id";
  renderChrome();
  loadModel(params.get("model") || "gapura").then(renderChrome);
})();
