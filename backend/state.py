"""
Shared state that flows through every node in the LangGraph graph.

Each node reads what it needs and returns a partial dict of updates —
LangGraph merges that into the running state (standard TypedDict-state
pattern, no custom reducers needed since every field here is simply
overwritten by whichever node sets it, except `agent_trail` which each
node appends to).
"""
from typing import Any, Literal, Optional, TypedDict


class ChatTurn(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class AgentState(TypedDict, total=False):
    # ---- input ----
    user_query: str
    history: list[ChatTurn]
    filter_department: Optional[str]
    filter_semester: Optional[int]

    # ---- router output ----
    intent: Literal["notes", "pyq", "guidance", "recommendation", "general"]
    subject_query: Optional[str]       # raw subject text as the user said it
    resolved_subject: Optional[str]    # canonical subject name after resolution
    semester: Optional[int]
    year: Optional[int]
    exam_type: Optional[str]
    course_id: Optional[str]

    # ---- agent outputs ----
    resources: list[dict[str, Any]]
    search_method: Optional[Literal["metadata", "semantic", "curated", "llm_suggested", "none"]]
    study_plan: Optional[dict[str, Any]]
    reply: str

    # ---- bookkeeping ----
    agent_trail: list[str]
