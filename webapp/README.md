# TankGuard — Web Dashboard

The browser twin of the H1 home display: one page that answers **"is the water
safe?"** first (TankScore + state), backs it up with the five parameter
readings, and charts whatever history it can honestly show. React + Vite +
TypeScript, no UI kit, no chart library — every trace is hand-rolled SVG.

```
npm install
npm run dev        # http://localhost:5173 — falls into the labelled demo feed
npm run build      # static bundle in dist/
npm run preview    # serve the built bundle locally
```

## Where the data comes from

The page talks to the tank-side firmware's real API (`firmware/m1_tank/`):
`GET /data` → `{"score","level","ph","turb","tds","temp"}`, polled every 5 s
(the firmware's own `SAMPLE_MS`), 1500 ms timeout (H1's `http.setTimeout`).

Probe order — first one that answers wins:

| # | Candidate | When |
|---|---|---|
| 1 | `?api=<base>` | pinned override — e.g. `?api=192.168.1.42` |
| 2 | same-origin | the normal case: the tank unit serves this page itself |
| 3 | `http://192.168.4.1` | the tank unit's AP-mode gateway (`TankGuard-Tank`) |

If nothing answers, the page switches to a **labelled demo feed** (seeded, and
run through the firmware's own scoring formula) and keeps re-probing for a
device about once a minute.

| URL | Effect |
|---|---|
| `?demo=1` | force the demo feed |
| `?demo=0` | deny the demo: with no device, the page shows a retry state |
| `?api=…` | probe only that base (demo denied unless `?demo=1`) |

While a device link drops, the last real frame stays on screen with its age —
never blanked, never replaced by fake data.

## Honesty rules the page enforces on itself

- **Session log, not device history.** The firmware stores no history, so the
  browser keeps its own log — 1 sample per minute per channel, 24 h cap, in
  `localStorage` — and labels it "session log" everywhere. Demo frames are
  never persisted; `clear log` wipes it.
- **Score bands match the H1 firmware** (`scoreColor()`): ≥70 good · ≥40 watch
  · <40 needs attention — the web and the TFT can never disagree.
- **The component strip is a display-only port** of the firmware's
  `scoreFrom()` weights (turbidity 40% · TDS 25% · pH 25% · temp 10%; level is
  monitored but not scored, exactly as the tank unit computes it). The number
  shown is always the device's own `score` field.
- **No pump UI.** The pump is controlled by the H1 home unit, which runs no
  server — its state is unobservable from a browser, so the page does not
  pretend to show it.

## Layout

Wordmark bar with the source chip (device / demo / link state) · **TankScore
panel** (numeral, state word, an 18-segment bar echoing the H1 dial, and the
weighted component strip) · **five reading cards** — Turbidity, TDS, pH,
Temperature, Level — each a tracked micro-label, tabular value + unit, and a
live trace (pressing a card opens that channel below) · **detail chart** with
1H/6H/ALL windows, hover or arrow-key crosshair, and min/avg/P95/max stats ·
footer with the data-source verdict.

## Serving it from the tank unit

`dist/` is fully static (~81 KB gzipped JS+CSS + Saira subsets) and needs no
build step on the device. The current `m1_tank.ino` serves a small inline
status page; serving this bundle from LittleFS (gzipped, with the ESP8266
responding at `/`) is a small firmware follow-up — until then, host `dist/`
anywhere static (or run the dev server) and point it at the unit with `?api=`.

## Verification (2026-10-30)

`npm run lint` clean · `npm run build` green · zero horizontal overflow at
320/390/768/900/1020/1440 · interaction probe green across card selection,
window tabs, hover/keyboard crosshair · device mode proven against a mock
`/data` (chip, 5 s polling, persistence across reload, clear log) · down and
demo states render honestly. Dev rasters in `webapp/.review/` (not committed).
