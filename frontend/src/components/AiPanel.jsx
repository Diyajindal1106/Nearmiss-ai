import { Bot, AlertTriangle, HelpCircle } from "lucide-react";
import { pct } from "../format.js";

/** Shows a stored or fresh CLIP analysis. Never invents values: it only renders what the API returned. */
export default function AiPanel({ analysis, categories, selected, onUse, compact = false }) {
  if (!analysis) return null;
  const { status } = analysis;
  const max = Math.max(0.0001, ...(analysis.scores || []).map((s) => s.relative_share));
  return (
    <section className={`ai-panel ai-${status}`} aria-live="polite">
      <header>
        <Bot size={18} />
        <strong>AI suggestion — human verification required</strong>
      </header>

      {status === "unavailable" && (
        <p className="ai-msg warn">
          <AlertTriangle size={16} /> AI analysis was unavailable, so no suggestion was made. Please choose the
          category manually. <span className="muted">({analysis.reason})</span>
        </p>
      )}

      {status === "uncertain" && (
        <p className="ai-msg">
          <HelpCircle size={16} /> <b>Uncertain — manual review required.</b> {analysis.reason}
        </p>
      )}

      {status === "ok" && (
        <div className="ai-top">
          <div>
            <div className="muted small">Suggested category</div>
            <div className="ai-suggest">{analysis.suggested_label}</div>
          </div>
          {onUse && (
            <button type="button" className={`btn ${selected === analysis.suggested_category ? "btn-ok" : "btn-primary"}`}
              onClick={() => onUse(analysis.suggested_category)}>
              {selected === analysis.suggested_category ? "Confirmed ✓" : "Confirm suggestion"}
            </button>
          )}
        </div>
      )}

      {analysis.scores?.length > 0 && (
        <table className="scores">
          <thead>
            <tr><th>Candidate description</th><th title="Raw CLIP image–text cosine similarity">Similarity</th><th>Relative share*</th></tr>
          </thead>
          <tbody>
            {analysis.scores.map((s) => (
              <tr key={s.category} className={s.category === analysis.suggested_category ? "top" : ""}>
                <td>{categories?.[s.category]?.label || s.label}</td>
                <td className="num">{s.cosine_similarity.toFixed(3)}</td>
                <td>
                  <div className="bar"><span style={{ width: `${(s.relative_share / max) * 100}%` }} /></div>
                  <span className="num small">{pct(s.relative_share)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {!compact && analysis.score_note && <p className="muted small">* {analysis.score_note}</p>}
      {analysis.quality?.warnings?.length > 0 && (
        <p className="ai-msg warn small"><AlertTriangle size={14} /> {analysis.quality.warnings.join(" ")}</p>
      )}
      {analysis.model && <p className="muted small">Model: {analysis.model} (zero-shot, not trained on campus data)</p>}
    </section>
  );
}
