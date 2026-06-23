"""REST API v1 — JSON-only Blueprint.

Mounted at /api/v1/ by app.py.
All endpoints are documented with Flasgger-compatible YAML docstrings
so Swagger UI is auto-generated at /api/docs.

Authentication: none (anonymous session, same cookie as HTML routes).
Rate limiting: inherited from the Limiter in app.py.
"""

from __future__ import annotations

import uuid

from flask import Blueprint, jsonify, request, session

from algorithms.bellman_ford import bellman_ford
from algorithms.bellman_ford import reconstruct_path as bf_path
from algorithms.bfs import bfs
from algorithms.cycle import has_cycle_directed, has_cycle_undirected
from algorithms.dfs import dfs
from algorithms.dijkstra import dijkstra
from algorithms.dijkstra import reconstruct_path as dijk_path
from algorithms.mst import kruskal
from algorithms.scc import tarjan_scc
from algorithms.topological_sort import topological_sort
from session_store import load_graph, save_graph

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

COMPLEXITY = {
    "bfs": {"time": "O(V + E)", "space": "O(V)"},
    "dfs": {"time": "O(V + E)", "space": "O(V)"},
    "dijkstra": {"time": "O((V + E) log V)", "space": "O(V)"},
    "bellman_ford": {"time": "O(V · E)", "space": "O(V)"},
    "mst": {"time": "O(E log E)", "space": "O(V)"},
    "scc": {"time": "O(V + E)", "space": "O(V)"},
    "cycle": {"time": "O(V + E)", "space": "O(V)"},
    "topo": {"time": "O(V + E)", "space": "O(V)"},
}


def _sid() -> str:
    if "_sid" not in session:
        session["_sid"] = str(uuid.uuid4())
    return session["_sid"]


def _ok(data: dict) -> tuple:
    return jsonify({"status": "ok", **data}), 200


def _err(msg: str, code: int = 400) -> tuple:
    return jsonify({"status": "error", "message": msg}), code


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------


@api_bp.route("/graph", methods=["GET"])
def get_graph():
    """
    Get current graph state.
    ---
    tags: [Graph]
    responses:
      200:
        description: Current graph as adjacency map.
        schema:
          type: object
          properties:
            directed: {type: boolean}
            nodes: {type: array, items: {type: string}}
            adjacency:
              type: object
              additionalProperties:
                type: object
                additionalProperties: {type: number}
    """
    g = load_graph()
    return _ok({"graph": g.to_dict()})


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


@api_bp.route("/nodes", methods=["POST"])
def create_node():
    """
    Add a node.
    ---
    tags: [Graph]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [node_id]
          properties:
            node_id: {type: string, example: A}
    responses:
      200: {description: Node added.}
      400: {description: Validation error.}
    """
    body = request.get_json(silent=True) or {}
    node_id = (body.get("node_id") or "").strip()
    if not node_id:
        return _err("node_id is required.")
    g = load_graph()
    if not g.add_node(node_id):
        return _err(f'Node "{node_id}" already exists.')
    save_graph(g)
    return _ok({"node_id": node_id, "graph": g.to_dict()})


@api_bp.route("/nodes/<node_id>", methods=["DELETE"])
def delete_node(node_id: str):
    """
    Delete a node and all incident edges.
    ---
    tags: [Graph]
    parameters:
      - in: path
        name: node_id
        type: string
        required: true
    responses:
      200: {description: Node deleted.}
      404: {description: Node not found.}
    """
    g = load_graph()
    if not g.delete_node(node_id):
        return _err(f'Node "{node_id}" not found.', 404)
    save_graph(g)
    return _ok({"deleted": node_id, "graph": g.to_dict()})


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


@api_bp.route("/edges", methods=["POST"])
def create_edge():
    """
    Add an edge.
    ---
    tags: [Graph]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [u, v]
          properties:
            u: {type: string, example: A}
            v: {type: string, example: B}
            w: {type: number, default: 1.0}
    responses:
      200: {description: Edge added.}
      400: {description: Validation error.}
    """
    body = request.get_json(silent=True) or {}
    u = (body.get("u") or "").strip()
    v = (body.get("v") or "").strip()
    if not u or not v:
        return _err("u and v are required.")
    try:
        w = float(body.get("w", 1.0))
    except (TypeError, ValueError):
        return _err("w must be a number.")
    g = load_graph()
    if not g.add_edge(u, v, w):
        return _err(f'One or both nodes ("{u}", "{v}") do not exist.')
    save_graph(g)
    return _ok({"edge": {"u": u, "v": v, "w": w}, "graph": g.to_dict()})


@api_bp.route("/edges/<u>/<v>", methods=["DELETE"])
def delete_edge(u: str, v: str):
    """
    Delete an edge.
    ---
    tags: [Graph]
    parameters:
      - in: path
        name: u
        type: string
        required: true
      - in: path
        name: v
        type: string
        required: true
    responses:
      200: {description: Edge deleted.}
      404: {description: Edge not found.}
    """
    g = load_graph()
    if not g.delete_edge(u, v):
        return _err(f'Edge "{u}→{v}" not found.', 404)
    save_graph(g)
    return _ok({"deleted": {"u": u, "v": v}, "graph": g.to_dict()})


# ---------------------------------------------------------------------------
# Algorithms
# ---------------------------------------------------------------------------


@api_bp.route("/algorithms/bfs", methods=["POST"])
def run_bfs():
    """
    Run Breadth-First Search.
    ---
    tags: [Algorithms]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [start]
          properties:
            start: {type: string}
    responses:
      200:
        description: BFS visit order.
    """
    body = request.get_json(silent=True) or {}
    start = (body.get("start") or "").strip()
    g = load_graph()
    if start not in g.node:
        return _err(f'Node "{start}" not found.')
    order = bfs(start, g.adjacency)
    return _ok({
        "algorithm": "BFS",
        "start": start,
        "visit_order": order,
        "complexity": COMPLEXITY["bfs"],
    })


@api_bp.route("/algorithms/dfs", methods=["POST"])
def run_dfs():
    """
    Run Depth-First Search.
    ---
    tags: [Algorithms]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [start]
          properties:
            start: {type: string}
    responses:
      200:
        description: DFS visit order and call-stack trace.
    """
    body = request.get_json(silent=True) or {}
    start = (body.get("start") or "").strip()
    g = load_graph()
    if start not in g.node:
        return _err(f'Node "{start}" not found.')
    result = dfs(start, g.adjacency)
    order, trace = result  # type: ignore[misc]
    return _ok({
        "algorithm": "DFS",
        "start": start,
        "visit_order": order,
        "stack_trace": trace,
        "complexity": COMPLEXITY["dfs"],
    })


@api_bp.route("/algorithms/dijkstra", methods=["POST"])
def run_dijkstra():
    """
    Run Dijkstra's shortest-path algorithm (non-negative weights).
    ---
    tags: [Algorithms]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [start]
          properties:
            start: {type: string}
            target: {type: string, description: Optional target for path reconstruction.}
    responses:
      200:
        description: Distances, visit order, and optional path.
    """
    body = request.get_json(silent=True) or {}
    start = (body.get("start") or "").strip()
    target = (body.get("target") or "").strip() or None
    g = load_graph()
    if start not in g.node:
        return _err(f'Node "{start}" not found.')
    result = dijkstra(start, g.adjacency)
    distances, visit_order, prev = result  # type: ignore[misc]
    path = dijk_path(prev, target) if target and target in g.node else None
    return _ok({
        "algorithm": "Dijkstra",
        "start": start,
        "distances": {k: (v if v != float("inf") else None) for k, v in distances.items()},
        "visit_order": visit_order,
        "path": path,
        "complexity": COMPLEXITY["dijkstra"],
    })


@api_bp.route("/algorithms/bellman-ford", methods=["POST"])
def run_bellman_ford():
    """
    Run Bellman-Ford (handles negative edge weights).
    ---
    tags: [Algorithms]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [start]
          properties:
            start: {type: string}
            target: {type: string}
    responses:
      200:
        description: Distances, visit order, negative cycle flag, and optional path.
    """
    body = request.get_json(silent=True) or {}
    start = (body.get("start") or "").strip()
    target = (body.get("target") or "").strip() or None
    g = load_graph()
    if start not in g.node:
        return _err(f'Node "{start}" not found.')
    result = bellman_ford(start, g.adjacency)
    distances, visit_order, prev, has_neg_cycle = result  # type: ignore[misc]
    path = None
    if target and target in g.node and not has_neg_cycle:
        path = bf_path(prev, target)
    return _ok({
        "algorithm": "Bellman-Ford",
        "start": start,
        "distances": {k: (v if v != float("inf") else None) for k, v in distances.items()},
        "visit_order": visit_order,
        "has_negative_cycle": has_neg_cycle,
        "path": path,
        "complexity": COMPLEXITY["bellman_ford"],
    })


@api_bp.route("/algorithms/mst", methods=["POST"])
def run_mst():
    """
    Run Kruskal's MST algorithm (with Union-Find).
    ---
    tags: [Algorithms]
    responses:
      200:
        description: MST edges and total weight.
    """
    g = load_graph()
    mst_edges, total_weight = kruskal(g.adjacency, g.directed)
    return _ok({
        "algorithm": "Kruskal MST",
        "mst_edges": [{"u": u, "v": v, "w": w} for u, v, w in mst_edges],
        "total_weight": total_weight,
        "complexity": COMPLEXITY["mst"],
    })


@api_bp.route("/algorithms/scc", methods=["POST"])
def run_scc():
    """
    Run Tarjan's Strongly Connected Components algorithm.
    ---
    tags: [Algorithms]
    responses:
      200:
        description: List of SCCs.
      400:
        description: Graph is not directed.
    """
    g = load_graph()
    if not g.directed:
        return _err("SCC requires a directed graph.")
    sccs = tarjan_scc(g.adjacency)
    return _ok({
        "algorithm": "Tarjan SCC",
        "sccs": sccs,
        "scc_count": len(sccs),
        "complexity": COMPLEXITY["scc"],
    })


@api_bp.route("/algorithms/cycle", methods=["POST"])
def run_cycle():
    """
    Detect a cycle in the current graph.
    ---
    tags: [Algorithms]
    responses:
      200:
        description: Cycle detection result.
    """
    g = load_graph()
    if g.directed:
        has = has_cycle_directed(g.adjacency)
    else:
        has = has_cycle_undirected(g.adjacency)
    return _ok({
        "algorithm": "Cycle Detection",
        "has_cycle": has,
        "mode": "directed" if g.directed else "undirected",
        "complexity": COMPLEXITY["cycle"],
    })


@api_bp.route("/algorithms/topo", methods=["POST"])
def run_topo():
    """
    Run topological sort (Kahn's algorithm).
    ---
    tags: [Algorithms]
    responses:
      200:
        description: Topological order or cycle notification.
      400:
        description: Graph is not directed.
    """
    g = load_graph()
    if not g.directed:
        return _err("Topological sort requires a directed graph.")
    order = topological_sort(g.adjacency)
    return _ok({
        "algorithm": "Topological Sort",
        "order": order,
        "has_cycle": order is None,
        "complexity": COMPLEXITY["topo"],
    })


# ---------------------------------------------------------------------------
