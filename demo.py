#!/usr/bin/env python3
"""Reproduces the most common CORS errors on your own machine, and shows the fix for each.

  python3 demo.py
  open http://localhost:8002/   (the page)   - it calls the API on http://localhost:8001/

Two servers: the page on :8002 and the API on :8001. Different ports mean different origins, so the browser applies CORS.
Open DevTools -> Console to read the exact error text; JavaScript only gets a generic "Failed to fetch"."""
import json, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

API, PAGE = 8001, 8002
PAGE_ORIGIN = f'http://localhost:{PAGE}'

# name -> (method, path, extra fetch options, title)
CASES = [
 ('ok',               'GET', '/ok',               {'credentials': 'include', 'headers': {'X-Api-Key': 'k'}}, 'Fixed: exact origin, credentials, headers, Vary'),
 ('no-header',        'GET', '/no-header',        {}, 'No Access-Control-Allow-Origin header'),
 ('wildcard-cookies', 'GET', '/wildcard-cookies', {'credentials': 'include'}, '"*" together with credentials'),
 ('wrong-origin',     'GET', '/wrong-origin',     {}, 'Allowed origin is not the page origin'),
 ('no-allow-cred',    'GET', '/no-allow-cred',    {'credentials': 'include'}, 'Credentials sent, no Allow-Credentials: true'),
 ('preflight-405',    'POST','/preflight-405',    {'headers': {'Content-Type': 'application/json'}, 'body': '{}'}, 'Preflight answered with 405'),
 ('missing-header',   'GET', '/missing-header',   {'headers': {'X-Api-Key': 'k'}}, 'Custom header not in Allow-Headers'),
 ('missing-method',   'PUT', '/missing-method',   {'body': '{}'}, 'Method not in Allow-Methods'),
]

def cors_ok(h, origin, creds=True, headers='content-type, x-api-key', methods='GET, POST, PUT, DELETE'):
    h['Access-Control-Allow-Origin'] = origin
    h['Vary'] = 'Origin'
    if creds: h['Access-Control-Allow-Credentials'] = 'true'
    h['Access-Control-Allow-Headers'] = headers
    h['Access-Control-Allow-Methods'] = methods
    h['Access-Control-Max-Age'] = '600'

class Api(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def reply(self, code, body, h):
        b = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b)))
        for k, v in h.items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(b)
    def do_OPTIONS(self):                       # preflight
        p = self.path.split('?')[0]; h = {}
        if p == '/preflight-405': cors_ok(h, PAGE_ORIGIN); return self.reply(405, {'error': 'OPTIONS not allowed'}, h)
        if p == '/ok': cors_ok(h, PAGE_ORIGIN)
        elif p == '/missing-header': cors_ok(h, PAGE_ORIGIN, headers='content-type')          # x-api-key missing
        elif p == '/missing-method': cors_ok(h, PAGE_ORIGIN, methods='GET, POST')             # PUT missing
        self.reply(204 if h else 404, {}, h)
    def do_ANY(self):
        p = self.path.split('?')[0]; h = {}
        cookie = self.headers.get('Cookie', '')
        body = {'ok': True, 'path': p, 'cookie_received': 'session=abc' in cookie}
        if p == '/ok': cors_ok(h, PAGE_ORIGIN)
        elif p == '/wildcard-cookies': h['Access-Control-Allow-Origin'] = '*'; h['Access-Control-Allow-Credentials'] = 'true'
        elif p == '/wrong-origin': h['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        elif p == '/no-allow-cred': h['Access-Control-Allow-Origin'] = PAGE_ORIGIN
        elif p == '/missing-header': cors_ok(h, PAGE_ORIGIN, headers='content-type')
        elif p == '/missing-method': cors_ok(h, PAGE_ORIGIN, methods='GET, POST')
        elif p == '/preflight-405': h['Access-Control-Allow-Origin'] = PAGE_ORIGIN
        # '/no-header': no CORS headers at all
        self.reply(200, body, h)
    do_GET = do_POST = do_PUT = do_DELETE = do_ANY

PAGE_HTML = """<!doctype html><meta charset=utf-8><title>CORS demo</title>
<style>body{font:15px system-ui;max-width:760px;margin:2em auto;padding:0 1em}button{margin:2px 8px 2px 0}
li{margin:.5em 0}.ok{color:#0a7d33}.bad{color:#b3261e}code{background:#eee;padding:1px 4px;border-radius:3px}</style>
<h1>CORS demo</h1>
<p>This page is on <code>localhost:8002</code>, the API on <code>localhost:8001</code>. Open DevTools &rarr; Console for the exact browser messages.</p>
<ul id=l></ul>
<script>
document.cookie = 'session=abc; path=/';
const CASES = __CASES__;
const API = 'http://localhost:__API__';
for (const [name, method, path, opts, title] of CASES) {
  const li = document.createElement('li'); li.id = name;
  li.innerHTML = '<button>Run</button><code>' + method + ' ' + path + '</code> ' + title + ' <b></b>';
  li.querySelector('button').onclick = async () => {
    const out = li.querySelector('b'); out.textContent = '...'; out.className = '';
    try {
      const r = await fetch(API + path, Object.assign({method}, opts));
      const j = await r.json();
      out.textContent = ' OK ' + r.status + ' (cookie sent: ' + j.cookie_received + ')'; out.className = 'ok';
    } catch (e) { out.textContent = ' BLOCKED (' + e.message + '); see Console'; out.className = 'bad'; }
  };
  document.getElementById('l').appendChild(li);
}
</script>"""

class Page(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        html = PAGE_HTML.replace('__CASES__', json.dumps(CASES)).replace('__API__', str(API)).encode()
        self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html))); self.end_headers(); self.wfile.write(html)

if __name__ == '__main__':
    for port, cls in ((API, Api), (PAGE, Page)):
        Thread(target=ThreadingHTTPServer(('127.0.0.1', port), cls).serve_forever, daemon=True).start()
    print(f'Open {PAGE_ORIGIN}/  (API on http://localhost:{API}). Ctrl+C to stop.', flush=True)
    try:
        while True: time.sleep(3600)
    except KeyboardInterrupt: pass
