#!/usr/bin/env python3
"""
tools/three_export.py
Uji viewer Three.js secara otomatis dengan Chrome headless (waktu nyata, bukan virtual time):
  1. sajikan folder web/ di http://127.0.0.1:<port>/
  2. buka index.html?export=1&post=1 di Chrome headless
  3. halaman merender pose default, mengukur frame time (300 frame), lalu POST hasilnya ke /__result
  4. simpan web/mymodel_three.ppm dan logs/lab3_three_bench.json

    python3 tools/three_export.py [--chrome PATH] [--gl swiftshader|default]

Catatan: ini menguji JALUR yang sama dengan browser biasa, tetapi GPU-nya bisa berbeda (headless sering
memakai SwiftShader = WebGL di CPU). Frame time GPU sungguhan dibaca dari label FPS di browser biasa.
"""

import argparse
import base64
import functools
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class Handler(http.server.SimpleHTTPRequestHandler):
    result = None

    def do_POST(self):
        if self.path == "/__result":
            body = self.rfile.read(int(self.headers["Content-Length"]))
            Handler.result = json.loads(body)
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404)

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome", default=CHROME)
    ap.add_argument("--gl", choices=["default", "swiftshader"], default="default")
    ap.add_argument("--timeout", type=float, default=90)
    ap.add_argument("--query", default="", help="parameter tambahan, mis. 'tex=0&aa=0'")
    ap.add_argument("--out", default="web/mymodel_three.ppm")
    args = ap.parse_args()

    if not os.path.exists(os.path.join(WEB, "mymodel.obj")):
        sys.exit("web/mymodel.obj belum ada: jalankan python3 make_model.py")

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=WEB))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    url = f"http://127.0.0.1:{port}/index.html?export=1&post=1" + (f"&{args.query}" if args.query else "")
    with tempfile.TemporaryDirectory() as profile:
        cmd = [args.chrome, "--headless=new", f"--user-data-dir={profile}", "--no-first-run",
               "--no-default-browser-check", "--window-size=800,900"]
        if args.gl == "swiftshader":
            cmd += ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
        proc = subprocess.Popen(cmd + [url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.time()
        while Handler.result is None and time.time() - t0 < args.timeout and proc.poll() is None:
            time.sleep(0.2)
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    srv.shutdown()

    r = Handler.result
    if r is None:
        sys.exit(f"tidak ada hasil dari halaman dalam {args.timeout:.0f} s (CDN Three.js tidak bisa diakses?)")
    if "error" in r:
        sys.exit(f"halaman melapor error: {r['error']}")

    with open(os.path.join(ROOT, args.out), "wb") as f:
        f.write(base64.b64decode(r["ppm"]))
    bench = dict(r["bench"], gl_mode=args.gl, query=args.query, date=time.strftime("%Y-%m-%d %H:%M"))
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    if not args.query:
        with open(os.path.join(ROOT, "logs", "lab3_three_bench.json"), "w") as f:
            json.dump(bench, f, indent=2)
    print(f"tulis {args.out}" + ("" if args.query else " dan logs/lab3_three_bench.json"))
    print(json.dumps(bench, indent=2))


if __name__ == "__main__":
    main()
