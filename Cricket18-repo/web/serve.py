#!/usr/bin/env python3
"""Local server for the browser build (this machine only).

Threads in WebAssembly need SharedArrayBuffer, which browsers only enable on cross-origin isolated
pages, so every response carries COOP/COEP headers.

  /            web/ (the page)
  /build/      build_web/www (recomp.js / .wasm from build_web.sh)

The player picks their own game folder, which the browser copies into its private storage. With
--game <folder>, the page can also copy it from this server (this machine only):

  /gamefiles.json  [{path, size}] for every file in the folder
  /game/<path>     its files

Usage: python3 web/serve.py [--port 8007] [--game <folder>]
"""
import argparse
import http.server
import json
import os
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(os.path.dirname(HERE), "build_web", "www")
GAME = None  # --game folder


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".wasm": "application/wasm",
                      ".js": "text/javascript"}

    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if GAME and urllib.parse.urlparse(self.path).path == "/gamefiles.json":
            files = []
            for d, _, names in os.walk(GAME):
                for n in names:
                    if n == ".DS_Store": continue
                    f = os.path.join(d, n)
                    files.append({"path": os.path.relpath(f, GAME).replace(os.sep, "/"), "size": os.path.getsize(f),
                                  "mtime": int(os.path.getmtime(f))})
            body = json.dumps(files).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def translate_path(self, path):
        p = urllib.parse.unquote(urllib.parse.urlparse(path).path)
        if GAME and p.startswith("/game/"):
            f = os.path.realpath(os.path.join(GAME, p[len("/game/"):]))
            return f if f.startswith(GAME + os.sep) else os.path.join(GAME, "missing")
        if p.startswith("/build/"):
            return os.path.join(BUILD, p[len("/build/"):])
        return os.path.join(HERE, p.lstrip("/"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8007)
    ap.add_argument("--game", help="game folder the page may copy from this server")
    a = ap.parse_args()
    global GAME
    GAME = os.path.realpath(a.game) if a.game else None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"http://localhost:{a.port}/")
    srv.serve_forever()


if __name__ == "__main__":
    main()
