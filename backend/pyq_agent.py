"""
PYQ Agent (LangGraph node)

Looks up pyqs.json for the resolved subject, optionally narrowed by
semester and exam type. Falls back to TF-IDF semantic search when
nothing matches on filters.
"""
from data_loader import store
from state import AgentState


def pyq_node(state: AgentState) -> dict:
    subject = state.get("resolved_subject")
    results = store.find_pyqs(
        subject,
        semester=state.get("semester"),
        exam_type=state.get("exam_type"),
    )
    method = "metadata"

    if not results:
        query = state.get("subject_query") or state.get("user_query", "")
        results = store.semantic_search_pyqs(query)
        method = "semantic" if results else "none"

    resources = [
        {
            "type": "pyq",
            "id": r.get("pyq_id"),
            "title": f"{r.get('subject_name')} — {r.get('exam_type')}",
            "subject": r.get("subject_name"),
            "semester": r.get("semester"),
            "exam_type": r.get("exam_type"),
            "url": r.get("file_path"),
            "academic_batch": r.get("academic_batch"),
            "score": r.get("score"),
        }
        for r in results
    ]

    if resources:
        lead = "Found these previous year papers:" if method == "metadata" else "No exact match, but these look related:"
        lines = [lead] + [
            f"- **{r['subject']}** · {r['exam_type']}" + (f" · Sem {r['semester']}" if r.get("semester") else "")
            for r in resources
        ]
        reply = "\n".join(lines)
    else:
        reply = f"I couldn't find previous year papers for {subject or state.get('subject_query') or 'that subject'} in the catalog yet."

    trail = state.get("agent_trail", []) + ["pyq"]
    return {"resources": resources, "search_method": method, "reply": reply, "agent_trail": trail}
