/* Formatting helpers — grouped digits, tabular-friendly, no unit logic. */

export const fmtValue = (v: number, dp: number): string =>
  v.toLocaleString("en-GB", { minimumFractionDigits: dp, maximumFractionDigits: dp });

export function fmtAgo(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 2) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 6) return m % 60 ? `${h} h ${m % 60} min ago` : `${h} h ago`;
  return `${Math.round(m / 60)} h ago`;
}

export function fmtSpan(min: number): string {
  if (min < 1) return "under a minute";
  if (min < 60) return `${Math.round(min)} min`;
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  if (h < 24) return m ? `${h} h ${m} min` : `${h} h`;
  return `${Math.round(min / 60)} h`;
}

export function fmtClock(ts: number): string {
  return new Date(ts).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export function fmtDayClock(ts: number): string {
  const d = new Date(ts);
  return `${d.toLocaleDateString("en-GB", { weekday: "short" })} ${d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
}

export function fmtTip(ts: number): string {
  return new Date(ts).toLocaleString("en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" });
}

export function stats(series: Array<{ v: number }>): { min: number; max: number; avg: number; p95: number } {
  if (!series.length) return { min: 0, max: 0, avg: 0, p95: 0 };
  const vs = series.map((p) => p.v).sort((a, b) => a - b);
  const sum = vs.reduce((s, v) => s + v, 0);
  return {
    min: vs[0],
    max: vs[vs.length - 1],
    avg: sum / vs.length,
    p95: vs[Math.min(vs.length - 1, Math.floor(vs.length * 0.95))],
  };
}
