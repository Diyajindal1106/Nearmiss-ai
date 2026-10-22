export const PRIORITY_LABEL = { urgent: "Urgent", high: "High", medium: "Medium", low: "Low" };
export const STATUS_LABEL = { open: "Reported", in_progress: "In Progress", resolved: "Resolved" };

export function timeAgo(iso) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

export const fullDate = (iso) =>
  new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

export const pct = (x) => `${Math.round(x * 100)}%`;
