import { STATE_META, SCORE_WEIGHTS } from "../lib/score";
import type { ScoreComponents } from "../lib/score";
import type { TankState } from "../lib/types";
import { fmtSpan, fmtValue } from "../lib/fmt";

const SEGS = 18; // echoes the 18-segment dial on the H1 home display

interface Props {
  score: number;
  state: TankState;
  components: ScoreComponents;
  /** minutes of score history behind the trend line */
  logSpanMin: number;
  firstScore: number | null;
}

const COMP_ROWS: Array<{ key: keyof ScoreComponents; label: string; weight: number }> = [
  { key: "turb", label: "Turbidity", weight: SCORE_WEIGHTS.turb },
  { key: "tds", label: "TDS", weight: SCORE_WEIGHTS.tds },
  { key: "ph", label: "pH", weight: SCORE_WEIGHTS.ph },
  { key: "temp", label: "Temperature", weight: SCORE_WEIGHTS.temp },
];

/**
 * The verdict: TankScore first (the number that answers "is the water safe?"),
 * its state word in the H1 firmware's bands, an 18-segment bar that mirrors the
 * home display's dial, and the firmware's own weighting made visible.
 */
export function ScorePanel({ score, state, components, logSpanMin, firstScore }: Props): React.JSX.Element {
  const meta = STATE_META[state];
  const filled = Math.round((Math.min(100, Math.max(0, score)) / 100) * SEGS);
  const delta = firstScore !== null && logSpanMin >= 30 ? score - firstScore : null;

  return (
    <section className="panel score" aria-labelledby="score-title" style={{ "--state": meta.hue } as React.CSSProperties}>
      <div className="score-main">
        <p className="kicker" id="score-title">
          Tank score
        </p>
        <div className="score-figure">
          <span className="score-num">{fmtValue(Math.round(score), 0)}</span>
          <span className="score-state" data-state={state}>
            {meta.word}
          </span>
        </div>
        <div
          className="segbar"
          role="img"
          aria-label={`TankScore ${Math.round(score)} of 100 — ${meta.word.toLowerCase()}`}
        >
          {Array.from({ length: SEGS }, (_, i) => (
            <span key={i} className={i < filled ? "on" : ""} />
          ))}
        </div>
        <p className="score-headline">{meta.headline}</p>
        {delta !== null && (
          <p className="score-trend" data-dir={delta >= 0 ? "up" : "down"}>
            {delta >= 0 ? "up" : "down"} {Math.abs(delta).toFixed(1)} pts since logging started ({fmtSpan(logSpanMin)})
          </p>
        )}
      </div>

      <div className="score-side">
        <p className="score-side-title">What drives the score</p>
        <ul className="comp-list">
          {COMP_ROWS.map((row) => {
            const v = Math.min(100, Math.max(0, components[row.key]));
            return (
              <li key={row.key}>
                <span className="comp-label">{row.label}</span>
                <span className="comp-bar" aria-hidden="true">
                  <span style={{ width: `${v}%` }} />
                </span>
                <span className="comp-val">{fmtValue(Math.round(v), 0)}</span>
                <span className="comp-weight">{Math.round(row.weight * 100)}%</span>
              </li>
            );
          })}
        </ul>
        <p className="comp-note">Firmware weights — level is monitored but not scored, exactly as the tank unit computes it.</p>
      </div>
    </section>
  );
}
