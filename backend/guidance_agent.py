"""
Guidance Agent (LangGraph node)

Generates a structured study plan via Grok. Grounds the prompt with
whatever catalog context is available (course/semester) so the plan
isn't generic. Falls back to a template plan if the LLM is unreachable.
"""
import logging

from data_loader import store
from llm_client import LLMError, grok_client
from state import AgentState

logger = logging.getLogger("acadease.guidance")

SYSTEM_PROMPT = """You are the Guidance Agent inside AcadEase AI, an academic assistant for \
Guru Nanak Dev University MCA students. A student wants help preparing for a subject/exam. \
Produce a clear, realistic, encouraging study plan.

Respond with ONLY a JSON object, no prose, no markdown fences, matching exactly:
{
  "summary": "one or two sentence overview",
  "days": [
    {"day": "Day 1", "focus": "topic(s)", "tasks": ["task 1", "task 2"]}
  ],
  "tips": ["short actionable tip", "..."]
}

Keep it realistic for a student juggling multiple subjects. Default to a 7-day plan if no \
timeframe was given. If no subject was named, ask for one in "summary" and return an empty \
days list.
"""


def _fallback_plan() -> dict:
    return {
        "summary": "I couldn't reach the planning model right now, so here's a general template you can adapt.",
        "days": [
            {"day": "Day 1-2", "focus": "Read through all units once", "tasks": ["Skim notes", "List unclear topics"]},
            {"day": "Day 3-4", "focus": "Deep dive on weak topics", "tasks": ["Rework examples", "Make short summary sheets"]},
            {"day": "Day 5", "focus": "Previous year papers", "tasks": ["Solve 2 PYQs under time limit"]},
            {"day": "Day 6", "focus": "Revision", "tasks": ["Review summary sheets", "Redo mistakes from PYQs"]},
            {"day": "Day 7", "focus": "Final recap", "tasks": ["Light revision only", "Rest well before the exam"]},
        ],
        "tips": ["Study in focused 45-50 min blocks with short breaks.", "Prioritize topics that appear most often in PYQs."],
    }


async def guidance_node(state: AgentState) -> dict:
    message = state["user_query"]
    history = state.get("history", [])
    subject = state.get("resolved_subject")

    context_note = ""
    if subject:
        ctx = store.get_subject_context(subject)
        if ctx:
            context_note = (
                f"\n\nCatalog context: subject '{subject}' is a {ctx.get('semester')}-semester "
                f"course in {ctx.get('course_name')}."
            )

    convo = [{"role": "system", "content": SYSTEM_PROMPT + context_note}]
    for h in history[-6:]:
        convo.append({"role": h["role"], "content": h["content"]})
    convo.append({"role": "user", "content": message})

    try:
        plan = await grok_client.chat_json(convo, temperature=0.5, max_tokens=900)
        if plan is None:
            plan = _fallback_plan()
    except LLMError as e:
        logger.warning("Guidance LLM call failed, using fallback plan: %s", e)
        plan = _fallback_plan()

    lines = [plan.get("summary", "Here's a study plan:")]
    for d in plan.get("days", []):
        tasks = "; ".join(d.get("tasks", []))
        lines.append(f"- **{d.get('day')}** — {d.get('focus')}: {tasks}")
    tips = plan.get("tips", [])
    if tips:
        lines.append("\n**Tips:** " + " | ".join(tips))

    trail = state.get("agent_trail", []) + ["guidance"]
    return {"study_plan": plan, "reply": "\n".join(lines), "resources": [], "agent_trail": trail}
