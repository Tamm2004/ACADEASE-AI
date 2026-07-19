const API_BASE = import.meta.env.VITE_API_URL;

export async function sendChatMessage({ message, sessionId, history }) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, history }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export async function fetchSubjects() {
  const res = await fetch(`${API_BASE}/api/subjects`);
  if (!res.ok) return { subjects: [] };
  return res.json();
}
