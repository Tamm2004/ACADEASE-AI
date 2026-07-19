"""
Resource Recommender Agent (LangGraph node)

Runs standalone (intent == "recommendation") or as an automatic
fallback when Notes/PYQ nodes find nothing. Checks resources.json
(curated: YouTube playlists, books, websites, practice platforms)
first; if the subject isn't curated, asks Grok for well-known
resources and is explicit that those are AI-suggested.
"""
import logging

from data_loader import store
from llm_client import LLMError, grok_client
from state import AgentState

logger = logging.getLogger("acadease.recommender")

SYSTEM_PROMPT = """You are the Resource Recommender Agent inside AcadEase AI. The requested \
subject has no curated resources on file. Suggest well-known, genuinely useful external \
resources: YouTube channels/playlists, a couple of standard textbooks, and useful websites.

Respond with ONLY a JSON object, no prose, no markdown fences:
{
  "youtube": [{"channel": "", "playlist": "", "url": "", "language": ""}],
  "books": [{"title": "", "author": ""}],
  "websites": [{"title": "", "url": ""}]
}

Only include entries you're reasonably confident actually exist. Empty lists are fine — \
don't invent something you're not sure of. Leave "url" empty if you're not certain of it.
"""


def _to_resource_items(resources: dict) -> list[dict]:
    items = []
    for yt in resources.get("youtube", []):
        items.append({
            "type": "youtube",
            "title": yt.get("playlist") or yt.get("channel") or "YouTube resource",
            "description": yt.get("channel"),
            "url": yt.get("url"),
        })
    for book in resources.get("books", []):
        items.append({"type": "book", "title": book.get("title", ""), "description": book.get("author")})
    for site in resources.get("websites", []):
        items.append({"type": "website", "title": site.get("title", ""), "url": site.get("url")})
    for practice in resources.get("practice", []):
        items.append({"type": "practice", "title": practice.get("platform", ""), "url": practice.get("url")})
    return items


async def recommender_node(state: AgentState) -> dict:
    subject = state.get("resolved_subject")
    prior_reply = state.get("reply", "")

    curated = store.find_resources(subject) if subject else None
    is_curated = curated is not None

    if not is_curated and subject:
        convo = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Subject: {subject}"},
        ]
        try:
            curated = await grok_client.chat_json(convo, temperature=0.3, max_tokens=500) or {}
        except LLMError as e:
            logger.warning("Recommender LLM call failed: %s", e)
            curated = {}
    curated = curated or {}

    items = _to_resource_items(curated)

    if items:
        lead = (
            "Here are trusted resources for this subject:"
            if is_curated
            else "No notes/PYQs on file yet, so here are some well-known resources "
                 "(AI-suggested — worth a quick sanity check):"
        )
        lines = [lead] + [f"- **{i['title']}**" + (f" — {i['description']}" if i.get("description") else "") for i in items]
        reply_addition = "\n".join(lines)
    else:
        subj = subject or state.get("subject_query") or "that subject"
        reply_addition = f"I don't have notes, PYQs, or curated resources for {subj} yet."

    combined_reply = (prior_reply + "\n\n" + reply_addition).strip() if prior_reply else reply_addition

    trail = state.get("agent_trail", []) + ["recommender"]
    existing_resources = state.get("resources", [])
    return {
        "resources": existing_resources + items,
        "reply": combined_reply,
        "search_method": "curated" if is_curated else "llm_suggested",
        "agent_trail": trail,
    }
