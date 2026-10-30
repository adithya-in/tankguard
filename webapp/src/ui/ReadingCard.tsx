import { ParamIcon } from "./ParamIcon";
import { Sparkline } from "./Sparkline";
import { fmtSpan, fmtValue } from "../lib/fmt";
import type { Channel } from "../lib/channels";
import type { Point } from "../lib/types";

interface Props {
  channel: Channel;
  value: number;
  /** full session-log series for the sparkline */
  series: Point[];
  /** minutes of log behind the sparkline */
  spanMin: number;
  active: boolean;
  onSelect: () => void;
}

function Caret({ up }: { up: boolean }): React.JSX.Element {
  return (
    <svg viewBox="0 0 8 8" width="7" height="7" aria-hidden="true" focusable="false" className="caret">
      <path d={up ? "M4 1.4 7 6.4H1Z" : "M4 6.6 1 1.6h6Z"} fill="currentColor" />
    </svg>
  );
}

/**
 * One parameter reading — the unit the whole page is built around: tracked
 * micro-label, large tabular value with a small unit, live trace. The card is
 * also the selector for the detail chart below.
 */
export function ReadingCard({ channel, value, series, spanMin, active, onSelect }: Props): React.JSX.Element {
  const values = series.map((p) => p.v);
  const first = series[0]?.v;
  const up = first !== undefined ? value >= first : true;
  const delta = first !== undefined && first !== 0 && spanMin >= 10 ? ((value - first) / Math.abs(first)) * 100 : null;

  const aria = `${channel.label}: ${fmtValue(value, channel.dp)} ${channel.unit}${delta !== null ? `, ${up ? "up" : "down"} ${Math.abs(delta).toFixed(1)} percent since logging started` : ""}. Show ${channel.label} detail.`;

  return (
    <button
      type="button"
      className="metric"
      style={{ "--hue": channel.hue } as React.CSSProperties}
      aria-pressed={active}
      aria-label={aria}
      onClick={onSelect}
    >
      <span className="metric-rule" aria-hidden="true" />
      <span className="metric-head">
        <span className="metric-icon">
          <ParamIcon param={channel.key} size={15} />
        </span>
        <span className="metric-label">{channel.label}</span>
        {delta !== null ? (
          <span className="metric-delta" title={`Change since logging started (${fmtSpan(spanMin)})`}>
            <Caret up={up} />
            {Math.abs(delta).toFixed(1)}%
          </span>
        ) : (
          <span className="metric-delta is-muted" title="The session log needs a few more minutes before a change is meaningful">
            logging…
          </span>
        )}
      </span>

      <span className="metric-value">
        <span className="metric-num">{fmtValue(value, channel.dp)}</span>
        {channel.unit && <span className="metric-unit">{channel.unit}</span>}
      </span>

      <Sparkline values={values} hue={channel.hue} height={44} className="metric-spark" />
      <span className="metric-foot">{spanMin >= 1 ? `session log · ${fmtSpan(spanMin)}` : "session log · starting"}</span>
    </button>
  );
}
