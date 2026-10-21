import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, UploadCloud, X } from "lucide-react";
import { api } from "../api.js";
import { useConfig } from "../ConfigContext.jsx";
import AiPanel from "../components/AiPanel.jsx";

export default function ReportForm() {
  const { config } = useConfig();
  const nav = useNavigate();
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [fileError, setFileError] = useState(null);
  const [form, setForm] = useState({ description: "", building: "", location_details: "", category: "" });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);
  const set = (k) => (e) => setForm((p) => ({ ...p, [k]: e.target.value }));

  function clearImage() {
    setFile(null); setPreview(null); setAnalysis(null); setFileError(null);
    setForm((p) => ({ ...p, category: "" }));
    if (fileRef.current) fileRef.current.value = "";
  }

  async function onFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFileError(null); setAnalysis(null);
    if (!config.upload.types.includes(f.type)) return setFileError("Unsupported file type. Please choose a JPEG, PNG or WebP image.");
    if (f.size > config.upload.max_bytes) return setFileError(`Image is too large. Maximum size is ${config.upload.max_bytes / 1048576} MB.`);
    setFile(f); setPreview(URL.createObjectURL(f)); setAnalyzing(true);
    try {
      setAnalysis(await api.analyze(f));
    } catch (err) {
      // Backend unreachable or rejected the file: say so; do not invent a suggestion.
      setAnalysis({ status: "unavailable", reason: err.message, scores: [] });
    } finally {
      setAnalyzing(false);
    }
  }

  function validate() {
    const er = {};
    if (form.description.trim().length < 10) er.description = "Please describe the hazard (at least 10 characters).";
    if (!form.building) er.building = "Choose the building or block.";
    if (!form.category) er.category = "Choose a category (confirm the AI suggestion or pick one yourself).";
    return er;
  }

  async function submit(e) {
    e.preventDefault();
    const er = validate();
    setErrors(er); setSubmitError(null);
    if (Object.keys(er).length) return;
    setSubmitting(true);
    try {
      const body = { ...form, upload_id: analysis?.upload_id || null };
      const r = await api.createReport(body);
      nav(`/reports/${r.id}`, { state: { justSubmitted: true } });
    } catch (err) {
      setSubmitError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <div className="page narrow">
      <h1>Report a hazard</h1>
      <p className="muted">Add a photo for an AI-assisted category suggestion, then confirm it. You always have the final say.</p>

      <form onSubmit={submit} noValidate className="card form">
        <div className="field">
          <label>Photo <span className="muted">(optional, JPEG/PNG/WebP, max 5 MB)</span></label>
          {!preview ? (
            <label className="drop">
              <UploadCloud size={28} />
              <span><b>Choose an image</b> or drop it here</span>
              <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={onFile} />
            </label>
          ) : (
            <div className="preview">
              <img src={preview} alt="Selected hazard preview" />
              <button type="button" className="btn btn-icon" onClick={clearImage} aria-label="Remove image"><X size={16} /></button>
            </div>
          )}
          {fileError && <p className="err" role="alert">{fileError}</p>}
          {analyzing && <p className="muted"><Loader2 className="spin" size={16} /> Analysing image with CLIP (the first run loads the model and can take a while)…</p>}
          {file && !analyzing && (
            <AiPanel analysis={analysis} categories={config.categories} selected={form.category}
              onUse={(c) => setForm((p) => ({ ...p, category: c }))} />
          )}
        </div>

        <div className="field">
          <label htmlFor="cat">Hazard category *</label>
          <div className="cats" id="cat" role="radiogroup">
            {Object.entries(config.categories).map(([k, v]) => (
              <label key={k} className={`cat ${form.category === k ? "on" : ""}`}>
                <input type="radio" name="category" value={k} checked={form.category === k} onChange={set("category")} />
                {v.label}
                {analysis?.suggested_category === k && <em>AI suggested</em>}
              </label>
            ))}
          </div>
          {errors.category && <p className="err" role="alert">{errors.category}</p>}
        </div>

        <div className="field">
          <label htmlFor="desc">Description *</label>
          <textarea id="desc" rows={4} maxLength={1000} value={form.description} onChange={set("description")}
            placeholder="What is the hazard and why is it dangerous?" aria-invalid={!!errors.description} />
          {errors.description && <p className="err" role="alert">{errors.description}</p>}
        </div>

        <div className="row2">
          <div className="field">
            <label htmlFor="bld">Building / block *</label>
            <select id="bld" value={form.building} onChange={set("building")} aria-invalid={!!errors.building}>
              <option value="">Select…</option>
              {Object.entries(config.buildings).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
            {errors.building && <p className="err" role="alert">{errors.building}</p>}
          </div>
          <div className="field">
            <label htmlFor="loc">Location details <span className="muted">(optional)</span></label>
            <input id="loc" maxLength={200} value={form.location_details} onChange={set("location_details")} placeholder="e.g. 2nd-floor landing, left side" />
          </div>
        </div>

        {submitError && <p className="err box" role="alert">{submitError}</p>}
        <div className="actions">
          <button className="btn btn-primary btn-lg" disabled={submitting || analyzing}>
            {submitting ? "Submitting…" : "Submit report"}
          </button>
        </div>
      </form>
    </div>
  );
}
