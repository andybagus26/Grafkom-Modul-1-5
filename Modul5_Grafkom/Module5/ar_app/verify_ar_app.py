"""Automated, headless-browser verification of the Pusaka3D AR Explainer.

Not a substitute for the real AR session (WebXR / Android Scene Viewer / iOS
Quick Look) on a phone -- that OS-level handoff cannot be driven from a
headless browser (README "Known deviations"). What this checks, in a real
Chromium engine via Playwright, is everything up to that handoff, for BOTH
models the app ships:

  module temple (?model=pusaka) -- the starter's 10 checks, plus
    * the language toggle re-renders an ALREADY OPEN panel (the starter
      check re-tapped the hotspot after toggling, which hid that bug);
  my candi bentar (?model=gapura) --
    * model loads/renders, 6 hotspots injected, Indonesian panel text;
    * occlusion: the hotspot on the inner face of the split ("celah") is
      reported hidden (no data-visible) from a side view and visible when
      looking down the passage, and a hidden hotspot is drawn dimmed.

Requires: pip install playwright. Uses Playwright's own Chromium if installed
(python -m playwright install chromium), otherwise the installed Google
Chrome (channel="chrome"). Serve the app first:
    python -m http.server 8743        (from ar_app/)
Run: python verify_ar_app.py [base_url]   (default http://localhost:8743)
"""
from __future__ import annotations

import os
import sys

from playwright.sync_api import sync_playwright, Error as PWError

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8743"
HERE = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(HERE, "screenshots")
ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
        "--enable-webgl", "--ignore-gpu-blocklist"]

_checks = 0


def check(name, condition):
    global _checks
    print(f"[{'ok' if condition else 'FAIL'}] {name}")
    assert condition, f"failed: {name}"
    _checks += 1


def launch(p):
    try:
        return p.chromium.launch(args=ARGS), "Playwright Chromium"
    except PWError:
        return p.chromium.launch(channel="chrome", args=ARGS), "Google Chrome (channel=chrome)"


def wait_ready(page, n_hotspots):
    page.wait_for_function(
        f"() => document.body.dataset.hotspots === '{n_hotspots}' && "
        "document.querySelector('model-viewer').loaded && document.querySelector('model-viewer').modelIsVisible",
        timeout=30000)
    page.wait_for_timeout(800)


def set_orbit(page, orbit):
    """Move the camera and wait until model-viewer's CURRENT orbit equals the
    goal (theta/phi within 0.1 deg). A fixed sleep is not enough: in a headless
    tab frames are throttled and the camera can still be on its way, so a
    reading taken too early belongs to some other angle."""
    page.evaluate("""(o) => { const v = document.querySelector('model-viewer');
                              v.cameraOrbit = o; v.jumpCameraToGoal(); }""", orbit)
    page.wait_for_function("""() => { const v = document.querySelector('model-viewer');
        const a = v.getCameraOrbit(), g = v.cameraOrbit.split(' ').map(parseFloat);
        const d = (x, y) => Math.abs(((x * 180 / Math.PI - y) % 360 + 540) % 360 - 180);
        return d(a.theta, g[0]) < 0.1 && d(a.phi, g[1]) < 0.1; }""", timeout=10000)
    page.wait_for_timeout(150)   # one more frame so hotspot attributes/occlusion update


def visible_ids(page):
    return page.evaluate("""() => [...document.querySelectorAll('.hotspot')]
                                  .filter(b => b.hasAttribute('data-visible')).map(b => b.dataset.id)""")


def main():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    page_errors = []
    with sync_playwright() as p:
        browser, which = launch(p)
        print(f"browser: {which} {browser.version}")
        page = browser.new_page(viewport={"width": 390, "height": 800})
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        # ---- module temple: the starter's checks ----------------------------
        page.goto(f"{BASE_URL}/index.html?model=pusaka", wait_until="networkidle", timeout=30000)
        wait_ready(page, 5)
        mv = page.evaluate("""() => { const el = document.querySelector('model-viewer');
            return { exists: !!el, loaded: el.loaded, modelIsVisible: el.modelIsVisible,
                     hasCanvas: !!(el.shadowRoot && el.shadowRoot.querySelector('canvas')) }; }""")
        check("model-viewer element exists", mv["exists"])
        check("model reported loaded", mv["loaded"])
        check("model reported visible (rendered)", mv["modelIsVisible"])
        check("a real WebGL <canvas> was created inside model-viewer", mv["hasCanvas"])
        n = page.evaluate("document.querySelectorAll('.hotspot').length")
        check(f"5 hotspots injected from hotspots.json (found {n})", n == 5)
        check("AR launch button present", page.evaluate("!!document.getElementById('ar-button')"))
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "m5_ar_overview.png"))

        page.click("button[slot='hotspot-stupa']")
        page.wait_for_timeout(300)
        title = page.inner_text("#info-title")
        check(f"clicking a hotspot opens the info panel (title='{title}')",
              not page.evaluate("document.getElementById('info-panel').hidden") and len(title) > 0)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "m5_ar_infopanel_en.png"))

        # NEW: toggle language with the panel still open, do NOT re-tap
        page.click("#lang-toggle")
        page.wait_for_timeout(300)
        title_open = page.inner_text("#info-title")
        check(f"language toggle re-renders the OPEN panel without a re-tap ('{title}' -> '{title_open}')",
              title_open == "Puncak / Stupa")
        page.click("button[slot='hotspot-stupa']")
        page.wait_for_timeout(300)
        title_id = page.inner_text("#info-title")
        check(f"language toggle changes the panel text ('{title}' -> '{title_id}')", title != title_id)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "m5_ar_infopanel_id.png"))

        page.click("#info-close")
        page.click("#quiz-toggle")
        page.wait_for_timeout(300)
        quiz_target = page.inner_text("#quiz-target")
        check(f"quiz mode picks a target ('{quiz_target}')",
              not page.evaluate("document.getElementById('quiz-banner').hidden") and len(quiz_target) > 0)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "m5_ar_quizmode.png"))

        # ---- my model: candi bentar ------------------------------------------
        page.goto(f"{BASE_URL}/index.html?model=gapura&lang=id", wait_until="networkidle", timeout=30000)
        wait_ready(page, 6)
        check("candi bentar model loaded and rendered",
              page.evaluate("document.querySelector('model-viewer').src.endsWith('gapura_bentar.glb')"))
        n = page.evaluate("document.querySelectorAll('.hotspot').length")
        check(f"6 hotspots injected from gapura_bentar.json (found {n})", n == 6)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "m5_gapura_overview.png"))
        page.click("button[slot='hotspot-skala']")
        page.wait_for_timeout(300)
        t_id = page.inner_text("#info-title")
        check(f"?lang=id opens the panel in Indonesian ('{t_id}')", t_id.startswith("Ukuran"))
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "m5_gapura_panel_id.png"))
        page.click("#info-close")

        # occlusion: the inner-face hotspot. The passage runs along z, so a view
        # from +z looks straight down it; a view from +x sees only the outer side.
        set_orbit(page, "90deg 80deg 0.85m")          # from +x: side of the east half
        side = visible_ids(page)
        opacity = page.evaluate("getComputedStyle(document.querySelector(\"[data-id='celah']\")).opacity")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "m5_gapura_side_occluded.png"))
        set_orbit(page, "0deg 80deg 0.85m")           # from +z: down the passage
        front = visible_ids(page)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "m5_gapura_passage_view.png"))
        check(f"occlusion: 'celah' hidden from the side view (visible there: {side})", "celah" not in side)
        check(f"occlusion: hidden hotspot is dimmed (opacity {opacity})", float(opacity) < 0.5)
        check(f"occlusion: 'celah' visible looking down the passage (visible there: {front})", "celah" in front)

        check("no uncaught JS errors on the page", len(page_errors) == 0)
        browser.close()

    print(f"\nALL CHECKS PASSED ({_checks} ok)")
    print("NOTE: this verifies everything up to the AR launch. The actual WebXR/"
          "Scene Viewer/Quick Look handoff needs a real phone -- see README.md.")


if __name__ == "__main__":
    main()
