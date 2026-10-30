import { CHANNELS } from "./channels";
import type { LogKey, Point, TankFrame } from "./types";

/* Session log — the browser's own record of what the tank unit reported.
   The device stores no history (firmware/m1_tank serves only the live frame),
   so the webapp keeps one sample per minute per channel, capped at 24 h, in
   localStorage. It is labelled "session log" on screen and never presented as
   device-stored history. Demo frames are never persisted. */

const STORAGE_KEY = "tankguard.log.v1";
export const BUCKET_MS = 60_000;
export const CAP_BUCKETS = 1440; // 24 h of 1-minute buckets

type LogData = Record<LogKey, Point[]>;

const emptyLog = (): LogData => ({
  score: [],
  turb: [],
  tds: [],
  ph: [],
  temp: [],
  level: [],
});

function validShape(raw: unknown): raw is LogData {
  if (typeof raw !== "object" || raw === null) return false;
  const rec = raw as Record<string, unknown>;
  return (
    Array.isArray(rec.score) &&
    CHANNELS.every((c) => Array.isArray(rec[c.key])) &&
    Object.keys(rec).length === CHANNELS.length + 1
  );
}

function load(): LogData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyLog();
    const parsed: unknown = JSON.parse(raw);
    if (!validShape(parsed)) return emptyLog();
    // drop anything malformed inside the arrays
    const out = emptyLog();
    (Object.keys(out) as LogKey[]).forEach((k) => {
      out[k] = (parsed[k] as unknown[]).filter(
        (p): p is Point =>
          typeof p === "object" && p !== null && typeof (p as Point).t === "number" && typeof (p as Point).v === "number",
      );
    });
    return out;
  } catch {
    return emptyLog();
  }
}

export class SessionLog {
  private data: LogData;
  private dirty = false;
  private readonly persist: boolean;

  constructor(persist: boolean) {
    this.persist = persist;
    this.data = persist ? load() : emptyLog();
  }

  /** Record a frame into its minute bucket; latest frame in a bucket wins. */
  append(f: TankFrame, ts: number): void {
    const bucket = Math.floor(ts / BUCKET_MS) * BUCKET_MS;
    const put = (key: LogKey, v: number): void => {
      const arr = this.data[key];
      const last = arr[arr.length - 1];
      if (last && last.t === bucket) {
        last.v = v;
      } else {
        arr.push({ t: bucket, v });
      }
      const cutoff = bucket - CAP_BUCKETS * BUCKET_MS;
      while (arr.length && arr[0].t < cutoff) arr.shift();
    };
    put("score", f.score);
    for (const c of CHANNELS) put(c.key, c.value(f));
    this.dirty = true;
  }

  /** series for a key, optionally limited to the last `minutes` (0 = all). */
  window(key: LogKey, minutes = 0): Point[] {
    const arr = this.data[key];
    if (!minutes) return arr;
    const cutoff = Date.now() - minutes * 60_000;
    const idx = arr.findIndex((p) => p.t >= cutoff);
    if (idx === -1) return [];
    return arr.slice(idx);
  }

  /** how long this key has been logged, in minutes */
  coverage(key: LogKey): number {
    const arr = this.data[key];
    if (arr.length < 2) return 0;
    return (arr[arr.length - 1].t - arr[0].t) / 60_000;
  }

  hasData(key: LogKey): boolean {
    return this.data[key].length > 0;
  }

  /** wipe the log (and storage, when persistent) */
  clear(): void {
    this.data = emptyLog();
    this.dirty = true;
    this.flush();
    if (this.persist) {
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch {
        // best-effort by design
      }
    }
  }

  /** persist at most once per appended bucket — call after append batches */
  flush(): void {
    if (!this.persist || !this.dirty) return;
    this.dirty = false;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.data));
    } catch {
      // storage full or unavailable — the session log is best-effort by design
    }
  }
}
