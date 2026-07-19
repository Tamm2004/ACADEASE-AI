import React from "react";

const AGENTS = [
  { key: "router", label: "Router Agent" },
  { key: "notes", label: "Notes Agent" },
  { key: "pyq", label: "PYQ Agent" },
  { key: "guidance", label: "Guidance Agent" },
  { key: "recommender", label: "Recommender Agent" },
];

function Crest() {
  return (
    <svg className="crest" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="24" cy="24" r="22" fill="#C79A3B" opacity="0.15" />
      <circle cx="24" cy="24" r="18" stroke="#DDBB63" strokeWidth="1.4" />
      <path d="M24 10 L30 17 L24 24 L18 17 Z" fill="#DDBB63" />
      <path d="M14 30 Q24 22 34 30" stroke="#DDBB63" strokeWidth="1.6" fill="none" />
      <text x="24" y="40" textAnchor="middle" fontSize="7" fill="#DDBB63" fontFamily="Fraunces, serif">
        GNDU
      </text>
    </svg>
  );
}

export default function Sidebar({ open, activeAgents, subjects, onSubjectClick }) {
  return (
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <div className="brand-row">
        <Crest />
        <div>
          <div className="brand-name">AcadEase AI</div>
        </div>
      </div>
      <div className="brand-sub">GNDU · Academic Assistant</div>

      <div className="sidebar-section-title">Agent Pipeline</div>
      <div className="agent-rail">
        {AGENTS.map((a) => (
          <div key={a.key} className={`agent-chip ${activeAgents.includes(a.key) ? "active" : ""}`}>
            <span className="dot" />
            {a.label}
          </div>
        ))}
      </div>

      <div className="sidebar-section-title">Subjects on file ({subjects.length})</div>
      <div className="subject-list">
        {subjects.map((s) => (
          <button key={s} className="subject-chip" onClick={() => onSubjectClick(s)}>
            {s}
          </button>
        ))}
      </div>

      <div className="sidebar-footer">
        Centralizing notes, previous year papers, and study guidance in one place —
        no more hunting through WhatsApp groups and Drive links.
      </div>
    </aside>
  );
}
