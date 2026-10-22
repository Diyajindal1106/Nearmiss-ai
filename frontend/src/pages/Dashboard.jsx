import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  FileText,
  Flame,
  Link2,
  Search,
  TrendingUp,
  X,
  ShieldAlert,
} from "lucide-react";
import { api } from "../api.js";
import { useConfig } from "../ConfigContext.jsx";
import {
  Empty,
  ErrorState,
  Loading,
  DemoTag,
  PriorityBadge,
  StatusBadge,
} from "../components/ui.jsx";
import { PRIORITY_LABEL, timeAgo } from "../format.js";

function Stat({ icon: Icon, label, value, tone, sub }) {
  return (
    <div className={`card stat ${tone}`}>
      <Icon size={20} />
      <div className="stat-v">{value}</div>
      <div className="stat-l">{label}</div>
      {sub && <div className="muted small">{sub}</div>}
    </div>
  );
}

function Bars({ data, labels, colors }) {
  const max = Math.max(1, ...Object.values(data));
  return (
    <ul className="bars">
      {Object.entries(data).map(([k, v]) => (
        <li key={k}>
          <span className="bars-l">{labels[k] || k}</span>
          <div className="bar">
            <span
              style={{
                width: `${(v / max) * 100}%`,
                background: colors?.[k] || "#2563eb",
              }}
            />
          </div>
          <span className="num">{v}</span>
        </li>
      ))}
    </ul>
  );
}

function TrendBars({ trend }) {
  if (!trend || trend.length === 0) {
    return <p className="muted small">No incident history recorded yet.</p>;
  }
  const max = Math.max(1, ...trend.map((t) => t.count));
  return (
    <ul className="bars">
      {trend.map((t) => (
        <li key={t.date}>
          <span className="bars-l small">{t.date}</span>
          <div className="bar">
            <span
              style={{
                width: `${(t.count / max) * 100}%`,
                background: "#2563eb",
              }}
            />
          </div>
          <span className="num">{t.count}</span>
        </li>
      ))}
    </ul>
  );
}

const PRIO_COLOR = {
  urgent: "#dc2626",
  high: "#ea580c",
  medium: "#d97706",
  low: "#64748b",
};

export default function Dashboard() {
  const { config } = useConfig();
  const [stats, setStats] = useState(null);
  const [reports, setReports] = useState(null);
  const [error, setError] = useState(null);
  const [f, setF] = useState({
    search: "",
    status: "",
    category: "",
    priority: "",
    sort: "priority",
  });
  const [newIncidentAlert, setNewIncidentAlert] = useState(null);

  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));

  const load = useCallback(() => {
    setError(null);
    Promise.all([api.stats(), api.reports(f)])
      .then(([s, r]) => {
        setStats(s);
        setReports(r);
      })
      .catch((e) => setError(e.message));
  }, [f]);

  useEffect(() => {
    const t = setTimeout(load, f.search ? 250 : 0);
    return () => clearTimeout(t);
  }, [load, f.search]);

  // Check for newly reported incidents and generate an in-app alert notification
  useEffect(() => {
    if (!reports || reports.length === 0) return;
    const maxId = Math.max(...reports.map((r) => r.id));
    const storedLastSeen = localStorage.getItem("nearmiss_last_seen_id");

    if (storedLastSeen === null) {
      localStorage.setItem("nearmiss_last_seen_id", String(maxId));
    } else {
      const lastId = parseInt(storedLastSeen, 10);
      const newItems = reports.filter((r) => r.id > lastId);
      if (newItems.length > 0) {
        setNewIncidentAlert({
          count: newItems.length,
          latest: newItems[0],
          maxId,
        });
      }
    }
  }, [reports]);

  function dismissAlert() {
    if (newIncidentAlert?.maxId) {
      localStorage.setItem("nearmiss_last_seen_id", String(newIncidentAlert.maxId));
    }
    setNewIncidentAlert(null);
  }

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!stats || !reports) return <Loading label="Loading dashboard…" />;

  const catLabels = Object.fromEntries(
    Object.entries(config.categories).map(([k, v]) => [k, v.label])
  );
  const bLabel = (b) => config.buildings[b]?.label || b;
  const filtered = Object.entries(f).some(([k, v]) => k !== "sort" && v);

  // Filter urgent unresolved hazards for active alerts banner
  const urgentReports = reports.filter(
    (r) => r.status !== "resolved" && r.priority === "urgent"
  );

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Safety Dashboard</h1>
          <p className="muted">
            Real-time hazard intelligence computed directly from incident reports.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.6rem" }}>
          <Link to="/chat" className="btn">
            Ask Safety AI
          </Link>
          <Link to="/report" className="btn btn-primary">
            Report a hazard
          </Link>
        </div>
      </div>

      {/* New Incident In-App Notification Alert */}
      {newIncidentAlert && (
        <div className="notice alert-notice" role="alert">
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <Bell size={18} className="spin-slow" />
            <span>
              <b>New Incident Alert:</b> Report #{newIncidentAlert.latest.id} (
              {catLabels[newIncidentAlert.latest.category] || newIncidentAlert.latest.category}) was
              submitted at {bLabel(newIncidentAlert.latest.building)}.
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Link to={`/reports/${newIncidentAlert.latest.id}`} className="btn btn-sm">
              View
            </Link>
            <button
              type="button"
              className="btn btn-icon btn-sm"
              onClick={dismissAlert}
              aria-label="Dismiss alert"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Critical / Urgent Hazard Banner */}
      {urgentReports.length > 0 && (
        <div className="notice danger-notice" role="alert">
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <ShieldAlert size={20} color="#dc2626" />
            <div>
              <b>Critical Hazard Warning:</b> {urgentReports.length} urgent incident
              {urgentReports.length > 1 ? "s require" : " requires"} immediate facilities action.
              {" "}
              {urgentReports.slice(0, 2).map((u) => (
                <Link
                  key={u.id}
                  to={`/reports/${u.id}`}
                  style={{ textDecoration: "underline", marginRight: 8 }}
                >
                  #{u.id} {bLabel(u.building)}
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {stats.demo_count > 0 && (
        <div className="notice">
          {stats.demo_count} of {stats.total} records are <b>illustrative sample data</b>. Reset with{" "}
          <code>python -m app.seed --reset</code>.
        </div>
      )}

      {/* Four Core Metric Cards */}
      <div className="grid4">
        <Stat
          icon={FileText}
          label="Total Incidents"
          value={stats.total}
          tone=""
          sub="All logged records"
        />
        <Stat
          icon={AlertTriangle}
          label="Open Incidents"
          value={stats.open}
          tone="warn"
          sub={`${stats.in_progress} in progress`}
        />
        <Stat
          icon={Flame}
          label="High-Priority Incidents"
          value={stats.urgent_high}
          tone="danger"
          sub="Urgent or high severity"
        />
        <Stat
          icon={CheckCircle2}
          label="Resolved Incidents"
          value={stats.resolved}
          tone="ok"
          sub="Fully mitigated"
        />
      </div>

      {/* Visual Analytics Grid */}
      <div className="grid4-charts">
        <div className="card">
          <h3>
            <Flame size={16} color="#ea580c" /> Priority of Unresolved
          </h3>
          <Bars data={stats.by_priority} labels={PRIORITY_LABEL} colors={PRIO_COLOR} />
        </div>

        <div className="card">
          <h3>
            <AlertTriangle size={16} color="#2563eb" /> Hazard Categories
          </h3>
          <Bars data={stats.by_category} labels={catLabels} />
        </div>

        <div className="card">
          <h3>
            <TrendingUp size={16} color="#15803d" /> Incident Trends (Recent)
          </h3>
          <TrendBars trend={stats.recent_trend} />
        </div>

        <div className="card">
          <h3>
            <Link2 size={16} /> Linked Hazard Groups
          </h3>
          {stats.groups.length === 0 ? (
            <p className="muted small">
              No groups yet. A group forms when 2+ reports share a block and category.
            </p>
          ) : (
            <ul className="groups">
              {stats.groups.map((g) => (
                <li key={`${g.building}-${g.category}`}>
                  <Link2 size={14} /> <b>{g.size}</b> reports · {catLabels[g.category]} ·{" "}
                  {bLabel(g.building)}
                  <div className="muted small">
                    {g.open_count} open · rule: {g.rule}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Filterable Incident List */}
      <div className="card">
        <div className="toolbar">
          <label className="search">
            <Search size={16} />
            <input
              placeholder="Search description, location, assignee…"
              value={f.search}
              onChange={set("search")}
              aria-label="Search reports"
            />
          </label>
          <select value={f.status} onChange={set("status")} aria-label="Filter by status">
            <option value="">All statuses</option>
            <option value="open">Reported (Open)</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
          </select>
          <select value={f.category} onChange={set("category")} aria-label="Filter by category">
            <option value="">All categories</option>
            {Object.entries(catLabels).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
          <select value={f.priority} onChange={set("priority")} aria-label="Filter by priority">
            <option value="">All priorities</option>
            {Object.entries(PRIORITY_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
          <select value={f.sort} onChange={set("sort")} aria-label="Sort">
            <option value="priority">Sort: priority</option>
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
            <option value="severity">Severity</option>
          </select>
        </div>

        {reports.length === 0 ? (
          <Empty
            title={filtered ? "No reports match these filters" : "No hazard reports yet"}
          >
            {filtered ? (
              "Try clearing a filter."
            ) : (
              <>
                Be the first: <Link to="/report">report a hazard</Link>.
              </>
            )}
          </Empty>
        ) : (
          <div className="table-wrap">
            <table className="list">
              <thead>
                <tr>
                  <th>Hazard</th>
                  <th>Location</th>
                  <th>Priority</th>
                  <th>Score</th>
                  <th>Related</th>
                  <th>Status</th>
                  <th>Reported</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <Link to={`/reports/${r.id}`} className="rowlink">
                        <b>
                          #{r.id} {catLabels[r.category]}
                        </b>
                      </Link>
                      {r.is_demo && <> <DemoTag /></>}
                      <div className="muted small clamp">{r.description}</div>
                    </td>
                    <td>
                      {bLabel(r.building)}
                      <div className="muted small">{r.location_details}</div>
                    </td>
                    <td>
                      <PriorityBadge
                        level={r.priority}
                        overridden={r.priority_source === "admin_override"}
                      />
                    </td>
                    <td className="num">{r.score.toFixed(0)}</td>
                    <td className="num">
                      {r.related_count ? (
                        <span className="chip">
                          <Link2 size={12} /> {r.related_count}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      <StatusBadge status={r.status} />
                    </td>
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
