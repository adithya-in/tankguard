import { useEffect, useRef, useState } from "react";
import { DetailChart } from "./ui/DetailChart";
import { ParamIcon } from "./ui/ParamIcon";
import { ReadingCard } from "./ui/ReadingCard";
import { ScorePanel } from "./ui/ScorePanel";
import { CHANNELS, CHANNEL_MAP } from "./lib/channels";
import { demoFrameAt } from "./lib/demo";
import { fmtAgo } from "./lib/fmt";
import { SessionLog } from "./lib/history";
import { scoreComponents, stateFor } from "./lib/score";
import { useTankSource } from "./lib/source";
import type { ChannelKey } from "./lib/types";

const WINDOWS: Array<{ key: string; label: string; minutes: number }> = [
  { key: "1h", label: "1H", minutes: 60 },
  { key: "6h", label: "6H", minutes: 360 },
  { key: "all", label: "ALL", minutes: 0 },
];

/** 24 h of demo backfill so the demo feed charts like a lived-in device. */
const DEMO_BACKFILL_BUCKETS = 1440;

export function App(): React.JSX.Element {
  const source = useTankSource();
  const { frame, kind, base, label, linkOk, lastOkAt } = source;

  const [channel, setChannel] = useState<ChannelKey>("turb");
  const [winKey, setWinKey] = useState("1h");
  const [nowTick, setNowTick] = useState(() => Date.now());

  const [deviceLog] = useState(() => new SessionLog(true));
  const [demoLog] = useState(() => new SessionLog(false));

  // record frames: device frames persist, demo frames stay in memory
  useEffect(() => {
    if (!frame) return;
    if (kind === "device") {
      deviceLog.append(frame, Date.now());
      deviceLog.flush();
    } else if (kind === "demo") {
      demoLog.append(frame, Date.now());
    }
  }, [frame, kind, deviceLog, demoLog]);

  // one-time demo backfill (idempotent: buckets overwrite)
  const backfilled = useRef(false);
  useEffect(() => {
    if (backfilled.current) return;
    backfilled.current = true;
    const now = Date.now();
    for (let i = DEMO_BACKFILL_BUCKETS; i >= 0; i--) {
      const t = now - i * 60_000;
      demoLog.append(demoFrameAt(t), t);
    }
  }, [demoLog]);

  // 1 s heartbeat so "received Xs ago" stays true without re-rendering the source
  useEffect(() => {
    if (!frame) return;
    const id = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [frame]);

  const log = kind === "demo" ? demoLog : deviceLog;
  const ch = CHANNEL_MAP[channel];
  const win = WINDOWS.find((x) => x.key === winKey) ?? WINDOWS[0];
  const chartSeries = log.window(channel, win.minutes);
  const scoreSeries = log.window("score");

  const ageMs = lastOkAt ? nowTick - lastOkAt : null;
  const jsonHref = kind === "device" ? `${base}/data` : null;

  return (
    <div className="shell">
      <a className="skip" href="#readings">
        Skip to readings
      </a>

      <header className="topbar">
        <div className="brand">
          <span className="wordmark">TANKGUARD</span>
          <span className="rule" aria-hidden="true" />
          <span className="brand-sub">Tank monitor</span>
        </div>
        <div className="top-tools">
          {kind === "device" && (
            <span className={`chip chip-device${linkOk ? "" : " is-down"}`} title={label}>
              <span className="chip-dot" />
              {linkOk ? "Device" : "Link lost"}
            </span>
          )}
          {kind === "demo" && (
            <span className="chip chip-demo" title="No tank unit answered — showing a labelled synthetic feed">
              Demo feed
            </span>
          )}
          {kind === "down" && (
            <span className="chip chip-down" title={label}>
              No device
            </span>
          )}
          {frame && kind === "device" && ageMs !== null && <span className="age">{linkOk ? "received " : "last "}{fmtAgo(ageMs)}</span>}
          {frame && kind === "demo" && <span className="age">synthetic · re-probing for a device</span>}
          {kind === "down" && (
            <button type="button" className="link-btn" onClick={source.retry}>
              Retry
            </button>
          )}
        </div>
      </header>

      <main className="content">
        {frame ? (
          <ScorePanel
            score={frame.score}
            state={stateFor(frame.score)}
            components={scoreComponents(frame)}
            logSpanMin={log.coverage("score")}
            firstScore={scoreSeries[0]?.v ?? null}
          />
        ) : (
          <section className="panel panel-waiting" aria-live="polite">
            <p className="kicker">Tank score</p>
            <div className="waiting-figure">—</div>
            <p className="waiting-title">{label}.</p>
            <p className="waiting-note">
              The page probes this network and <span className="mono">192.168.4.1</span> every few seconds. Point it at a unit
              with <span className="mono">?api=&lt;ip&gt;</span>, or{" "}
              <button type="button" className="link-btn" onClick={source.retry}>
                retry now
              </button>
              .
            </p>
          </section>
        )}

        <section className="metrics" id="readings" aria-label="Parameter readings">
          {frame
            ? CHANNELS.map((c) => (
                <ReadingCard
                  key={c.key}
                  channel={c}
                  value={c.value(frame)}
                  series={log.window(c.key)}
                  spanMin={log.coverage(c.key)}
                  active={c.key === channel}
                  onSelect={() => setChannel(c.key)}
                />
              ))
            : CHANNELS.map((c) => (
                <div key={c.key} className="metric is-blank" style={{ "--hue": c.hue } as React.CSSProperties}>
                  <span className="metric-head">
                    <span className="metric-icon">
                      <ParamIcon param={c.key} size={15} />
                    </span>
                    <span className="metric-label">{c.label}</span>
                  </span>
                  <span className="metric-value">
                    <span className="metric-num">—</span>
                  </span>
                </div>
              ))}
        </section>

        <section className="panel panel-chart" aria-labelledby="chart-title">
          <header className="panel-head">
            <div className="panel-title">
              <h2 id="chart-title">{ch.label}</h2>
              <p className="panel-sub">{ch.why}</p>
              <p className="panel-source">
                {kind === "demo" ? "Demo feed · synthetic backfill" : "Session log · kept by this browser, the device stores no history"}
              </p>
            </div>
            <div className="seg" role="group" aria-label="Chart window">
              {WINDOWS.map((x) => (
                <button
                  key={x.key}
                  type="button"
                  className={`seg-btn${x.key === winKey ? " is-on" : ""}`}
                  aria-pressed={x.key === winKey}
                  onClick={() => setWinKey(x.key)}
                >
                  {x.label}
                </button>
              ))}
            </div>
          </header>
          <DetailChart key={`${channel}:${winKey}`} channel={ch} series={chartSeries} windowMin={win.minutes} />
        </section>
      </main>

      <footer className="foot">
        <span>
          {kind === "device" && (
            <>
              Data from the tank unit&apos;s <span className="mono">/data</span> endpoint
              {jsonHref && (
                <>
                  {" · "}
                  <a href={jsonHref}>raw JSON</a>
                </>
              )}
            </>
          )}
          {kind === "demo" && <>Demo feed — synthetic values run through the firmware&apos;s own scoring formula.</>}
          {kind === "down" && <>No device answered on this network.</>}
        </span>
        <span>
          Session log: this browser, 1 sample/min, 24 h cap ·{" "}
          <button
            type="button"
            className="link-btn tiny"
            onClick={() => {
              deviceLog.clear();
              setNowTick(Date.now());
            }}
          >
            clear log
          </button>
        </span>
        <span>Pump control lives on the home unit (H1) — not shown here.</span>
      </footer>
    </div>
  );
}
