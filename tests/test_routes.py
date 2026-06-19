"""Integration tests for Flask HTML routes and REST API endpoints."""

from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# HTML route smoke tests
# ---------------------------------------------------------------------------


class TestHomeRoute:
    def test_get_home_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Graph Visualizer" in resp.data


class TestAddNode:
    def test_add_node_redirects(self, client):
        resp = client.post("/add_node", data={"node_id": "A"})
        assert resp.status_code == 302

    def test_add_duplicate_node_shows_error(self, client):
        client.post("/add_node", data={"node_id": "A"})
        resp = client.post("/add_node", data={"node_id": "A"}, follow_redirects=True)
        assert b"already exists" in resp.data

    def test_empty_node_id_shows_error(self, client):
        resp = client.post("/add_node", data={"node_id": ""}, follow_redirects=True)
        assert b"cannot be empty" in resp.data


class TestAddEdge:
    def _setup(self, client):
        client.post("/add_node", data={"node_id": "A"})
        client.post("/add_node", data={"node_id": "B"})

    def test_add_edge_success(self, client):
        self._setup(client)
        resp = client.post("/add_edge", data={"u": "A", "v": "B", "w": "2.5"})
        assert resp.status_code == 302

    def test_add_edge_unknown_node(self, client):
        client.post("/add_node", data={"node_id": "A"})
        resp = client.post("/add_edge", data={"u": "A", "v": "MISSING"}, follow_redirects=True)
        assert b"not found" in resp.data.lower() or b"unknown" in resp.data.lower()

    def test_add_edge_bad_weight(self, client):
        self._setup(client)
        resp = client.post("/add_edge", data={"u": "A", "v": "B", "w": "xyz"}, follow_redirects=True)
        assert b"number" in resp.data.lower()


class TestAlgorithmRoutes:
    def _build_graph(self, client):
        for n in ("A", "B", "C"):
            client.post("/add_node", data={"node_id": n})
        client.post("/add_edge", data={"u": "A", "v": "B", "w": "1"})
        client.post("/add_edge", data={"u": "B", "v": "C", "w": "1"})

    def test_bfs_returns_200(self, client):
        self._build_graph(client)
        resp = client.post("/bfs", data={"node_id": "A"})
        assert resp.status_code == 200

    def test_dfs_returns_200(self, client):
        self._build_graph(client)
        resp = client.post("/dfs", data={"node_id": "A"})
        assert resp.status_code == 200

    def test_dijkstra_returns_200(self, client):
        self._build_graph(client)
        resp = client.post("/dijkstra", data={"node_id": "A"})
        assert resp.status_code == 200

    def test_cycle_returns_200(self, client):
        self._build_graph(client)
        resp = client.post("/cycle")
        assert resp.status_code == 200

    def test_topo_sort_requires_directed(self, client):
        self._build_graph(client)
        resp = client.post("/topological", follow_redirects=True)
        assert b"directed" in resp.data.lower()


class TestResetAndMode:
    def test_reset_clears_graph(self, client):
        client.post("/add_node", data={"node_id": "A"})
        client.post("/reset")
        resp = client.get("/")
        assert b'"nodes": []' in resp.data or b"No nodes yet" in resp.data

    def test_set_mode_directed(self, client):
        resp = client.post("/set_mode", data={"direction": "Directed Graph"})
        assert resp.status_code == 302


# ---------------------------------------------------------------------------
# REST API endpoint tests
# ---------------------------------------------------------------------------


def _json(resp) -> dict:
    return json.loads(resp.data)


class TestAPIGraph:
    def test_get_graph_empty(self, client):
        resp = client.get("/api/v1/graph")
        assert resp.status_code == 200
        data = _json(resp)
        assert data["status"] == "ok"
        assert data["graph"]["nodes"] == []


class TestAPINodes:
    def test_create_node(self, client):
        resp = client.post(
            "/api/v1/nodes",
            json={"node_id": "X"},
        )
        assert resp.status_code == 200
        data = _json(resp)
        assert data["node_id"] == "X"

    def test_create_duplicate_node_400(self, client):
        client.post("/api/v1/nodes", json={"node_id": "X"})
        resp = client.post("/api/v1/nodes", json={"node_id": "X"})
        assert resp.status_code == 400

    def test_delete_node(self, client):
        client.post("/api/v1/nodes", json={"node_id": "X"})
        resp = client.delete("/api/v1/nodes/X")
        assert resp.status_code == 200

    def test_delete_absent_node_404(self, client):
        resp = client.delete("/api/v1/nodes/MISSING")
        assert resp.status_code == 404


class TestAPIEdges:
    def _setup(self, client):
        client.post("/api/v1/nodes", json={"node_id": "A"})
        client.post("/api/v1/nodes", json={"node_id": "B"})

    def test_create_edge(self, client):
        self._setup(client)
        resp = client.post("/api/v1/edges", json={"u": "A", "v": "B", "w": 3.0})
        assert resp.status_code == 200
        data = _json(resp)
        assert data["edge"]["w"] == 3.0

    def test_create_edge_missing_node_400(self, client):
        client.post("/api/v1/nodes", json={"node_id": "A"})
        resp = client.post("/api/v1/edges", json={"u": "A", "v": "MISSING"})
        assert resp.status_code == 400

    def test_delete_edge(self, client):
        self._setup(client)
        client.post("/api/v1/edges", json={"u": "A", "v": "B"})
        resp = client.delete("/api/v1/edges/A/B")
        assert resp.status_code == 200

    def test_delete_absent_edge_404(self, client):
        self._setup(client)
        resp = client.delete("/api/v1/edges/A/B")
        assert resp.status_code == 404


class TestAPIAlgorithms:
    def _build(self, client, directed: bool = False):
        # Explicitly reset + set mode so each test starts clean
        client.post("/reset")
        client.post("/set_mode", data={"direction": "Directed Graph" if directed else "Undirected Graph"})
        for n in ("A", "B", "C"):
            client.post("/api/v1/nodes", json={"node_id": n})
        client.post("/api/v1/edges", json={"u": "A", "v": "B", "w": 1})
        client.post("/api/v1/edges", json={"u": "B", "v": "C", "w": 2})

    def test_bfs(self, client):
        self._build(client)
        resp = client.post("/api/v1/algorithms/bfs", json={"start": "A"})
        data = _json(resp)
        assert data["status"] == "ok"
        assert "A" in data["visit_order"]
        assert "complexity" in data

    def test_dfs(self, client):
        self._build(client)
        resp = client.post("/api/v1/algorithms/dfs", json={"start": "A"})
        data = _json(resp)
        assert data["status"] == "ok"
        assert "stack_trace" in data

    def test_dijkstra_with_path(self, client):
        self._build(client)
        resp = client.post("/api/v1/algorithms/dijkstra", json={"start": "A", "target": "C"})
        data = _json(resp)
        assert data["status"] == "ok"
        assert data["path"] == ["A", "B", "C"]
        assert data["distances"]["C"] == 3.0

    def test_bellman_ford(self, client):
        self._build(client)  # includes explicit reset
        resp = client.post("/api/v1/algorithms/bellman-ford", json={"start": "A"})
        data = _json(resp)
        assert data["status"] == "ok"
        assert data["has_negative_cycle"] is False

    def test_scc_requires_directed(self, client):
        self._build(client, directed=False)  # includes explicit reset
        resp = client.post("/api/v1/algorithms/scc")
        assert resp.status_code == 400

    def test_topo_requires_directed(self, client):
        self._build(client, directed=False)  # includes explicit reset
        resp = client.post("/api/v1/algorithms/topo")
        assert resp.status_code == 400

    def test_mst(self, client):
        self._build(client)  # includes explicit reset
        resp = client.post("/api/v1/algorithms/mst")
        data = _json(resp)
        assert data["status"] == "ok"
        assert len(data["mst_edges"]) == 2  # 3 nodes → 2 MST edges



