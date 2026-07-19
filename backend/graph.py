"""
Builds and compiles the AcadEase AI LangGraph.

    START -> router -> (notes | pyq | guidance | recommendation | general)

Notes/PYQ nodes conditionally continue to the Recommender node when
they find nothing in the catalog, so the assistant never dead-ends —
the "intelligent hub" behaviour from the project brief.
"""
from langgraph.graph import END, START, StateGraph

from general_agent import general_node
from guidance_agent import guidance_node
from notes_agent import notes_node
from pyq_agent import pyq_node
from recommender_agent import recommender_node
from router import router_node
from state import AgentState


def _route_after_router(state: AgentState) -> str:
    return {
        "notes": "notes",
        "pyq": "pyq",
        "guidance": "guidance",
        "recommendation": "recommender",
        "general": "general",
    }.get(state.get("intent", "general"), "general")


def _route_after_lookup(state: AgentState) -> str:
    """After Notes/PYQ search: hand off to the Recommender if nothing was found."""
    return "recommender" if not state.get("resources") else "end"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("notes", notes_node)
    graph.add_node("pyq", pyq_node)
    graph.add_node("guidance", guidance_node)
    graph.add_node("recommender", recommender_node)
    graph.add_node("general", general_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        _route_after_router,
        {"notes": "notes", "pyq": "pyq", "guidance": "guidance", "recommender": "recommender", "general": "general"},
    )

    graph.add_conditional_edges("notes", _route_after_lookup, {"recommender": "recommender", "end": END})
    graph.add_conditional_edges("pyq", _route_after_lookup, {"recommender": "recommender", "end": END})

    graph.add_edge("guidance", END)
    graph.add_edge("recommender", END)
    graph.add_edge("general", END)

    return graph.compile()


acadease_graph = build_graph()
