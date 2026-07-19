import React from "react";
import ResourceCard from "./ResourceCard.jsx";

const AGENT_DISPLAY = {
  router: "Router",
  notes: "Notes Agent",
  pyq: "PYQ Agent",
  guidance: "Guidance Agent",
  recommender: "Recommender Agent",
  general: "General",
};

function trailLabel(trail) {
  if (!trail || trail.length === 0) return null;
  // Router is implicit in every request; only show the specialist hop(s).
  const specialists = trail.filter((t) => t !== "router");
  const shown = specialists.length > 0 ? specialists : trail;
  return shown.map((t) => AGENT_DISPLAY[t] || t).join(" → ");
}

function renderText(text) {
  return text.split("\n").map((line, i) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/g).map((chunk, j) =>
      chunk.startsWith("**") && chunk.endsWith("**") ? (
        <strong key={j}>{chunk.slice(2, -2)}</strong>
      ) : (
        chunk
      )
    );
    return <p key={i}>{parts}</p>;
  });
}

export default function MessageBubble({ role, content, agentTrail, resources }) {
  const label = role === "assistant" ? trailLabel(agentTrail) : null;
  return (
    <div className={`msg-row ${role}`}>
      <div className="msg-bubble">
        {label && <span className="agent-tag">{label}</span>}
        {renderText(content)}
        {resources && resources.length > 0 && (
          <div className="resource-list">
            {resources.map((r, i) => (
              <ResourceCard key={r.id || i} item={r} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
