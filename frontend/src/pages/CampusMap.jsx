import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useConfig } from "../ConfigContext.jsx";
import { Empty, ErrorState, Loading, PriorityBadge, StatusBadge } from "../components/ui.jsx";

const FILL = { urgent: "#fecaca", high: "#fed7aa", medium: "#fde68a", low: "#e2e8f0", none: "#dcfce7" };
const STROKE = { urgent: "#dc2626", high: "#ea580c", medium: "#d97706", low: "#64748b", none: "#16a34a" };

export default function CampusMap() {
  const { config } = useConfig();
  const [stats, setStats] = useState(null);
  const [reports, setReports] = useState(null);
  const [error, setError] = useState(null);
  const [sel, setSel] = useState(null);

  const load = () => {
    setError(null);
    Promise.all([api.stats(), api.reports({ sort: "priority" })])
      .then(([s, r]) => { setStats(s); setReports(r); })
      .catch((e) => setError(e.message));
  };
  useEffect(load, []);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!stats) return <Loading label="Loading campus view…" />;

  const here = reports.filter((r) => r.building === sel);
  return (
    <div className="page">
      <h1>Campus hazard map</h1>
      <p className="muted">Schematic layout for orientation only — not to scale and not GPS. Colour shows the highest-priority unresolved hazard in each block.</p>
      <div className="grid2">
        <div className="card">
          <svg viewBox="0 0 100 60" className="map" role="img" aria-label="Schematic campus map">
            <rect x="0" y="0" width="100" height="60" rx="2" fill="#f8fafc" />
            <path d="M2 40 H98 M50 2 V58" stroke="#cbd5e1" strokeWidth="1.2" strokeDasharray="2 1.5" />
            {Object.entries(config.buildings).map(([k, b]) => {
              const s = stats.by_building[k];
              const tone = s.unresolved ? s.top_priority : "none";
              return (
                <g key={k} onClick={() => setSel(k)} onKeyDown={(e) => e.key === "Enter" && setSel(k)} tabIndex={0}
                  role="button" aria-label={`${b.label}: ${s.unresolved} unresolved`} style={{ cursor: "pointer" }}>
                  <rect x={b.x} y={b.y} width={b.w} height={b.h} rx="1.5" fill={FILL[tone]}
                    stroke={sel === k ? "#0b1b33" : STROKE[tone]} strokeWidth={sel === k ? 1.1 : 0.6} />
                  <text x={b.x + b.w / 2} y={b.y + b.h / 2 - 0.5} textAnchor="middle" fontSize="2.6" fill="#0f172a" fontWeight="600">{b.label}</text>
                  <text x={b.x + b.w / 2} y={b.y + b.h / 2 + 3.2} textAnchor="middle" fontSize="2.4" fill="#334155">
                    {s.unresolved ? `${s.unresolved} open` : s.total ? "all resolved" : "no reports"}
                  </text>
                </g>
              );
            })}
          </svg>
          <div className="legend">
            {["urgent", "high", "medium", "low", "none"].map((t) => (
              <span key={t}><i style={{ background: FILL[t], borderColor: STROKE[t] }} />{t === "none" ? "No open hazards" : t[0].toUpperCase() + t.slice(1)}</span>
            ))}
          </div>
        </div>

        <div className="card">
          <h3>{sel ? config.buildings[sel].label : "Select a block"}</h3>
          {!sel ? <p className="muted">Click a block on the map to see its reports.</p>
            : here.length === 0 ? <Empty title="No reports here">Nothing has been reported for this block.</Empty> : (
              <ul className="plain">
                {here.map((r) => (
                  <li key={r.id}>
                    <Link to={`/reports/${r.id}`}><b>#{r.id} {config.categories[r.category].label}</b></Link>
                    <div className="muted small clamp">{r.description}</div>
                    <PriorityBadge level={r.priority} overridden={r.priority_source === "admin_override"} /> <StatusBadge status={r.status} />
                  </li>
                ))}
              </ul>
            )}
        </div>
      </div>
    </div>
  );
}
