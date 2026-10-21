import { Link } from "react-router-dom";
import { ArrowRight, Camera, Bot, Layers, ClipboardCheck, Footprints, Construction, Droplets, Zap, ShieldAlert } from "lucide-react";
import { Logo } from "../components/ui.jsx";

const steps = [
  { icon: Camera, title: "Report", text: "Snap a photo, describe the hazard and pick the block. No more scattered chats and calls." },
  { icon: Bot, title: "Classify", text: "A pretrained vision-language model suggests a category. You confirm or change it." },
  { icon: Layers, title: "Group & prioritise", text: "Similar reports at the same place are linked, and an explainable 0–100 score ranks the queue." },
  { icon: ClipboardCheck, title: "Review & resolve", text: "Admins assign an owner, update status, and record how it was fixed." },
];

const hazards = [
  { icon: Construction, title: "Pothole / damaged road", text: "Gates, parking, internal roads" },
  { icon: Footprints, title: "Broken steps / stairs", text: "Entrances and staircases" },
  { icon: Droplets, title: "Slippery / wet floor", text: "Corridors, lobbies, canteens" },
  { icon: Zap, title: "Exposed electrical wire", text: "Labs, panels, outlets" },
];

const sample = [
  ["Broken stair", "Block B entrance · 3 linked reports", "high"],
  ["Exposed wire", "Science Lab · needs human review", "urgent"],
  ["Pothole", "Main Gate · 2 linked reports", "medium"],
];

export default function Landing() {
  return (
    <div className="landing">
      <header className="topnav">
        <Logo />
        <nav>
          <a href="#how">How it works</a>
          <a href="#hazards">Hazards</a>
          <Link to="/dashboard" className="btn">Dashboard</Link>
        </nav>
      </header>

      <section className="hero">
        <div>
          <span className="eyebrow">Campus safety · Early-stage prototype</span>
          <h1>Detect danger before disaster.</h1>
          <p className="tagline">“Don’t wait for an accident to fix a problem.”</p>
          <p className="lead">
            Loose steps, wet floors, potholes and exposed wires get reported on WhatsApp, calls and paper —
            then forgotten. NearMiss AI turns those scattered reports into one location-aware priority queue
            that admins can explain, assign and close.
          </p>
          <div className="cta">
            <Link to="/report" className="btn btn-primary btn-lg">Report a Hazard <ArrowRight size={18} /></Link>
            <Link to="/dashboard" className="btn btn-lg">View Safety Dashboard</Link>
          </div>
        </div>
        <div className="hero-card" aria-label="Illustrative example queue">
          <div className="hero-card-head"><ShieldAlert size={16} /> Hazard queue <em>illustrative example</em></div>
          {sample.map(([t, s, p]) => (
            <div className="hero-row" key={t}>
              <div><b>{t}</b><div className="muted small">{s}</div></div>
              <span className={`badge prio-${p}`}>{p[0].toUpperCase() + p.slice(1)}</span>
            </div>
          ))}
          <p className="muted small">Concept data. The live app shows only what has been reported to it.</p>
        </div>
      </section>

      <section id="how" className="section">
        <h2>From report to resolution — with humans in control</h2>
        <div className="grid4">
          {steps.map(({ icon: Icon, title, text }, i) => (
            <div className="card step" key={title}>
              <span className="step-n">{i + 1}</span>
              <Icon size={22} className="accent" />
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="hazards" className="section alt">
        <h2>Four hazard categories to start</h2>
        <div className="grid4">
          {hazards.map(({ icon: Icon, title, text }) => (
            <div className="card" key={title}><Icon size={22} className="accent" /><h3>{title}</h3><p>{text}</p></div>
          ))}
        </div>
      </section>

      <footer className="foot">
        <p>
          NearMiss AI is an ideation-stage prototype. It has not been validated with real users and has not been
          shown to prevent accidents. AI output is a suggestion that requires human verification; risk scores are a
          prioritisation aid, not a prediction.
        </p>
        <p className="muted small">Code Alpha Ideathon · Divyanshi Sharma &amp; Diya</p>
      </footer>
    </div>
  );
}
