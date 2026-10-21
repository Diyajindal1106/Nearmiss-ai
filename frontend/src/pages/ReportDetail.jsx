import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Link2 } from "lucide-react";
import { api } from "../api.js";
import { useConfig } from "../ConfigContext.jsx";
import AiPanel from "../components/AiPanel.jsx";
import ScoreBreakdown from "../components/ScoreBreakdown.jsx";
import { DemoTag, ErrorState, Loading, PriorityBadge, StatusBadge } from "../components/ui.jsx";
import { PRIORITY_LABEL, STATUS_LABEL, fullDate } from "../format.js";

const SOURCE = {
  ai_confirmed: "Reporter confirmed the AI suggestion",
  ai_overridden: "Reporter chose a different category than the AI suggested",
  manual: "Reporter chose the category manually (no usable AI suggestion)",
  admin_changed: "Changed by an administrator",
};

export default function ReportDetail() {
  const { id } = useParams();
  const { config } = useConfig();
  const { state } = useLocation();
  const [r, setR] = useState(null);
  const [error, setError] = useState(null);
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);

  const adopt = (data) => {
    setR(data);
    setDraft({
      category: data.category, status: data.status, severity: data.severity,
      priority_override: data.priority_source === "admin_override" ? data.priority : "auto",
      assignee: data.assignee || "", resolution_notes: data.resolution_notes || "",
    });
  };
  const load = useCallback(() => {
    setError(null);
    api.report(id).then(adopt).catch((e) => setError(e.message));
  }, [id]);
  useEffect(load, [load]);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!r) return <Loading label="Loading report…" />;

  const set = (k) => (e) => setDraft((p) => ({ ...p, [k]: k === "severity" ? Number(e.target.value) : e.target.value }));
  const dirty = JSON.stringify(draft) !== JSON.stringify({
    category: r.category, status: r.status, severity: r.severity,
    priority_override: r.priority_source === "admin_override" ? r.priority : "auto",
    assignee: r.assignee || "", resolution_notes: r.resolution_notes || "",
  });

  async function save(e) {
    e.preventDefault();
    setSaving(true); setSaveMsg(null);
    try {
      adopt(await api.updateReport(r.id, draft));
      setSaveMsg({ ok: true, text: "Saved." });
    } catch (err) {
      setSaveMsg({ ok: false, text: err.message });
    } finally {
      setSaving(false);
    }
  }

  const cat = (k) => config.categories[k]?.label || k;
  return (
    <div className="page">
      <Link to="/dashboard" className="back"><ArrowLeft size={16} /> Back to dashboard</Link>

      {state?.justSubmitted && (
        <div className="notice ok">
          <CheckCircle2 size={16} /> Report submitted. Priority score {r.score.toFixed(1)} ({PRIORITY_LABEL[r.computed_priority]})
          {r.related_count > 0 ? ` — linked with ${r.related_count} similar report(s) at this location.` : "."}
        </div>
      )}

      <div className="page-head">
        <div>
          <h1>#{r.id} · {cat(r.category)} {r.is_demo && <DemoTag />}</h1>
          <p className="muted">{config.buildings[r.building]?.label}{r.location_details ? ` · ${r.location_details}` : ""} · reported {fullDate(r.created_at)} · open for {r.age_days} d</p>
        </div>
        <div className="badges"><PriorityBadge level={r.priority} overridden={r.priority_source === "admin_override"} /><StatusBadge status={r.status} /></div>
      </div>

      <div className="detail-grid">
        <div className="col">
          <div className="card">
            {r.image_url && <img className="hero-img" src={r.image_url} alt="Submitted hazard" />}
            <h3>Description</h3>
            <p>{r.description}</p>
            <p className="muted small">Category provenance: {SOURCE[r.category_source]}.</p>
          </div>

          <div className="card">
            <h3>AI review</h3>
            {r.ai_result ? (
              <AiPanel analysis={r.ai_result} categories={config.categories} />
            ) : (
              <p className="muted">No image analysis was run for this report{r.is_demo ? " (sample record)" : ""}. Category was chosen by a person.</p>
            )}
          </div>

          <div className="card"><h3>Why this priority?</h3>
            <ScoreBreakdown breakdown={r.score_breakdown} score={r.score} />
            {r.priority_source === "admin_override" && (
              <p className="notice">An administrator set this to <b>{PRIORITY_LABEL[r.priority]}</b>; the computed level is <b>{PRIORITY_LABEL[r.computed_priority]}</b>.</p>
            )}
          </div>

          <div className="card">
            <h3><Link2 size={16} /> Related reports ({r.related.length})</h3>
            <p className="muted small">Linked by rule: same building/block + same confirmed category. Nothing is merged automatically.</p>
            {r.related.length === 0 ? <p className="muted">No other reports share this location and category.</p> : (
              <ul className="plain">
                {r.related.map((x) => (
                  <li key={x.id}>
                    <Link to={`/reports/${x.id}`}><b>#{x.id}</b></Link> <StatusBadge status={x.status} />
                    <div className="small">{x.description}</div>
                    <div className="muted small">
                      Shared: {config.buildings[r.building]?.label}, {cat(r.category)} · description word overlap {Math.round(x.description_similarity * 100)}%
                      {x.location_details_overlap ? " · similar spot details" : ""}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="col">
          <form className="card form" onSubmit={save}>
            <h3>Admin review</h3>
            <p className="muted small">Prototype: no login yet, so anyone with access to this page can edit. Changes are saved to SQLite and logged.</p>
            <div className="field"><label htmlFor="a-cat">Category</label>
              <select id="a-cat" value={draft.category} onChange={set("category")}>
                {Object.entries(config.categories).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select></div>
            <div className="row2">
              <div className="field"><label htmlFor="a-sev">Severity (1–5)</label>
                <select id="a-sev" value={draft.severity} onChange={set("severity")}>
                  {[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}
                </select></div>
              <div className="field"><label htmlFor="a-pri">Priority</label>
                <select id="a-pri" value={draft.priority_override} onChange={set("priority_override")}>
                  <option value="auto">Auto ({PRIORITY_LABEL[r.computed_priority]})</option>
                  {config.priority_overrides.map((p) => <option key={p} value={p}>{PRIORITY_LABEL[p]}</option>)}
                </select></div>
            </div>
            <div className="field"><label htmlFor="a-who">Assigned to</label>
              <input id="a-who" value={draft.assignee} onChange={set("assignee")} placeholder="Person or maintenance team" maxLength={120} /></div>
            <div className="field"><label htmlFor="a-st">Status</label>
              <select id="a-st" value={draft.status} onChange={set("status")}>
                {config.statuses.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
              </select></div>
            <div className="field"><label htmlFor="a-n">Resolution notes {draft.status === "resolved" && "*"}</label>
              <textarea id="a-n" rows={3} maxLength={2000} value={draft.resolution_notes} onChange={set("resolution_notes")} placeholder="What was done to fix it?" /></div>
            {saveMsg && <p className={saveMsg.ok ? "ok-text" : "err box"} role="status">{saveMsg.text}</p>}
            <button className="btn btn-primary" disabled={!dirty || saving}>{saving ? "Saving…" : "Save changes"}</button>
          </form>

          <div className="card">
            <h3>Status history</h3>
            <ol className="timeline">
              {[...r.history].reverse().map((h, i) => (
                <li key={i}>
                  <b>{h.field === "created" ? "Report created" : `${h.field.replace("_", " ")} changed`}</b>
                  {h.field !== "created" && <div className="small">{h.old_value ?? "—"} → {h.new_value ?? "—"}</div>}
                  {h.note && <div className="small">{h.note}</div>}
                  <div className="muted small">{fullDate(h.changed_at)} · {h.changed_by}</div>
                </li>
              ))}
            </ol>
            <p className="muted small">Last updated {fullDate(r.updated_at)}{r.resolved_at ? ` · resolved ${fullDate(r.resolved_at)}` : ""}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
