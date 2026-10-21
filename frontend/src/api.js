// Thin fetch wrapper. In dev, Vite proxies /api to the backend. Set VITE_API_URL to override.
const BASE = import.meta.env.VITE_API_URL || "";

function message(detail, status) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => `${(d.loc || []).filter((x) => x !== "body").join(".") || "field"}: ${d.msg}`)
      .join("; ");
  }
  return `Request failed (${status})`;
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(BASE + path, options);
  } catch {
    throw new Error("Cannot reach the NearMiss AI backend. Is it running on port 8000?");
  }
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON body */
  }
  if (!res.ok) throw new Error(message(body && body.detail, res.status));
  return body;
}

const json = (method, data) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
});

export const api = {
  health: () => request("/api/health"),
  config: () => request("/api/config"),
  stats: () => request("/api/stats"),
  reports: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v));
    return request(`/api/reports?${q}`);
  },
  report: (id) => request(`/api/reports/${id}`),
  createReport: (data) => request("/api/reports", json("POST", data)),
  updateReport: (id, data) => request(`/api/reports/${id}`, json("PATCH", data)),
  analyze: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("/api/analyze", { method: "POST", body: fd });
  },
};
