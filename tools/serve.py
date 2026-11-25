#!/usr/bin/env python3
"""Local stand-in for Vercel's routing (cleanUrls + mobile user-agent rewrite) for tests: serve.py <public> <port>"""
import http.server, os, re, sys, functools
ROOT, PORT = sys.argv[1], int(sys.argv[2])
MOBILE = re.compile(r'iPhone|iPod|Android.*Mobile|Windows Phone|BlackBerry|BB10|Opera Mini|Mobile Safari|IEMobile|webOS')
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def translate_path(self, path):
        p = path.split('?')[0].split('#')[0]
        mob = bool(MOBILE.search(self.headers.get('User-Agent', '')))
        slug = p.strip('/') or 'index'
        if '/' not in slug and os.path.exists(os.path.join(ROOT, slug + '.html')):
            return os.path.join(ROOT, ('m/' if mob else '') + slug + '.html')
        return super().translate_path(path)
    def send_error(self, code, *a, **k):
        if code == 404:
            body = open(os.path.join(ROOT, '404.html'), 'rb').read()
            self.send_response(404); self.send_header('Content-Type', 'text/html'); self.end_headers(); self.wfile.write(body); return
        super().send_error(code, *a, **k)
http.server.ThreadingHTTPServer(('127.0.0.1', PORT), functools.partial(H, directory=ROOT)).serve_forever()
