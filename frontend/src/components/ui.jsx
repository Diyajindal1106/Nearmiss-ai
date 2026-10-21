import { ShieldAlert } from "lucide-react";
import { PRIORITY_LABEL, STATUS_LABEL } from "../format.js";

export function Logo({ light = false }) {
  return (
    <span className={`logo ${light ? "logo-light" : ""}`}>
      <span className="logo-mark"><ShieldAlert size={18} strokeWidth={2.4} /></span>
      <span>NearMiss <b>AI</b></span>
    </span>
  );
}

export const PriorityBadge = ({ level, overridden }) => (
  <span className={`badge prio-${level}`} title={overridden ? "Set by an administrator" : "Computed from score"}>
    {PRIORITY_LABEL[level]}{overridden ? " ✎" : ""}
  </span>
);

export const StatusBadge = ({ status }) => (
  <span className={`badge st-${status}`}>{STATUS_LABEL[status]}</span>
);

export const DemoTag = () => (
  <span className="badge demo" title="Illustrative sample record, not a real incident">Sample data</span>
);

export function Loading({ label = "Loading…" }) {
  return <div className="state" role="status"><span className="spinner" aria-hidden /> {label}</div>;
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="state error" role="alert">
      <strong>Something went wrong.</strong>
      <p>{message}</p>
      {onRetry && <button className="btn" onClick={onRetry}>Try again</button>}
    </div>
  );
}

export const Empty = ({ title, children }) => (
  <div className="state"><strong>{title}</strong><p>{children}</p></div>
);
