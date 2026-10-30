#!/usr/bin/env node
/* Build the LittleFS payload the tank unit (M1) serves.
 *
 *   npm run build                          → dist/
 *   node tools/build-device-bundle.mjs     → device/  (+ device-littlefs.bin when mklittlefs is found)
 *
 * Text assets are pre-gzipped (the ESP8266 serves them with Content-Encoding:
 * gzip — no on-device compression, no CPU cost per request). Binary assets
 * (woff2, png, svg icons) are already compressed formats and are copied raw.
 * Dependencies: Node built-ins only. */

import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { gzipSync } from "node:zlib";
import { fileURLToPath } from "node:url";

const webappRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const distDir = join(webappRoot, "dist");
const outDir = join(webappRoot, "device");

const GZIP_EXTENSIONS = new Set([".html", ".js", ".css", ".json", ".svg"]);
const FS_SIZE = 0x100000; // 1 MB — the "4M1M" flash layout (FS at 0x300000)
const FS_OFFSET = 0x300000;
const LFS_NAME_MAX = 32; // the ESP8266 core builds LittleFS with 32-char image paths

/* @fontsource filenames are far longer than LittleFS allows — shorten them and
 * rewrite the references inside the CSS before it is gzipped. */
const fontRenames = [
  { pattern: /saira-latin-ext-wght-normal-[A-Za-z0-9_-]*\.woff2/g, short: "f-lx.woff2" },
  { pattern: /saira-latin-wght-normal-[A-Za-z0-9_-]*\.woff2/g, short: "f-latin.woff2" },
  { pattern: /saira-vietnamese-wght-normal-[A-Za-z0-9_-]*\.woff2/g, short: "f-vn.woff2" },
];

const shorten = (rel) => {
  let out = rel;
  for (const r of fontRenames) out = out.replace(r.pattern, r.short);
  return out;
};

if (!existsSync(join(distDir, "index.html"))) {
  console.error("dist/index.html not found — run `npm run build` first.");
  process.exit(1);
}

rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });

const walk = (dir) =>
  readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = join(dir, e.name);
    return e.isDirectory() ? walk(p) : [p];
  });

let gzTotal = 0;
let rawTotal = 0;
let tooLong = null;
const files = walk(distDir).sort();
for (const file of files) {
  const rel = relative(distDir, file).split("\\").join("/");
  const lower = rel.toLowerCase();
  const ext = lower.slice(lower.lastIndexOf("."));
  const relShort = shorten(rel);
  const imagePosix = `/${relShort}`;
  if (imagePosix.length > LFS_NAME_MAX) tooLong = imagePosix;
  const dest = join(outDir, relShort);
  mkdirSync(dirname(dest), { recursive: true });
  if (GZIP_EXTENSIONS.has(ext)) {
    let content = readFileSync(file);
    if (ext === ".css") {
      // retarget the font urls at their short image names
      let css = content.toString("utf8");
      for (const r of fontRenames) css = css.replace(r.pattern, r.short);
      content = Buffer.from(css, "utf8");
    }
    const gz = gzipSync(content, { level: 9 });
    writeFileSync(`${dest}.gz`, gz);
    gzTotal += gz.length;
    console.log(`  gzip  ${imagePosix}  ${statSync(file).size} -> ${gz.length} B`);
  } else {
    copyFileSync(file, dest);
    rawTotal += statSync(file).size;
    console.log(`  copy  ${imagePosix}  ${statSync(file).size} B`);
  }
}

if (tooLong) {
  console.error(`\nimage path exceeds LittleFS's ${LFS_NAME_MAX}-char limit: ${tooLong}`);
  process.exit(1);
}

const total = gzTotal + rawTotal;
console.log(`\npayload: ${total.toLocaleString("en-GB")} B (${(total / 1024).toFixed(1)} KB) of ${FS_SIZE.toLocaleString("en-GB")} B LittleFS`);

/* mklittlefs ships with the Arduino ESP8266 core — build the image if present. */
const candidates = [
  process.env.LOCALAPPDATA ? join(process.env.LOCALAPPDATA, "Arduino15", "packages", "esp8266", "tools", "mklittlefs") : "",
  process.env.USERPROFILE ? join(process.env.USERPROFILE, "AppData", "Local", "Arduino15", "packages", "esp8266", "tools", "mklittlefs") : "",
].filter(Boolean);

const findMklittlefs = () => {
  for (const base of candidates) {
    if (!existsSync(base)) continue;
    const found = walk(base).filter((p) => /mklittlefs(\.exe)?$/i.test(p));
    if (found.length) return found.sort().at(-1);
  }
  return null;
};

const mklittlefs = findMklittlefs();
if (mklittlefs) {
  const image = join(webappRoot, "device-littlefs.bin");
  rmSync(image, { force: true });
  try {
    execFileSync(mklittlefs, ["-c", outDir, "-s", `0x${FS_SIZE.toString(16)}`, image], { stdio: "inherit" });
  } catch {
    console.error("\nmklittlefs failed — the payload is ready in device/, see the errors above.");
    process.exit(1);
  }
  console.log(`\nimage:   device-littlefs.bin (${(statSync(image).size / 1024).toFixed(1)} KB)`);
  console.log(`flash it (4M1M layout, FS offset 0x${FS_OFFSET.toString(16)}):`);
  console.log(`  esptool.py --port <PORT> write_flash 0x${FS_OFFSET.toString(16)} device-littlefs.bin`);
} else {
  console.log("\nmklittlefs not found (install the Arduino ESP8266 core) — the payload is ready in device/.");
  console.log("Build the image with:  mklittlefs -c device -s 0x100000 device-littlefs.bin");
  console.log(`Flash it at offset 0x${FS_OFFSET.toString(16)} (4M1M layout).`);
}
