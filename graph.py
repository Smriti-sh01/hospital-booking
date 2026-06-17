"""
graph.py
────────
Builds and compiles the LangGraph StateGraph for the appointment agent.

Graph shape:
    START
      │
      ▼
    normalise_input
      │
      ▼
    session_load
      │
      ▼
    llm_classify
      │
      ▼  (conditional edge via router())
      ├─► greeting_node ──────────────────────┐
      ├─► slot_fill_node ─────────────────────┤
      ├─► api_chain_node → slot_fill_node ────┤
      ├─► confirmation_node ──────────────────┤
      └─► confirmation_handler ───────────────┘
                                              │
                                              ▼
                                        session_write
                                              │
                                              ▼
                                        response_node
                                              │
                                              ▼
                                             END

Every branch converges at session_write → response_node → END.

Note on api_chain_node:
    After api_chain_node fetches live options, control goes to
    slot_fill_node which reads the cache and builds the options payload.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from state import AppointmentState
from nodes.normalise     import normalise_input_node
from nodes.session       import session_load_node, session_write_node
from nodes.classify      import llm_classify_node
from nodes.router        import router
from nodes.greeting      import greeting_node
from nodes.slot_fill     import slot_fill_node
from nodes.api_chain     import api_chain_node
from nodes.confirmation  import confirmation_node, confirmation_handler
from nodes.response      import response_node

def build_graph() -> StateGraph:
    g = StateGraph(AppointmentState)

    # ── Register nodes ────────────────────────────────────────────────────
    g.add_node("normalise_input",      normalise_input_node)
    g.add_node("session_load",         session_load_node)
    g.add_node("llm_classify",         llm_classify_node)
    g.add_node("greeting_node",        greeting_node)
    g.add_node("slot_fill_node",       slot_fill_node)
    g.add_node("api_chain_node",       api_chain_node)
    g.add_node("confirmation_node",    confirmation_node)
    g.add_node("confirmation_handler", confirmation_handler)
    g.add_node("session_write",        session_write_node)
    g.add_node("response_node",        response_node)

    # ── Fixed edges: pipeline start ───────────────────────────────────────
    g.add_edge(START,              "normalise_input")
    g.add_edge("normalise_input",  "session_load")
    g.add_edge("session_load",     "llm_classify")

    # ── Conditional edge: router decides the next node ────────────────────
    g.add_conditional_edges(
        "llm_classify",
        router,
        {
            "greeting_node":        "greeting_node",
            "slot_fill_node":       "slot_fill_node",
            "api_chain_node":       "api_chain_node",
            "confirmation_node":    "confirmation_node",
            "confirmation_handler": "confirmation_handler",
            "session_write":        "session_write",
        },
    )

    # ── api_chain_node always feeds into slot_fill_node ───────────────────
    # (slot_fill_node reads the freshly populated api_context and builds
    #  the options payload for the user)
    g.add_edge("api_chain_node", "slot_fill_node")

    # ── All logic nodes converge at session_write ─────────────────────────
    for node in [
        "greeting_node",
        "slot_fill_node",
        "confirmation_node",
        "confirmation_handler",
    ]:
        g.add_edge(node, "session_write")

    # ── session_write → response → END ───────────────────────────────────
    g.add_edge("session_write", "response_node")
    g.add_edge("response_node", END)

    return g


# Compile once at import time — reused for every request
compiled_graph = build_graph().compile()

