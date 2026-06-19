"""Session-based per-user graph storage.

The graph is stored as a JSON-serialised dict inside Flask's signed-cookie
session.  This means:
  - No shared global state between requests or users.
  - No external dependency (no Redis, no DB for the working graph).
  - Thread-safe by design under gunicorn (each worker gets its own session).

The saved-graph persistence layer (named saves that survive restarts) is
handled separately in db.py.
"""

from __future__ import annotations

from flask import session

from graph import Graph

SESSION_KEY = "graph_state"


def load_graph() -> Graph:
    """Return the Graph stored in the current session.

    If no graph exists yet (new session or cleared state), returns a fresh
    undirected Graph.
    """
    raw = session.get(SESSION_KEY)
    if raw is None:
        return Graph(directed=False)
    try:
        return Graph.from_dict(raw)
    except Exception:
        # Corrupted session data — start fresh rather than crash.
        return Graph(directed=False)


def save_graph(g: Graph) -> None:
    """Persist the Graph into the current session."""
    session[SESSION_KEY] = g.to_dict()
    # Mark the session as modified so Flask serialises it even when only
    # mutable nested structures changed (dict inside dict).
    session.modified = True


def clear_graph() -> None:
    """Remove the graph from the session entirely."""
    session.pop(SESSION_KEY, None)
