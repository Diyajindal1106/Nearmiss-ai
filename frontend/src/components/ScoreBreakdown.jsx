import { Info } from "lucide-react";

const COLORS = ["#2563eb", "#7c3aed", "#0891b2"];

export default function ScoreBreakdown({ breakdown, score }) {
  return (
    <div className="score-card">
      <div className="score-head">
        <div className="score-num">{score.toFixed(1)}<span>/100</span></div>
        <div className="muted small">Priority score (prioritisation aid, not an accident prediction)</div>
      </div>
      <div className="stack" role="img" aria-label="Score composition">
        {breakdown.components.map((c, i) => (
          <span key={c.key} style={{ width: `${c.points}%`, background: COLORS[i] }} title={`${c.label}: ${c.points} pts`} />
        ))}
      </div>
      <table className="scores">
        <thead><tr><th>Factor</th><th>Input</th><th>× Weight</th><th>Points</th></tr></thead>
        <tbody>
          {breakdown.components.map((c, i) => (
            <tr key={c.key}>
              <td><span className="dot" style={{ background: COLORS[i] }} /> {c.label}<div className="muted small">{c.explanation}</div></td>
              <td className="num">{Math.round(c.normalized * 100)}%</td>
              <td className="num">{Math.round(c.weight * 100)}%</td>
              <td className="num"><b>{c.points.toFixed(1)}</b></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted small"><Info size={13} /> Formula: 100 × Σ(weight × normalised factor). Weights, caps and thresholds are illustrative defaults in <code>backend/app/config.py</code>.</p>
    </div>
  );
}
