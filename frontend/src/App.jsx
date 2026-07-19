import React, { useEffect, useRef, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import MessageBubble from "./components/MessageBubble.jsx";
import TypingIndicator from "./components/TypingIndicator.jsx";
import { sendChatMessage, fetchSubjects } from "./api.js";

const SUGGESTIONS = [
  { eyebrow: "Notes", text: "Show me notes for DBMS" },
  { eyebrow: "PYQ", text: "PYQs for Machine Learning, final semester" },
  { eyebrow: "Guidance", text: "Help me prepare for my DAA exam in a week" },
  { eyebrow: "Resources", text: "Recommend resources for Deep Learning" },
];

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeAgents, setActiveAgents] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [subjects, setSubjects] = useState([]);

  const scrollRef = useRef(null);
  const sessionId = useRef(`session-${Date.now()}`);

  useEffect(() => {
    fetchSubjects().then((s) => setSubjects(s.subjects || []));
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  async function handleSend(overrideText) {
    const text = (overrideText ?? input).trim();
    if (!text || loading) return;

    const userMsg = { role: "user", content: text };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await sendChatMessage({
        message: text,
        sessionId: sessionId.current,
        history: nextMessages.map((m) => ({ role: m.role, content: m.content })),
      });
      setActiveAgents(res.agent_trail || []);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.reply,
          agentTrail: res.agent_trail,
          resources: res.resources,
        },
      ]);
    } catch (e) {
      setError(e.message || "Something went wrong reaching AcadEase AI.");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="app-shell">
      <Sidebar
        open={sidebarOpen}
        activeAgents={activeAgents}
        subjects={subjects}
        onSubjectClick={(s) => handleSend(`Show me notes for ${s}`)}
      />

      <div className="main">
        <div className="topbar">
          <button className="icon-btn" style={{ color: "var(--maroon-800)" }} onClick={() => setSidebarOpen((o) => !o)}>
            ☰
          </button>
          <strong style={{ fontFamily: "var(--font-display)", color: "var(--maroon-800)" }}>AcadEase AI</strong>
        </div>

        <div className="chat-scroll" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="empty-state">
              <h1>Ask AcadEase AI</h1>
              <p>
                Your centralized academic hub — notes, previous year papers, study plans,
                and trusted external resources, one question away.
              </p>
              <div className="suggestion-grid">
                {SUGGESTIONS.map((s) => (
                  <button key={s.text} className="suggestion-card" onClick={() => handleSend(s.text)}>
                    <span className="eyebrow">{s.eyebrow}</span>
                    {s.text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} content={m.content} agentTrail={m.agentTrail} resources={m.resources} />
          ))}

          {loading && <TypingIndicator />}
          {error && <div className="error-banner">{error}</div>}
        </div>

        <div className="composer">
          <div className="composer-inner">
            <textarea
              rows={1}
              placeholder="Ask for notes, PYQs, a study plan, or resource recommendations…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button className="send-btn" onClick={() => handleSend()} disabled={loading || !input.trim()}>
              ➤
            </button>
          </div>
          <div className="composer-hint">AcadEase AI can be wrong about unverified resources — always cross-check before an exam.</div>
        </div>
      </div>
    </div>
  );
}
