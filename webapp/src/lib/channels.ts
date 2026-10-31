import type { ChannelKey, TankFrame } from "./types";

export interface Channel {
  key: ChannelKey;
  label: string;
  short: string;
  unit: string;
  /** decimals the firmware itself prints for this field */
  dp: number;
  hue: string;
  /** one plain-language line: why this number matters */
  why: string;
  value: (f: TankFrame) => number;
}

export const CHANNELS: Channel[] = [
  {
    key: "turb",
    label: "Turbidity",
    short: "Turb",
    unit: "NTU",
    dp: 1,
    hue: "#E4572E",
    why: "Floating particles and biofilm fragments — the strongest sign of sludge in the water.",
    value: (f) => f.turb,
  },
  {
    key: "tds",
    label: "TDS",
    short: "TDS",
    unit: "ppm",
    dp: 0,
    hue: "#1B7FD4",
    why: "Dissolved solids leaching from settled debris. India drinking norm tops near 500 ppm.",
    value: (f) => f.tds,
  },
  {
    key: "ph",
    label: "pH",
    short: "pH",
    unit: "",
    dp: 2,
    hue: "#7A5AF8",
    why: "Acidity balance. Drifting pH points to algal or rotting organic activity.",
    value: (f) => f.ph,
  },
  {
    key: "temp",
    label: "Temperature",
    short: "Temp",
    unit: "°C",
    dp: 1,
    hue: "#C97A08",
    why: "Warm water grows microbes faster; also compensates the other probes.",
    value: (f) => f.temp,
  },
  {
    key: "level",
    label: "Water level",
    short: "Level",
    unit: "%",
    dp: 0,
    hue: "#0E9F6E",
    why: "How much water is in the tank — and whether a refill or drain just happened.",
    value: (f) => f.level,
  },
];

export const CHANNEL_MAP: Record<ChannelKey, Channel> = Object.fromEntries(
  CHANNELS.map((c) => [c.key, c]),
) as Record<ChannelKey, Channel>;
