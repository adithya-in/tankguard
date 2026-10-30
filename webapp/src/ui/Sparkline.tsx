import { useId } from "react";

interface Props {
  values: number[];
  hue: string;
  /** rendered height in px */
  height?: number;
  /** draw the live dot at the right edge */
  dot?: boolean;
  /** area wash under the line */
  area?: boolean;
  strokeWidth?: number;
  className?: string;
}

/**
 * The signature reading trace: a hairline path with a soft area wash and a live
 * dot. The path stretches to the frame (preserveAspectRatio none) while the
 * stroke stays at constant screen weight; the dot is DOM-positioned so it stays
 * a true circle at any frame width.
 */
export function Sparkline({ values, hue, height = 36, dot = true, area = true, strokeWidth = 1.6, className }: Props): React.JSX.Element {
  const uid = useId().replace(/:/g, "");
  const w = 100;
  const h = 36;
  const n = values.length;

  let lo = Infinity;
  let hi = -Infinity;
  for (const v of values) {
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) {
    lo = 0;
    hi = 1;
  }
  const pad = (hi - lo) * 0.12 || Math.max(0.5, Math.abs(hi) * 0.02);
  lo -= pad;
  hi += pad;
  const span = hi - lo || 1;

  const x = (i: number): number => (n <= 1 ? w / 2 : (i / (n - 1)) * w);
  const y = (v: number): number => h - ((v - lo) / span) * h;

  let line = "";
  for (let i = 0; i < n; i++) line += `${i === 0 ? "M" : "L"}${x(i).toFixed(2)} ${y(values[i]).toFixed(2)} `;
  const fill = `${line}L${w} ${h} L0 ${h} Z`;
  const last = values[n - 1] ?? 0;
  const lastPct = (y(last) / h) * 100;

  return (
    <div className={`spark${className ? ` ${className}` : ""}`} style={{ height }}>
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" width="100%" height={height} aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id={`sg-${uid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={hue} stopOpacity="0.24" />
            <stop offset="100%" stopColor={hue} stopOpacity="0.01" />
          </linearGradient>
        </defs>
        {area && n > 1 && <path d={fill} fill={`url(#sg-${uid})`} />}
        {n === 1 && <circle cx={x(0)} cy={y(values[0])} r="1.6" fill={hue} />}
        <path
          d={line}
          fill="none"
          stroke={hue}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      {dot && n > 0 && <span className="spark-dot" style={{ top: `calc(${lastPct}% - 2.5px)`, background: hue }} />}
    </div>
  );
}
