"""
General node — greetings, small talk, or anything the Router couldn't
classify into a specialist intent.
"""
from state import AgentState

GENERAL_REPLY = (
    "Hi! I'm AcadEase AI. Ask me for notes, previous year papers, a study plan, "
    "or resource recommendations for any subject — e.g. \"DBMS notes\", "
    "\"PYQs for Operating System mid sem\", or \"help me prepare for my DAA exam\"."
)


def general_node(state: AgentState) -> dict:
    trail = state.get("agent_trail", []) + ["general"]
    return {"reply": GENERAL_REPLY, "resources": [], "agent_trail": trail}
