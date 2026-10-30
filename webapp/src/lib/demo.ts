import { scoreFrom } from "./score";
import type { TankFrame } from "./types";

/* Demo feed — used when no tank unit answers (or ?demo=1). Values are a
   deterministic function of wall-clock time, so the backfilled 24 h and the
   live tick agree, and a reload reproduces the same story. The score is
   computed with the firmware's own formula, so the demo never shows a state
   the real device couldn't produce. */

const MIN = 60_000;

function hash(n: number): number {
  let h = (n ^ 0x9e3779b9) >>> 0;
  h = Math.imul(h ^ (h >>> 16), 2246822519);
  h = Math.imul(h ^ (h >>> 13), 3266489917);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

/** smooth deterministic noise in [-1, 1] at minute resolution */
function noise(seed: number, tMs: number): number {
  const i = Math.floor(tMs / MIN);
  const a = hash(seed * 1013 + i);
  const b = hash(seed * 1013 + i + 1);
  const f = (tMs % MIN) / MIN;
  const smooth = f * f * (3 - 2 * f);
  return (a + (b - a) * smooth) * 2 - 1;
}

const wave = (tMs: number, periodMin: number, phase: number): number => Math.sin((tMs / (periodMin * MIN)) * Math.PI * 2 + phase);

/** One demo frame at time tMs. Pure: same time in, same frame out. */
export function demoFrameAt(tMs: number): TankFrame {
  const turb = 7.5 + 4.5 * wave(tMs, 95, 0.4) + 2.8 * noise(1, tMs);
  const tds = 295 + 55 * wave(tMs, 160, 1.9) + 30 * noise(2, tMs);
  const ph = 7.15 + 0.35 * wave(tMs, 210, 4.1) + 0.14 * noise(3, tMs);
  const temp = 27.2 + 1.6 * wave(tMs, 720, 2.2) + 0.5 * noise(4, tMs);
  // slow fill/draw cycle: pump tops the tank up, household draws it down
  const level = 62 + 24 * wave(tMs, 46, 0.8) + 3 * noise(5, tMs);

  return {
    turb: Math.max(0, turb),
    tds: Math.max(0, tds),
    ph: Math.min(14, Math.max(0, ph)),
    temp,
    level: Math.min(100, Math.max(0, level)),
    score: scoreFrom({ turb, tds, ph, temp }),
  };
}
