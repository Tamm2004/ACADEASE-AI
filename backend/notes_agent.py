"""
Notes Agent (LangGraph node)

Looks up notes.json for the resolved subject. Falls back to TF-IDF
semantic search over titles/descriptions/tags if there's no exact
subject match — real subject naming here isn't perfectly consistent
across files, so this catches near-misses.
"""
from data_loader import store
from state import AgentState


def notes_node(state: AgentState) -> dict:
    subject = state.get("resolved_subject")
    results = store.find_notes(subject)
    method = "metadata"

    if not results:
        query = state.get("subject_query") or state.get("user_query", "")
        results = store.semantic_search_notes(query)
        method = "semantic" if results else "none"

    resources = [
        {
            "type": "note",
            "id": r.get("note_id"),
            "title": r.get("title"),
            "subject": r.get("subject_name"),
            "description": r.get("description"),
            "url": r.get("file_path"),
            "source": r.get("source"),
            "score": r.get("score"),
        }
        for r in results
    ]

    if resources:
        lead = "Here's what I found:" if method == "metadata" else "No exact match, but these look related:"
        lines = [lead] + [f"- **{r['title']}** ({r['subject']})" for r in resources]
        reply = "\n".join(lines)
    else:
        reply = f"I couldn't find notes for {subject or state.get('subject_query') or 'that subject'} in the catalog yet."

    trail = state.get("agent_trail", []) + ["notes"]
    return {"resources": resources, "search_method": method, "reply": reply, "agent_trail": trail}
