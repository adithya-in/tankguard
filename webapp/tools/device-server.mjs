#!/usr/bin/env node
/* A desk-stand-in for the tank unit's HTTP server: the exact route table,
 * MIME types, pre-gzipped serving and cache rules that firmware/m1_tank runs
 * after the LittleFS patch. Point a browser at it and the webapp behaves as
 * if the ESP8266 itself were serving it — same-origin /data, bundle from
 * flash, everything.
 *
 *   node tools/device-server.mjs [port]     (default 4311)
 *
 * Serves the payload produced by tools/build-device-bundle.mjs (device/) and
 * a live /data frame computed with the firmware's own scoreFrom() formula. */

import { createServer } from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { extname, join, normalize, sep } from "node:path";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname as dirName, resolve } from "node:path";

const webappRoot = resolve(dirName(fileURLToPath(import.meta.url)), "..");
const deviceDir = join(webappRoot, "device");
const PORT = Number(process.argv[2] ?? 4311);

if (!existsSync(join(deviceDir, "index.html.gz"))) {
  console.error("device/index.html.gz not found — run `node tools/build-device-bundle.mjs` first.");
  process.exit(1);
}

// firmware/m1_tank scoreFrom(), kept in lockstep
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const scoreFrom = (turb, tds, ph, temp) => {
  const sTurb = clamp(100 - (turb - 5) * (100 / 45), 0, 100);
  const sTds = clamp(100 - (tds - 300) * (100 / 700), 0, 100);
  const sPh = clamp(100 - Math.abs(ph - 7) * 40, 0, 100);
  const tdev = Math.max(0, Math.abs(temp - 25) - 5);
  const sTemp = clamp(100 - tdev * 4, 0, 100);
  return 0.4 * sTurb + 0.25 * sTds + 0.25 * sPh + 0.1 * sTemp;
};

const t0 = Date.now();
const liveFrame = () => {
  const s = (Date.now() - t0) / 1000;
  const turb = 11 + 2 * Math.sin(s / 40);
  const tds = Math.round(320 + 20 * Math.sin(s / 60));
  const ph = 7.2 + 0.1 * Math.sin(s / 90);
  const temp = 27 + Math.sin(s / 120);
  return {
    score: +scoreFrom(turb, tds, ph, temp).toFixed(1),
    level: +(64 + 6 * Math.sin(s / 300)).toFixed(1),
    ph: +ph.toFixed(2),
    turb: +turb.toFixed(1),
    tds,
    temp: +temp.toFixed(1),
  };
};

const MIME = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".png": "image/png",
};

const server = createServer((req, res) => {
  const url = new URL(req.url ?? "/", `http://127.0.0.1:${PORT}`);
  const path = decodeURIComponent(url.pathname);

  // /data — same as handleData() in the sketch
  if (path === "/data") {
    res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" });
    res.end(JSON.stringify(liveFrame()));
    return;
  }

  // static bundle — same rules as serveFromFS() in the sketch
  let file = path === "/" ? "/index.html" : path;
  if (file.endsWith("/")) file += "index.html";
  const clean = normalize(file).split(sep).join("/");
  if (clean.includes("..") || !clean.startsWith("/")) {
    res.writeHead(404).end("not found");
    return;
  }

  const mime = MIME[extname(clean)] ?? "application/octet-stream";
  const cache = clean.startsWith("/assets/") ? "public, max-age=86400" : "no-cache";

  const gzPath = join(deviceDir, `${clean.slice(1)}.gz`);
  if (existsSync(gzPath)) {
    res.writeHead(200, { "Content-Type": mime, "Content-Encoding": "gzip", "Cache-Control": cache });
    createReadStream(gzPath).pipe(res);
    return;
  }
  const rawPath = join(deviceDir, clean.slice(1));
  if (existsSync(rawPath) && statSync(rawPath).isFile()) {
    res.writeHead(200, { "Content-Type": mime, "Cache-Control": cache });
    createReadStream(rawPath).pipe(res);
    return;
  }

  res.writeHead(404, { "Content-Type": "text/plain" });
  res.end("not found");
});

server.listen(PORT, "127.0.0.1", async () => {
  const index = await readFile(join(deviceDir, "index.html.gz"));
  console.log(`tank-unit stand-in on http://127.0.0.1:${PORT}/`);
  console.log(`bundle: ${index.length} B index.html.gz + assets from device/`);
  console.log("routes: / (gzip html) · /assets/* (gzip js/css, raw woff2) · /data (live frame)");
});
