import { useEffect, useRef, useState } from "react";
import { fmtClock, fmtDayClock, fmtTip, fmtValue, stats } from "../lib/fmt";
import type { Channel } from "../lib/channels";
import type { Point } from "../lib/types";

const PAD = { top: 16, right: 14, bottom: 26, left: 46 };
const H = 240;

interface Props {
  channel: Channel;
  series: Point[];
  /** 0 = everything logged */
  windowMin: number;
}

/**
 * Detail chart for the selected channel: the browser's session log (1 sample
 * per minute, up to 24 h — the device itself keeps no history). Real pixel
 * width via ResizeObserver so the axis type and hairline grid stay true; hover
 * or arrow keys drive a crosshair; the last tick reads "now".
 */
export function DetailChart({ channel, series, windowMin }: Props): React.JSX.Element {
  const frame = useRef<HTMLDivElement | null>(null);
  const [w, setW] = useState(680);
  const [hover, setHover] = useState<number | null>(null);

  // the observed root renders in every state (empty or plotted), so the
  // observer always attaches and the svg is sized to the real panel width
  useEffect(() => {
    const el = frame.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const cw = entries[0]?.contentRect.width ?? 0;
      if (cw > 0) setW(Math.round(cw));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const n = series.length;
  const innerW = Math.max(120, w - PAD.left - PAD.right);
  const innerH = H - PAD.top - PAD.bottom;

  const lo0 = n ? Math.min(...series.map((p) => p.v)) : 0;
  const hi0 = n ? Math.max(...series.map((p) => p.v)) : 1;
  const pad = (hi0 - lo0) * 0.12 || Math.max(0.5, Math.abs(hi0) * 0.02);
  const lo = lo0 - pad;
  const hi = hi0 + pad;
  const span = hi - lo || 1;
  const t0 = n ? series[0].t : 0;
  const t1 = n ? series[n - 1].t : 1;
  const tspan = t1 - t0 || 1;

  const px = (t: number): number => PAD.left + ((t - t0) / tspan) * innerW;
  const py = (v: number): number => PAD.top + innerH - ((v - lo) / span) * innerH;

  let cur = "";
  for (let i = 0; i < n; i++) cur += `${i === 0 ? "M" : "L"}${px(series[i].t).toFixed(1)} ${py(series[i].v).toFixed(1)} `;
  cur = cur.trim();
  const areaPath = n > 1 ? `${cur} L${px(t1).toFixed(1)} ${PAD.top + innerH} L${PAD.left} ${PAD.top + innerH} Z` : "";

  const s = stats(series);
  const domainTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => lo + span * f);
  const xTickIdx = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.min(n - 1, Math.round(f * (n - 1))));

  const pickAt = (clientX: number): void => {
    const el = frame.current?.querySelector("svg");
    if (!el || !n) return;
    const r = el.getBoundingClientRect();
    const rel = ((clientX - r.left) / r.width) * w - PAD.left;
    const f = rel / innerW;
    const tGuess = t0 + f * tspan;
    // nearest point by time (buckets are 1 min apart, so this is exact enough)
    let best = 0;
    let bestD = Infinity;
    for (let i = 0; i < n; i++) {
      const d = Math.abs(series[i].t - tGuess);
      if (d < bestD) {
        bestD = d;
        best = i;
      }
    }
    setHover(best);
  };

  const active = hover !== null && hover >= 0 && hover < n ? hover : null;
  const tipLeft = active === null ? 0 : Math.min(Math.max(px(series[active].t), 66), Math.max(66, w - 66));
  const tipFlip = active !== null && px(series[active].t) > w - 170;
  const point = active === null ? null : series[active];

  const xLabel = (t: number, last: boolean): string => {
    if (last) return "now";
    return tspan > 6 * 3_600_000 ? fmtDayClock(t) : fmtClock(t);
  };

  const aria =
    `${channel.label} session log over the last ${Math.round(tspan / 60_000)} minutes. ` +
    `Minimum ${fmtValue(s.min, channel.dp)} ${channel.unit}, average ${fmtValue(s.avg, channel.dp)}, maximum ${fmtValue(s.max, channel.dp)}.`;

  return (
    <div className="chart" ref={frame}>
      {n < 2 ? (
        <div className="chart-empty">
          <strong>Not enough samples yet.</strong>
          <span>
            The session log takes a minute per point — the trace appears as the tank unit keeps reporting
            {windowMin ? ` (showing the last ${windowMin >= 60 ? `${Math.round(windowMin / 60)} h` : `${windowMin} min`})` : ""}.
          </span>
        </div>
      ) : (
        <>
          <div className="chart-plot" style={{ height: H }}>
        <svg
          width={w}
          height={H}
          role="img"
          aria-label={aria}
          tabIndex={0}
          className="chart-svg"
          onPointerMove={(e) => pickAt(e.clientX)}
          onPointerLeave={() => setHover(null)}
          onFocus={() => setHover((h) => h ?? n - 1)}
          onBlur={() => setHover(null)}
          onKeyDown={(e) => {
            if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
              e.preventDefault();
              setHover((h) => {
                const base = h ?? n - 1;
                const next = e.key === "ArrowLeft" ? base - 1 : base + 1;
                return Math.min(n - 1, Math.max(0, next));
              });
            } else if (e.key === "Escape") {
              setHover(null);
            }
          }}
        >
          <defs>
            <linearGradient id={`cg-${channel.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={channel.hue} stopOpacity="0.2" />
              <stop offset="100%" stopColor={channel.hue} stopOpacity="0.01" />
            </linearGradient>
          </defs>

          {domainTicks.map((v, i) => (
            <g key={`g${i}`}>
              <line
                x1={PAD.left}
                x2={PAD.left + innerW}
                y1={py(v)}
                y2={py(v)}
                className={i === 0 ? "grid-base" : "grid-line"}
              />
              <text x={PAD.left - 10} y={py(v) + 3.5} className="axis-y">
                {fmtValue(v, channel.dp === 0 ? 0 : 1)}
              </text>
            </g>
          ))}

          <line
            x1={PAD.left}
            x2={PAD.left + innerW}
            y1={py(s.avg)}
            y2={py(s.avg)}
            className="avg-line"
            stroke={channel.hue}
          />

          {areaPath && <path d={areaPath} fill={`url(#cg-${channel.key})`} />}
          {cur && <path d={cur} className="series-cur" stroke={channel.hue} />}

          {xTickIdx.map((idx, i) => (
            <text
              key={`x${i}`}
              x={Math.min(PAD.left + innerW, Math.max(PAD.left, px(series[idx].t)))}
              y={H - 6}
              className="axis-x"
              textAnchor={i === 0 ? "start" : i === xTickIdx.length - 1 ? "end" : "middle"}
            >
              {xLabel(series[idx].t, i === xTickIdx.length - 1)}
            </text>
          ))}

          {active !== null && point && (
            <g className="cross">
              <line x1={px(point.t)} x2={px(point.t)} y1={PAD.top} y2={PAD.top + innerH} />
              <circle cx={px(point.t)} cy={py(point.v)} r="4" fill={channel.hue} stroke="#fff" strokeWidth="2" />
            </g>
          )}
        </svg>

        {active !== null && point && (
          <div className={`tip${tipFlip ? " flip" : ""}`} style={{ left: tipLeft }}>
            <div className="tip-time">{fmtTip(point.t)}</div>
            <div className="tip-val">
              {fmtValue(point.v, channel.dp)} <span>{channel.unit}</span>
            </div>
          </div>
        )}
      </div>

      <dl className="chart-stats">
        <div>
          <dt>Min</dt>
          <dd>{fmtValue(s.min, channel.dp)}</dd>
        </div>
        <div>
          <dt>Avg</dt>
          <dd>{fmtValue(s.avg, channel.dp)}</dd>
        </div>
        <div>
          <dt>P95</dt>
          <dd>{fmtValue(s.p95, channel.dp)}</dd>
        </div>
        <div>
          <dt>Max</dt>
          <dd>{fmtValue(s.max, channel.dp)}</dd>
        </div>
        <div className="unit-cell">
          <dt>Unit</dt>
          <dd>{channel.unit || "—"}</dd>
        </div>
        <div>
          <dt>Points</dt>
          <dd>{n}</dd>
        </div>
      </dl>
        </>
      )}
    </div>
  );
}
