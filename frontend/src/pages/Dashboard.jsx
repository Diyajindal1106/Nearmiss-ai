import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, FileText, Flame, Link2, Search } from "lucide-react";
import { api } from "../api.js";
import { useConfig } from "../ConfigContext.jsx";
import { Empty, ErrorState, Loading, DemoTag, PriorityBadge, StatusBadge } from "../components/ui.jsx";
import { PRIORITY_LABEL, timeAgo } from "../format.js";

function Stat({ icon: Icon, label, value, tone }) {
  return (
    <div className={`card stat ${tone}`}>
      <Icon size={20} />
      <div className="stat-v">{value}</div>
      <div className="stat-l">{label}</div>
    </div>
  );
}

function Bars({ data, labels, colors }) {
  const max = Math.max(1, ...Object.values(data));
  return (
    <ul className="bars">
      {Object.entries(data).map(([k, v]) => (
        <li key={k}>
          <span className="bars-l">{labels[k]}</span>
          <div className="bar"><span style={{ width: `${(v / max) * 100}%`, background: colors?.[k] }} /></div>
          <span className="num">{v}</span>
        </li>
      ))}
    </ul>
  );
}

const PRIO_COLOR = { urgent: "#dc2626", high: "#ea580c", medium: "#d97706", low: "#64748b" };

export default function Dashboard() {
  const { config } = useConfig();
  const [stats, setStats] = useState(null);
  const [reports, setReports] = useState(null);
  const [error, setError] = useState(null);
  const [f, setF] = useState({ search: "", status: "", category: "", priority: "", sort: "priority" });
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));

  const load = useCallback(() => {
    setError(null);
    Promise.all([api.stats(), api.reports(f)])
      .then(([s, r]) => { setStats(s); setReports(r); })
      .catch((e) => setError(e.message));
  }, [f]);

  useEffect(() => {
    const t = setTimeout(load, f.search ? 250 : 0); // debounce typing
    return () => clearTimeout(t);
  }, [load, f.search]);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!stats || !reports) return <Loading label="Loading dashboard…" />;

  const catLabels = Object.fromEntries(Object.entries(config.categories).map(([k, v]) => [k, v.label]));
  const bLabel = (b) => config.buildings[b]?.label || b;
  const filtered = Object.entries(f).some(([k, v]) => k !== "sort" && v);

  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Safety dashboard</h1><p className="muted">Every figure below is computed from the reports in the database.</p></div>
        <Link to="/report" className="btn btn-primary">Report a hazard</Link>
      </div>

      {stats.demo_count > 0 && (
        <div className="notice">
          {stats.demo_count} of {stats.total} records are <b>illustrative sample data</b>, not real incidents. Reset with <code>python -m app.seed --reset</code>.
        </div>
      )}

      <div className="grid4">
        <Stat icon={FileText} label="Total reported" value={stats.total} tone="" />
        <Stat icon={AlertTriangle} label="Open / unresolved" value={stats.unresolved} tone="warn" />
        <Stat icon={Flame} label="Urgent or high priority" value={stats.urgent_high} tone="danger" />
        <Stat icon={CheckCircle2} label="Resolved" value={stats.resolved} tone="ok" />
      </div>

      <div className="grid3">
        <div className="card"><h3>Priority of unresolved</h3>
          <Bars data={stats.by_priority} labels={PRIORITY_LABEL} colors={PRIO_COLOR} /></div>
        <div className="card"><h3>Hazard categories (all reports)</h3>
          <Bars data={stats.by_category} labels={catLabels} /></div>
        <div className="card"><h3>Linked report groups</h3>
          {stats.groups.length === 0 ? <p className="muted small">No groups yet. A group forms when 2+ reports share a block and category.</p> : (
            <ul className="groups">
              {stats.groups.map((g) => (
                <li key={`${g.building}-${g.category}`}>
                  <Link2 size={14} /> <b>{g.size}</b> reports · {catLabels[g.category]} · {bLabel(g.building)}
                  <div className="muted small">{g.open_count} still open · rule: {g.rule}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="card">
        <div className="toolbar">
          <label className="search"><Search size={16} /><input placeholder="Search description, location, assignee…" value={f.search} onChange={set("search")} aria-label="Search reports" /></label>
          <select value={f.status} onChange={set("status")} aria-label="Filter by status">
            <option value="">All statuses</option><option value="open">Open</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option>
          </select>
          <select value={f.category} onChange={set("category")} aria-label="Filter by category">
            <option value="">All categories</option>
            {Object.entries(catLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select value={f.priority} onChange={set("priority")} aria-label="Filter by priority">
            <option value="">All priorities</option>
            {Object.entries(PRIORITY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select value={f.sort} onChange={set("sort")} aria-label="Sort">
            <option value="priority">Sort: priority</option><option value="newest">Newest</option><option value="oldest">Oldest</option><option value="severity">Severity</option>
          </select>
        </div>

        {reports.length === 0 ? (
          <Empty title={filtered ? "No reports match these filters" : "No hazard reports yet"}>
            {filtered ? "Try clearing a filter." : <>Be the first: <Link to="/report">report a hazard</Link>.</>}
          </Empty>
        ) : (
          <div className="table-wrap">
            <table className="list">
              <thead><tr><th>Hazard</th><th>Location</th><th>Priority</th><th>Score</th><th>Related</th><th>Status</th><th>Reported</th></tr></thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <Link to={`/reports/${r.id}`} className="rowlink"><b>#{r.id} {catLabels[r.category]}</b></Link>
                      {r.is_demo && <> <DemoTag /></>}
                      <div className="muted small clamp">{r.description}</div>
                    </td>
                    <td>{bLabel(r.building)}<div className="muted small">{r.location_details}</div></td>
                    <td><PriorityBadge level={r.priority} overridden={r.priority_source === "admin_override"} /></td>
                    <td className="num">{r.score.toFixed(0)}</td>
                    <td className="num">{r.related_count ? <span className="chip"><Link2 size={12} /> {r.related_count}</span> : "—"}</td>
                    <td><StatusBadge status={r.status} /></td>
                    <td className="muted small">{timeAgo(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
