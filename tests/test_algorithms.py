"""Unit tests for all graph algorithms.

Key principle: every test covers at least one interesting edge case, not
just the happy path.  We never use NetworkX as the implementation — only
as an oracle to cross-validate our output where noted.
"""

from __future__ import annotations

import pytest

from algorithms.bfs import bfs
from algorithms.bellman_ford import bellman_ford, reconstruct_path as bf_reconstruct
from algorithms.cycle import has_cycle_directed, has_cycle_undirected
from algorithms.dfs import dfs
from algorithms.dijkstra import dijkstra, reconstruct_path as dijk_reconstruct
from algorithms.mst import UnionFind, kruskal
from algorithms.scc import tarjan_scc
from algorithms.topological_sort import topological_sort
from graph import Graph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_graph(edges: list[tuple], directed: bool = False, nodes: list[str] | None = None) -> Graph:
    g = Graph(directed=directed)
    all_nodes: set[str] = set(nodes or [])
    for e in edges:
        all_nodes.update(e[:2])
    for n in sorted(all_nodes):
        g.add_node(n)
    for e in edges:
        u, v = e[0], e[1]
        w = e[2] if len(e) > 2 else 1.0
        g.add_edge(u, v, w)
    return g


# ---------------------------------------------------------------------------
# BFS
# ---------------------------------------------------------------------------


class TestBFS:
    def test_basic_visit_order(self):
        g = make_graph([("A", "B"), ("A", "C"), ("B", "D")])
        order = bfs("A", g.adjacency)
        assert order[0] == "A"
        assert set(order) == {"A", "B", "C", "D"}
        # B and C must appear before D (level-order)
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_single_node(self):
        g = Graph()
        g.add_node("X")
        assert bfs("X", g.adjacency) == ["X"]

    def test_absent_start_returns_none(self):
        g = Graph()
        g.add_node("A")
        assert bfs("MISSING", g.adjacency) is None

    def test_disconnected_graph_visits_component_only(self):
        g = make_graph([("A", "B")])
        g.add_node("Z")  # isolated
        order = bfs("A", g.adjacency)
        assert "Z" not in order
        assert set(order) == {"A", "B"}

    def test_self_loop_does_not_infinite_loop(self):
        g = Graph(directed=True)
        g.add_node("A")
        g.add_edge("A", "A")
        order = bfs("A", g.adjacency)
        assert order == ["A"]


# ---------------------------------------------------------------------------
# DFS
# ---------------------------------------------------------------------------


class TestDFS:
    def test_preorder_first_node(self, weighted_directed):
        result = dfs("A", weighted_directed.adjacency)
        order, trace = result
        assert order[0] == "A"
        assert set(order) == {"A", "B", "C", "D"}

    def test_trace_structure(self, weighted_directed):
        result = dfs("A", weighted_directed.adjacency)
        order, trace = result
        assert len(trace) == len(order)
        for frame in trace:
            assert "focus" in frame
            assert "stack" in frame
            assert isinstance(frame["stack"], list)

    def test_trace_focus_matches_order(self, weighted_directed):
        result = dfs("A", weighted_directed.adjacency)
        order, trace = result
        assert [f["focus"] for f in trace] == order

    def test_absent_start(self):
        g = Graph()
        assert dfs("MISSING", g.adjacency) is None

    def test_single_node(self):
        g = Graph()
        g.add_node("A")
        order, trace = dfs("A", g.adjacency)
        assert order == ["A"]
        assert trace[0]["stack"] == ["A"]


# ---------------------------------------------------------------------------
# Dijkstra
# ---------------------------------------------------------------------------


class TestDijkstra:
    def test_distances(self, weighted_directed):
        result = dijkstra("A", weighted_directed.adjacency)
        distances, _, _ = result
        assert distances["A"] == 0
        assert distances["B"] == 1
        assert distances["D"] == 3   # A→B→D
        assert distances["C"] == 4   # A→C (A→B→C=6, A→C=4, A→B→D→? no)

    def test_path_reconstruction(self, weighted_directed):
        result = dijkstra("A", weighted_directed.adjacency)
        _, _, prev = result
        path = dijk_reconstruct(prev, "D")
        assert path == ["A", "B", "D"]

    def test_unreachable_node(self):
        g = Graph(directed=True)
        for n in ("A", "B"):
            g.add_node(n)
        # No edges — B is unreachable from A
        result = dijkstra("A", g.adjacency)
        distances, _, _ = result
        assert distances["B"] == float("inf")

    def test_absent_start(self):
        g = Graph()
        assert dijkstra("MISSING", g.adjacency) is None

    def test_single_node_zero_distance(self):
        g = Graph()
        g.add_node("A")
        result = dijkstra("A", g.adjacency)
        distances, _, _ = result
        assert distances["A"] == 0


# ---------------------------------------------------------------------------
# Bellman-Ford
# ---------------------------------------------------------------------------


class TestBellmanFord:
    def test_same_result_as_dijkstra_no_negatives(self, weighted_directed):
        bf = bellman_ford("A", weighted_directed.adjacency)
        dijk = dijkstra("A", weighted_directed.adjacency)
        bf_dist = bf[0]
        dijk_dist = dijk[0]
        assert bf_dist == pytest.approx(dijk_dist)

    def test_negative_weights(self, negative_weighted):
        result = bellman_ford("A", negative_weighted.adjacency)
        distances, _, _, has_neg_cycle = result
        assert not has_neg_cycle
        # A→B(−1)→D(2)→C(−5) = −4
        assert distances["C"] == pytest.approx(-4.0)

    def test_negative_cycle_detected(self):
        g = Graph(directed=True)
        for n in ("A", "B", "C"):
            g.add_node(n)
        g.add_edge("A", "B", 1)
        g.add_edge("B", "C", -3)
        g.add_edge("C", "B", 1)   # B→C→B cycle = -3+1 = -2 < 0
        result = bellman_ford("A", g.adjacency)
        _, _, _, has_neg_cycle = result
        assert has_neg_cycle is True

    def test_path_reconstruction(self, negative_weighted):
        result = bellman_ford("A", negative_weighted.adjacency)
        _, _, prev, _ = result
        path = bf_reconstruct(prev, "C")
        assert path == ["A", "B", "D", "C"]

    def test_absent_start(self):
        g = Graph()
        assert bellman_ford("MISSING", g.adjacency) is None


# ---------------------------------------------------------------------------
# MST (Kruskal + Union-Find)
# ---------------------------------------------------------------------------


class TestUnionFind:
    def test_initially_separate(self):
        uf = UnionFind(["A", "B", "C"])
        assert uf.find("A") != uf.find("B")

    def test_union_merges(self):
        uf = UnionFind(["A", "B", "C"])
        assert uf.union("A", "B") is True
        assert uf.find("A") == uf.find("B")

    def test_double_union_returns_false(self):
        uf = UnionFind(["A", "B"])
        uf.union("A", "B")
        assert uf.union("A", "B") is False

    def test_path_compression(self):
        # After many unions, find() should still return a valid root
        nodes = [str(i) for i in range(10)]
        uf = UnionFind(nodes)
        for i in range(9):
            uf.union(nodes[i], nodes[i + 1])
        root = uf.find(nodes[0])
        for n in nodes:
            assert uf.find(n) == root


class TestKruskal:
    def test_total_weight(self):
        # Square: A–B(1), B–C(2), C–D(3), D–A(4), A–C(5)
        # MST should be A–B(1) + B–C(2) + C–D(3) = 6
        g = make_graph([
            ("A", "B", 1), ("B", "C", 2), ("C", "D", 3),
            ("D", "A", 4), ("A", "C", 5),
        ])
        edges, total = kruskal(g.adjacency)
        assert total == pytest.approx(6.0)
        assert len(edges) == 3  # spanning tree has n-1 edges

    def test_single_node_no_edges(self):
        g = Graph()
        g.add_node("A")
        edges, total = kruskal(g.adjacency)
        assert edges == []
        assert total == 0.0

    def test_disconnected_graph_is_spanning_forest(self):
        g = make_graph([("A", "B", 1)], nodes=["A", "B", "C"])  # C isolated
        edges, _ = kruskal(g.adjacency)
        assert len(edges) == 1  # only A–B; C stays isolated

    def test_triangle(self, triangle):
        edges, total = kruskal(triangle.adjacency)
        assert len(edges) == 2  # 3 nodes → 2 MST edges
        assert total == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Tarjan SCC
# ---------------------------------------------------------------------------


class TestTarjanSCC:
    def test_single_scc(self):
        # Fully connected directed cycle: A→B→C→A
        g = make_graph([("A", "B"), ("B", "C"), ("C", "A")], directed=True)
        sccs = tarjan_scc(g.adjacency)
        assert len(sccs) == 1
        assert set(sccs[0]) == {"A", "B", "C"}

    def test_dag_each_node_own_scc(self):
        # DAG has no non-trivial SCCs
        g = make_graph([("A", "B"), ("B", "C")], directed=True)
        sccs = tarjan_scc(g.adjacency)
        assert len(sccs) == 3
        assert all(len(scc) == 1 for scc in sccs)

    def test_two_sccs(self):
        # A↔B (SCC) and C (separate)
        g = make_graph([("A", "B"), ("B", "A"), ("B", "C")], directed=True)
        sccs = tarjan_scc(g.adjacency)
        sizes = sorted(len(s) for s in sccs)
        assert sizes == [1, 2]

    def test_empty_graph(self):
        g = Graph(directed=True)
        sccs = tarjan_scc(g.adjacency)
        assert sccs == []

    def test_single_node_no_edges(self):
        g = Graph(directed=True)
        g.add_node("A")
        sccs = tarjan_scc(g.adjacency)
        assert len(sccs) == 1
        assert sccs[0] == ["A"]


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------


class TestCycleDetection:
    def test_undirected_cycle(self, triangle):
        assert has_cycle_undirected(triangle.adjacency) is True

    def test_undirected_tree_no_cycle(self):
        g = make_graph([("A", "B"), ("B", "C"), ("C", "D")])
        assert has_cycle_undirected(g.adjacency) is False

    def test_directed_cycle(self):
        g = make_graph([("A", "B"), ("B", "C"), ("C", "A")], directed=True)
        assert has_cycle_directed(g.adjacency) is True

    def test_directed_acyclic(self, weighted_directed):
        assert has_cycle_directed(weighted_directed.adjacency) is False

    def test_self_loop_is_cycle_directed(self):
        g = Graph(directed=True)
        g.add_node("A")
        g.add_edge("A", "A")
        assert has_cycle_directed(g.adjacency) is True

    def test_empty_graph_no_cycle(self):
        assert has_cycle_directed({}) is False
        assert has_cycle_undirected({}) is False

    def test_disconnected_with_cycle(self):
        # Component 1: A–B (no cycle); Component 2: C–D–E–C (cycle)
        g = make_graph([("A", "B"), ("C", "D"), ("D", "E"), ("E", "C")])
        assert has_cycle_undirected(g.adjacency) is True


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------


class TestTopologicalSort:
    def test_basic_order(self, weighted_directed):
        order = topological_sort(weighted_directed.adjacency)
        assert order is not None
        # A must come before B, B before D, etc.
        idx = {n: i for i, n in enumerate(order)}
        assert idx["A"] < idx["B"]
        assert idx["B"] < idx["D"]
        assert idx["A"] < idx["C"]
        assert idx["C"] < idx["D"]

    def test_cycle_returns_none(self):
        g = make_graph([("A", "B"), ("B", "C"), ("C", "A")], directed=True)
        assert topological_sort(g.adjacency) is None

    def test_empty_graph(self):
        assert topological_sort({}) == []

    def test_single_node(self):
        g = Graph(directed=True)
        g.add_node("A")
        assert topological_sort(g.adjacency) == ["A"]

    def test_deterministic_output(self, weighted_directed):
        # Running twice should produce identical output
        o1 = topological_sort(weighted_directed.adjacency)
        o2 = topological_sort(weighted_directed.adjacency)
        assert o1 == o2

    def test_all_nodes_present(self, weighted_directed):
        order = topological_sort(weighted_directed.adjacency)
        assert set(order) == set(weighted_directed.node)
