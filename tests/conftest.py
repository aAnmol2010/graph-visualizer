"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from graph import Graph


@pytest.fixture()
def empty_directed() -> Graph:
    return Graph(directed=True)


@pytest.fixture()
def empty_undirected() -> Graph:
    return Graph(directed=False)


@pytest.fixture()
def triangle() -> Graph:
    """Undirected triangle: A–B–C–A (weights all 1)."""
    g = Graph(directed=False)
    for n in ("A", "B", "C"):
        g.add_node(n)
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("C", "A")
    return g


@pytest.fixture()
def weighted_directed() -> Graph:
    """Directed weighted graph for shortest-path tests.

    Topology:
        A →(1)→ B →(2)→ D
        A →(4)→ C →(1)→ D
        B →(5)→ C
    Shortest A→D: A→B→D (cost 3).
    """
    g = Graph(directed=True)
    for n in ("A", "B", "C", "D"):
        g.add_node(n)
    g.add_edge("A", "B", 1)
    g.add_edge("A", "C", 4)
    g.add_edge("B", "D", 2)
    g.add_edge("B", "C", 5)
    g.add_edge("C", "D", 1)
    return g


@pytest.fixture()
def negative_weighted() -> Graph:
    """Directed graph with negative edges (no negative cycle).

    A→B(−1), A→C(4), B→C(3), B→D(2), D→C(−5)
    Shortest A→C via Bellman-Ford: A→B→D→C = -1+2-5 = -4.
    """
    g = Graph(directed=True)
    for n in ("A", "B", "C", "D"):
        g.add_node(n)
    g.add_edge("A", "B", -1)
    g.add_edge("A", "C", 4)
    g.add_edge("B", "C", 3)
    g.add_edge("B", "D", 2)
    g.add_edge("D", "C", -5)
    return g


@pytest.fixture(scope="session")
def flask_app():
    """Flask test application — created once per test session with in-memory SQLite.

    We do NOT hold an app_context() open for the whole session; instead we let
    each Flask test_client() request manage its own request context naturally.
    The DB is initialised once here.
    """
    import os
    os.environ["RATELIMIT_ENABLED"] = "0"  # disable Flask-Limiter before app import

    from app import app as flask_application
    flask_application.config["TESTING"] = True
    flask_application.config["SECRET_KEY"] = "test-secret"
    flask_application.config["RATELIMIT_ENABLED"] = False  # disable limiter in tests



    yield flask_application


@pytest.fixture()
def client(flask_app):
    """New test client per test — fresh session (new cookie) each time."""
    with flask_app.test_client() as c:
        yield c
