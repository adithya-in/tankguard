/* Data shapes the tank-side firmware actually serves (firmware/m1_tank.ino).
   The webapp stays strictly inside what GET /data provides — nothing invented. */

/** Exactly the JSON of GET /data on the tank unit. */
export interface TankFrame {
  /** 0–100 composite, firmware formula: 0.40·turb + 0.25·tds + 0.25·ph + 0.10·temp */
  score: number;
  /** 0–100 water level (ultrasonic) */
  level: number;
  ph: number;
  turb: number;
  tds: number;
  temp: number;
}

export type ChannelKey = "turb" | "tds" | "ph" | "temp" | "level";

export type LogKey = ChannelKey | "score";

export interface Point {
  /** bucket timestamp, Unix ms */
  t: number;
  v: number;
}

/** State bands match the H1 TFT firmware's scoreColor(): ≥70 green, ≥40 yellow, <40 red. */
export type TankState = "good" | "watch" | "attention";

export type SourceKind = "device" | "demo" | "down";
