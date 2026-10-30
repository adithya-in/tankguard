import type { TankFrame, TankState } from "./types";

/* Port of scoreFrom() in firmware/m1_tank/m1_tank.ino — kept line-for-line so
   the browser can break the score into components exactly the way the device
   computes it. The device's own /data "score" is always what gets displayed;
   this port is used for the component strip and the demo feed only. */

export const SCORE_WEIGHTS = { turb: 0.4, tds: 0.25, ph: 0.25, temp: 0.1 } as const;

const clamp = (v: number, lo: number, hi: number): number => Math.min(hi, Math.max(lo, v));

export interface ScoreComponents {
  /** 0–100 sub-score per parameter, before weighting */
  turb: number;
  tds: number;
  ph: number;
  temp: number;
}

export function scoreComponents(f: Pick<TankFrame, "turb" | "tds" | "ph" | "temp">): ScoreComponents {
  const sTurb = clamp(100 - (f.turb - 5) * (100 / 45), 0, 100);
  const sTds = clamp(100 - (f.tds - 300) * (100 / 700), 0, 100);
  const sPh = clamp(100 - Math.abs(f.ph - 7) * 40, 0, 100);
  const tdev = Math.max(0, Math.abs(f.temp - 25) - 5);
  const sTemp = clamp(100 - tdev * 4, 0, 100);
  return { turb: sTurb, tds: sTds, ph: sPh, temp: sTemp };
}

export function scoreFrom(f: Pick<TankFrame, "turb" | "tds" | "ph" | "temp">): number {
  const c = scoreComponents(f);
  return SCORE_WEIGHTS.turb * c.turb + SCORE_WEIGHTS.tds * c.tds + SCORE_WEIGHTS.ph * c.ph + SCORE_WEIGHTS.temp * c.temp;
}

/** H1 TFT bands: ≥70 green · ≥40 yellow · <40 red. */
export function stateFor(score: number): TankState {
  if (score >= 70) return "good";
  if (score >= 40) return "watch";
  return "attention";
}

export const STATE_META: Record<TankState, { word: string; hue: string; headline: string }> = {
  good: {
    word: "GOOD",
    hue: "#0E9F6E",
    headline: "Water reads healthy — no action needed.",
  },
  watch: {
    word: "WATCH",
    hue: "#C97A08",
    headline: "Water is holding but drifting — keep an eye on it.",
  },
  attention: {
    word: "NEEDS ATTENTION",
    hue: "#D93A2B",
    headline: "Quality has dropped — check the tank, not just the dashboard.",
  },
};
