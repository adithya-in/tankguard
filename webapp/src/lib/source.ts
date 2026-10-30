import { useCallback, useEffect, useRef, useState } from "react";
import { demoFrameAt } from "./demo";
import type { SourceKind, TankFrame } from "./types";

/* Where the page's data comes from, and the honesty around it.

   Probe order (first /data that answers wins):
     1. ?api=<base>          — pinned override, demo denied unless ?demo=1
     2. same-origin          — the normal case: the tank unit serves this page
     3. http://192.168.4.1   — the tank unit's AP-mode gateway
   If nothing answers: a labelled DEMO feed (unless denied), which keeps
   re-probing for a device about once a minute. While a device link drops, the
   last real frame stays on screen with its age — never blanked, never faked.

   Timings match the firmware world: poll every 5 s (SAMPLE_MS), fetch timeout
   1500 ms (H1's http.setTimeout). */

const POLL_MS = 5_000;
const FETCH_TIMEOUT_MS = 1_500;
const FAILS_BEFORE_REPROBE = 3;
const DEMO_REPROBE_TICKS = 12; // ~1 min between background device probes in demo

type Mode = "probing" | "device" | "demo" | "down";

interface Params {
  api: string | null;
  demo: "1" | "0" | null;
}

function readParams(): Params {
  const sp = new URLSearchParams(location.search);
  const rawApi = sp.get("api");
  let api: string | null = null;
  if (rawApi) {
    const trimmed = rawApi.trim().replace(/\/+$/, "");
    api = /^https?:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;
  }
  const rawDemo = sp.get("demo");
  return { api, demo: rawDemo === "1" || rawDemo === "0" ? rawDemo : null };
}

function candidates(p: Params): string[] {
  if (p.api) return [p.api];
  const out: string[] = [];
  if (location.protocol !== "file:") out.push(""); // same-origin: served by the device
  out.push("http://192.168.4.1"); // AP-mode gateway of TankGuard-Tank
  return out;
}

function isFrame(x: unknown): x is TankFrame {
  if (typeof x !== "object" || x === null) return false;
  const f = x as Record<string, unknown>;
  return ["score", "level", "ph", "turb", "tds", "temp"].every((k) => typeof f[k] === "number" && Number.isFinite(f[k]));
}

async function fetchFrame(base: string): Promise<TankFrame> {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(`${base}/data`, { signal: ac.signal, cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json: unknown = await res.json();
    if (!isFrame(json)) throw new Error("not a TankGuard /data frame");
    return json;
  } finally {
    clearTimeout(timer);
  }
}

const labelFor = (base: string): string =>
  base === "" ? "tank unit · this network" : `tank unit · ${base.replace(/^https?:\/\//, "")}`;

/* Read once at load — the URL does not change during the page's life. */
const PARAMS: Params = readParams();
const CANDIDATES: string[] = candidates(PARAMS);
const DEMO_DENIED: boolean = PARAMS.demo === "0" || (PARAMS.api !== null && PARAMS.demo !== "1");

export interface SourceState {
  frame: TankFrame | null;
  kind: SourceKind;
  base: string;
  label: string;
  linkOk: boolean;
  lastOkAt: number | null;
  retry: () => void;
}

export function useTankSource(): SourceState {
  const modeRef = useRef<Mode>("probing");
  const baseRef = useRef<string>("");
  const failsRef = useRef(0);
  const tickCountRef = useRef(0);
  const retryRef = useRef<() => void>(() => {});

  const [state, setState] = useState<SourceState>(() => ({
    frame: null,
    kind: "down",
    base: "",
    label: "probing for the tank unit",
    linkOk: false,
    lastOkAt: null,
    retry: () => retryRef.current(),
  }));

  const demoDenied = DEMO_DENIED;

  const publish = useCallback((frame: TankFrame, kind: SourceKind, base: string, label: string): void => {
    setState((s) => ({ ...s, frame, kind, base, label, linkOk: true, lastOkAt: Date.now() }));
  }, []);

  const degrade = useCallback((label: string): void => {
    setState((s) => ({ ...s, kind: "down", base: "", label, linkOk: false }));
  }, []);

  useEffect(() => {
    let disposed = false;

    const probeAll = async (): Promise<{ base: string; frame: TankFrame } | null> => {
      for (const base of CANDIDATES) {
        try {
          const frame = await fetchFrame(base);
          return { base, frame };
        } catch {
          // try the next candidate
        }
      }
      return null;
    };

    const tick = async (): Promise<void> => {
      if (disposed) return;
      tickCountRef.current += 1;

      if (modeRef.current === "device") {
        try {
          const frame = await fetchFrame(baseRef.current);
          failsRef.current = 0;
          publish(frame, "device", baseRef.current, labelFor(baseRef.current));
        } catch {
          failsRef.current += 1;
          if (failsRef.current >= FAILS_BEFORE_REPROBE) {
            modeRef.current = "probing";
            degrade("tank unit unreachable — re-probing");
          } else {
            setState((s) => ({ ...s, linkOk: false }));
          }
        }
        return;
      }

      if (modeRef.current === "demo") {
        publish(demoFrameAt(Date.now()), "demo", "", "demo feed — synthetic");
        if (tickCountRef.current % DEMO_REPROBE_TICKS === 0) {
          const found = await probeAll();
          if (found && !disposed) {
            baseRef.current = found.base;
            failsRef.current = 0;
            modeRef.current = "device";
            publish(found.frame, "device", found.base, labelFor(found.base));
          }
        }
        return;
      }

      // probing or down: look for the device, then fall back honestly
      const found = await probeAll();
      if (disposed) return;
      if (found) {
        baseRef.current = found.base;
        failsRef.current = 0;
        modeRef.current = "device";
        publish(found.frame, "device", found.base, labelFor(found.base));
        return;
      }
      if (!demoDenied) {
        modeRef.current = "demo";
        publish(demoFrameAt(Date.now()), "demo", "", "demo feed — synthetic");
        return;
      }
      modeRef.current = "down";
      degrade("no tank unit answered on this network");
    };

    retryRef.current = () => {
      modeRef.current = "probing";
      failsRef.current = 0;
      void tick();
    };

    void tick();
    const id = window.setInterval(() => void tick(), POLL_MS);
    return () => {
      disposed = true;
      window.clearInterval(id);
    };
  }, [publish, degrade, demoDenied]);

  return state;
}
