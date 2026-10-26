import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const files = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
  ['/report.css', ['report.css', 'text/css; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/report.js', ['report.js', 'text/javascript; charset=utf-8']],
  ['/favicon.svg', ['favicon.svg', 'image/svg+xml']],
]);
const port = Number(process.env.PORT || 4173);
const server = http.createServer(async (request, response) => {
  const path = new URL(request.url, 'http://localhost').pathname;
  const file = files.get(path);
  if (!file || !['GET', 'HEAD'].includes(request.method)) {
    response.writeHead(404); response.end('Not found'); return;
  }
  try {
    const data = await readFile(fileURLToPath(new URL(file[0], import.meta.url)));
    response.writeHead(200, {
      'Content-Type': file[1], 'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
      'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; base-uri 'none'; form-action 'none'",
    });
    response.end(request.method === 'HEAD' ? undefined : data);
  } catch { response.writeHead(500); response.end('Preview unavailable'); }
});
server.listen(port, '127.0.0.1', () => console.log(`Local: http://127.0.0.1:${port}`));
