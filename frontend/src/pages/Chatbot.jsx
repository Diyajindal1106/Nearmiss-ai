import { useEffect, useRef, useState } from "react";
import { Bot, Send, Sparkles, AlertCircle, CheckCircle, HelpCircle } from "lucide-react";
import { api } from "../api.js";

const SUGGESTIONS = [
  "How should I handle an exposed electrical wire hazard?",
  "What is the recommended response for a chemical or water spill?",
  "How does NearMiss AI calculate the risk priority score?",
  "When should an incident status be moved to Resolved?",
];

export default function Chatbot() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hello! I am your NearMiss AI Safety Assistant. Ask me any questions about hazard identification, risk assessment, or safety reporting procedures.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [configured, setConfigured] = useState(null);
  const [configMsg, setConfigMsg] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    api.chatStatus()
      .then((res) => {
        setConfigured(res.configured);
        if (!res.configured) {
          setConfigMsg(
            "Gemini API key is not configured. Set the GEMINI_API_KEY environment variable in your backend environment to enable live AI responses."
          );
        }
      })
      .catch(() => {
        setConfigured(false);
        setConfigMsg("Could not connect to the NearMiss AI backend service.");
      });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(textToSend) {
    const text = (textToSend || input).trim();
    if (!text || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);

    try {
      const res = await api.chat(text);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: res.reply,
          isWarning: res.status !== "ok",
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Request failed: ${err.message}`,
          isWarning: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e) {
    e.preventDefault();
    send();
  }

  return (
    <div className="page narrow">
      <div className="page-head">
        <div>
          <h1>Safety Assistant</h1>
          <p className="muted">
            Interactive guidance on campus safety, hazard triage, and NearMiss AI incident protocols.
          </p>
        </div>
        <div>
          {configured === true && (
            <span className="badge prio-low" style={{ background: "#dcfce7", color: "#166534" }}>
              <CheckCircle size={12} style={{ display: "inline", verticalAlign: "-2px", marginRight: 4 }} />
              Gemini Active
            </span>
          )}
          {configured === false && (
            <span className="badge prio-high">
              <AlertCircle size={12} style={{ display: "inline", verticalAlign: "-2px", marginRight: 4 }} />
              API Key Not Set
            </span>
          )}
        </div>
      </div>

      {configured === false && configMsg && (
        <div className="notice" style={{ borderLeft: "4px solid #ea580c" }}>
          <b>Configuration Notice:</b> {configMsg}
        </div>
      )}

      <div className="card chat-card">
        <div className="chat-window">
          {messages.map((m, idx) => (
            <div key={idx} className={`chat-row ${m.role}`}>
              {m.role === "assistant" && (
                <div className="chat-avatar">
                  <Bot size={18} />
                </div>
              )}
              <div className={`chat-bubble ${m.role} ${m.isWarning ? "warning" : ""}`}>
                <div style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="chat-row assistant">
              <div className="chat-avatar">
                <Bot size={18} />
              </div>
              <div className="chat-bubble assistant">
                <span className="spinner" /> Thinking…
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="chat-suggestions">
          <span className="small muted" style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <Sparkles size={14} /> Suggested questions:
          </span>
          <div className="chips-row">
            {SUGGESTIONS.map((s, idx) => (
              <button
                key={idx}
                type="button"
                className="chip-btn"
                onClick={() => send(s)}
                disabled={loading}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={onSubmit} className="chat-input-bar">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your safety question here…"
            disabled={loading}
            maxLength={1000}
          />
          <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
            <Send size={16} /> Send
          </button>
        </form>
      </div>
    </div>
  );
}
