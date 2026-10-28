# cors-errors-explained

The CORS errors you see in the browser console, what each one actually means, and the smallest fix. Every error here can be reproduced on your own machine with a 100-line Python script, so you can break it and fix it yourself.

```bash
git clone https://github.com/qwemort/cors-errors-explained
cd cors-errors-explained
python3 demo.py            # no dependencies
# open http://localhost:8002/ and press the buttons, keep DevTools > Console open
```

The page runs on `localhost:8002`, the API on `localhost:8001`. Different ports are different origins, so the browser applies CORS. Each button calls one endpoint that is configured wrongly in one specific way. The last one (`/ok`) is the fixed version.

JavaScript only gets a generic `TypeError: Failed to fetch`. The useful message is in the console, and it is the same one you see in the table below (Chrome wording; Firefox words it differently but the causes are the same).

## Error, cause, fix

| Console message (Chrome) | Cause | Fix |
|---|---|---|
| `No 'Access-Control-Allow-Origin' header is present on the requested resource` | The API response has no CORS headers at all. Also happens when an error page (404, 500, proxy) is returned without them, so the real error is hidden. | Send `Access-Control-Allow-Origin: <your page origin>` on every response, including errors. Check the status in the Network tab first. |
| `The value of the 'Access-Control-Allow-Origin' header in the response must not be the wildcard '*' when the request's credentials mode is 'include'` | You send cookies (`credentials: 'include'`) but the server answers `*`. | Answer the exact origin of the page, add `Access-Control-Allow-Credentials: true` and `Vary: Origin`. |
| `The 'Access-Control-Allow-Origin' header has a value 'X' that is not equal to the supplied origin` | The server allows a different origin than the one making the request (often `localhost:3000` vs `localhost:5173`, or `http` vs `https`, or a `www.` mismatch). | Allow the real origin. Compare scheme, host and port character by character. |
| `The value of the 'Access-Control-Allow-Credentials' header in the response is '' which must be 'true' when the request's credentials mode is 'include'` | Origin is right but the credentials header is missing. | Add `Access-Control-Allow-Credentials: true`. |
| `Response to preflight request doesn't pass access control check: It does not have HTTP ok status` | The browser sent an `OPTIONS` preflight first and the server answered 4xx/5xx (404, 405, 401 from an auth middleware, a redirect). | Make `OPTIONS` return 200 or 204 with the CORS headers, before auth and routing. |
| `Request header field x-api-key is not allowed by Access-Control-Allow-Headers in preflight response` | A custom header (or `Authorization`) was sent but the preflight answer does not list it. | Add it to `Access-Control-Allow-Headers`. |
| `Method PUT is not allowed by Access-Control-Allow-Methods in preflight response` | The method is not listed in the preflight answer. | Add it to `Access-Control-Allow-Methods`. |

The `preflight-405` case in `demo.py` shows the "does not have HTTP ok status" message. If the preflight also lacks the origin header, Chrome reports "No 'Access-Control-Allow-Origin' header is present" instead; same root problem, different first message.

## When does the browser send a preflight?

A simple request goes out directly: `GET`, `HEAD` or `POST` with only basic headers and a `Content-Type` of `text/plain`, `application/x-www-form-urlencoded` or `multipart/form-data`. Anything else triggers an `OPTIONS` request first: `PUT`, `PATCH`, `DELETE`, a custom header, an `Authorization` header, or `Content-Type: application/json`. That last one surprises people: a plain JSON `POST` is already preflighted. See [MDN: Preflight request](https://developer.mozilla.org/en-US/docs/Glossary/Preflight_request).

## Fixes by stack

**Express (`cors` package)**

```js
const cors = require('cors');
app.use(cors({ origin: ['http://localhost:3000'], credentials: true }));
// the package answers OPTIONS preflights for you; register it before your routes and auth
```

**Flask (`flask-cors`)**

```python
from flask_cors import CORS
CORS(app, origins=["http://localhost:3000"], supports_credentials=True)
```

**nginx**

```nginx
map $http_origin $cors_origin {
    default "";
    "http://localhost:3000" $http_origin;
}
server {
    location /api/ {
        if ($request_method = OPTIONS) {
            add_header Access-Control-Allow-Origin $cors_origin always;
            add_header Access-Control-Allow-Credentials true always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
            add_header Access-Control-Max-Age 600 always;
            add_header Vary Origin always;
            return 204;
        }
        add_header Access-Control-Allow-Origin $cors_origin always;
        add_header Access-Control-Allow-Credentials true always;
        add_header Vary Origin always;
        proxy_pass http://backend;
    }
}
```

**No access to the server? Proxy it in development.** The browser only applies CORS to cross-origin calls, so make the call same-origin. Vite:

```js
// vite.config.js
export default { server: { proxy: { '/api': 'http://localhost:8001' } } };
```

Then call `/api/...` from your app. webpack-dev-server and Next.js rewrites work the same way.

## Things that are easy to get wrong

- **`*` is fine without cookies, not with them.** For credentialed requests the origin must be exact, and so must the headers and methods lists in many browsers (`*` is not treated as a wildcard when credentials are included).
- **Echoing any `Origin` back with credentials is not a fix, it is a vulnerability.** It lets every site read your logged-in responses. Check the origin against an allowlist. Add `Vary: Origin` whenever the value changes per request, or caches will serve the wrong one.
- **CORS protects reading, not sending.** A simple cross-origin request still reaches your server; the browser only refuses to hand the response to the page. It is not authentication. curl, Postman and server-to-server calls ignore CORS entirely, which is why "it works in Postman".
- **Cookies are a separate gate.** CORS headers can be perfect and the cookie still not sent. Across different sites (not just different ports) the cookie needs `SameSite=None; Secure`, and browsers increasingly block third-party cookies. The demo is same-site (`localhost` to `localhost`), so the cookie goes through.
- **Redirects break preflights.** A preflight must not be redirected. `http` to `https` or a trailing-slash redirect on the API is a common cause.
- **The error can hide the real problem.** If the API crashed with a 500 and the error page has no CORS headers, you see a CORS error. Look at the status in the Network tab.

## A note on extensions that "fix CORS"

Browser extensions that add CORS headers can be handy for local development, but they change what the browser lets pages read. Use one only for the pages you are developing, keep it off otherwise, and prefer one that asks for access per site rather than to every site at install. I make one (PureHeaders, below), so weigh that; the demo and everything above work without any extension.

## About

Maintained by the developer of PureHeaders, PureMock, PureJSON and PureSession, small browser extensions for web developers (no accounts, no telemetry). PureHeaders adds and changes request and response headers, including CORS headers, only on the sites you pick. Corrections and new cases are welcome as issues or pull requests. Contact: papana44444@gmail.com

MIT License.
