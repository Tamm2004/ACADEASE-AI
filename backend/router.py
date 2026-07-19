"""
Router Agent (LangGraph node)

Reads the user's message + recent history, decides which specialist
node should run next, and extracts structured entities. Falls back to
keyword heuristics if the LLM call fails or returns unparseable JSON,
so the graph still makes progress if Grok is unreachable.
"""
import logging

from data_loader import store
from llm_client import LLMError, grok_client
from state import AgentState

logger = logging.getLogger("acadease.router")

SYSTEM_PROMPT = """You are the Router Agent inside AcadEase AI, an academic assistant for \
Guru Nanak Dev University MCA students. Classify the student's latest message into exactly \
one intent and extract any entities mentioned.

Intents:
- "notes": student wants study notes / lecture material for a subject
- "pyq": student wants previous year question papers / exam papers
- "guidance": student wants a study plan, exam prep strategy, or "how do I prepare for X"
- "recommendation": student explicitly wants external resources (YouTube, books, websites, practice)
- "general": greetings, small talk, or anything not covered above

Respond with ONLY a JSON object, no prose, no markdown fences, matching exactly:
{
  "intent": "notes" | "pyq" | "guidance" | "recommendation" | "general",
  "subject": string or null,
  "semester": integer or null,
  "year": integer or null,
  "exam_type": "Mid Semester" | "Final Semester" | null,
  "reasoning": short string
}

Subject codes/names may be informal (e.g. "daa", "dbms", "os"); pass through whatever the \
student wrote in "subject" — a separate step resolves it to the catalog's canonical name.
"""

_KEYWORD_FALLBACK = [
    (("previous year", "pyq", "question paper", "past paper", "exam paper"), "pyq"),
    (("study plan", "prepare for", "how do i study", "guidance", "schedule"), "guidance"),
    (("youtube", "playlist", "recommend", "book for", "website", "practice"), "recommendation"),
    (("notes", "material", "unit ", "chapter"), "notes"),
]


def _keyword_fallback(message: str) -> dict:
    lower = message.lower()
    for keywords, intent in _KEYWORD_FALLBACK:
        if any(k in lower for k in keywords):
            return {"intent": intent, "subject": None, "semester": None, "year": None, "exam_type": None}
    return {"intent": "general", "subject": None, "semester": None, "year": None, "exam_type": None}


async def router_node(state: AgentState) -> dict:
    message = state["user_query"]
    history = state.get("history", [])

    convo = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-6:]:
        convo.append({"role": h["role"], "content": h["content"]})
    convo.append({"role": "user", "content": message})

    try:
        decision = await grok_client.chat_json(convo, temperature=0.1, max_tokens=300)
        if decision is None:
            decision = _keyword_fallback(message)
    except LLMError as e:
        logger.warning("Router LLM call failed, using keyword fallback: %s", e)
        decision = _keyword_fallback(message)

    raw_subject = decision.get("subject")
    resolved = store.resolve_subject(raw_subject) or store.resolve_subject(message)

    trail = state.get("agent_trail", []) + ["router"]
    return {
        "intent": decision.get("intent", "general"),
        "subject_query": raw_subject,
        "resolved_subject": resolved,
        "semester": decision.get("semester"),
        "year": decision.get("year"),
        "exam_type": decision.get("exam_type"),
        "agent_trail": trail,
    }
