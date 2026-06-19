"""Unit tests for the Graph ADT (graph.py)."""

from __future__ import annotations

import json

import pytest

from graph import Graph


class TestAddNode:
    def test_add_single_node(self, empty_undirected):
        g = empty_undirected
        assert g.add_node("X") is True
        assert "X" in g.node
        assert "X" in g.adjacency

    def test_add_duplicate_returns_false(self, empty_undirected):
        g = empty_undirected
        g.add_node("X")
        assert g.add_node("X") is False
        assert g.node_count == 1

    def test_add_multiple_nodes(self, empty_undirected):
        g = empty_undirected
        for n in "ABCDE":
            g.add_node(n)
        assert g.node_count == 5


class TestAddEdge:
    def test_undirected_edge_is_symmetric(self, empty_undirected):
        g = empty_undirected
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", 3.0)
        assert g.adjacency["A"]["B"] == 3.0
        assert g.adjacency["B"]["A"] == 3.0

    def test_directed_edge_is_one_way(self, empty_directed):
        g = empty_directed
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", 5.0)
        assert g.adjacency["A"]["B"] == 5.0
        assert "A" not in g.adjacency["B"]

    def test_missing_node_returns_false(self, empty_undirected):
        g = empty_undirected
        g.add_node("A")
        assert g.add_edge("A", "MISSING") is False  # no silent no-op

    def test_default_weight_is_one(self, empty_undirected):
        g = empty_undirected
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B")
        assert g.adjacency["A"]["B"] == 1.0

    def test_self_loop_directed(self, empty_directed):
        g = empty_directed
        g.add_node("A")
        assert g.add_edge("A", "A", 0) is True
        assert g.adjacency["A"]["A"] == 0

    def test_replace_weight(self, empty_undirected):
        g = empty_undirected
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", 1.0)
        g.add_edge("A", "B", 9.9)
        assert g.adjacency["A"]["B"] == 9.9


class TestDeleteNode:
    def test_delete_removes_node_and_edges(self, triangle):
        g = triangle
        assert g.delete_node("A") is True
        assert "A" not in g.node
        assert "A" not in g.adjacency
        assert "A" not in g.adjacency.get("B", {})
        assert "A" not in g.adjacency.get("C", {})

    def test_delete_absent_returns_false(self, empty_undirected):
        g = empty_undirected
        assert g.delete_node("MISSING") is False

    def test_delete_isolated_node(self, empty_undirected):
        g = empty_undirected
        g.add_node("A")
        assert g.delete_node("A") is True
        assert g.node_count == 0


class TestDeleteEdge:
    def test_delete_directed_edge(self, weighted_directed):
        g = weighted_directed
        assert g.delete_edge("A", "B") is True
        assert "B" not in g.adjacency["A"]
        # Reverse should not exist in a directed graph anyway
        assert "A" not in g.adjacency.get("B", {})

    def test_delete_undirected_edge_removes_both(self, triangle):
        g = triangle
        assert g.delete_edge("A", "B") is True
        assert "B" not in g.adjacency["A"]
        assert "A" not in g.adjacency["B"]

    def test_delete_absent_edge_returns_false(self, empty_directed):
        g = empty_directed
        g.add_node("A")
        g.add_node("B")
        assert g.delete_edge("A", "B") is False


class TestCounts:
    def test_node_count(self, triangle):
        assert triangle.node_count == 3

    def test_edge_count_undirected(self, triangle):
        # Triangle has 3 edges; adjacency stores 6 entries (each direction)
        assert triangle.edge_count == 3

    def test_edge_count_directed(self, weighted_directed):
        # A→B, A→C, B→D, B→C, C→D = 5
        assert weighted_directed.edge_count == 5


class TestSerialization:
    def test_to_dict_round_trip(self, weighted_directed):
        d = weighted_directed.to_dict()
        g2 = Graph.from_dict(d)
        assert g2.directed == weighted_directed.directed
        assert set(g2.node) == set(weighted_directed.node)
        assert g2.adjacency == weighted_directed.adjacency

    def test_to_json_round_trip(self, triangle):
        json_str = triangle.to_json()
        data = json.loads(json_str)
        g2 = Graph.from_json(json_str)
        assert not g2.directed
        assert g2.edge_count == 3

    def test_from_dict_empty(self):
        g = Graph.from_dict({"directed": True, "nodes": [], "adjacency": {}})
        assert g.directed is True
        assert g.node_count == 0

    def test_viz_dict_structure(self, triangle):
        d = triangle.to_viz_dict()
        assert "nodes" in d
        assert "edges" in d
        assert "directed" in d
        assert len(d["nodes"]) == 3
        assert len(d["edges"]) == 3  # de-duplicated for undirected
