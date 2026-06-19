"""Flask application — HTML routes only.

All JSON endpoints live in api/v1.py (Blueprint mounted at /api/v1/).
Graph state is per-session via session_store.py — no shared global mutable state.
"""

from __future__ import annotations

import logging
import os

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from algorithms.bfs import BFS
from algorithms.cycle import has_cycle_directed, has_cycle_undirected
from algorithms.dfs import DFS
from algorithms.dijkstra import Dijkstra
from algorithms.topological_sort import topological_sort
from session_store import load_graph, save_graph

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-in-production")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True

# Rate limiting — reasonable ceiling for an educational app.
# Set env var RATELIMIT_ENABLED=0 to disable (e.g. in tests or local dev).
_rate_limit_enabled = os.environ.get("RATELIMIT_ENABLED", "1") not in ("0", "false", "False")
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per minute", "20 per second"],
    storage_uri="memory://",
    enabled=_rate_limit_enabled,
)

# Register the REST API blueprint
from api.v1 import api_bp  # noqa: E402 (after app creation to avoid circular imports)

app.register_blueprint(api_bp)

# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------


@app.template_filter("fmt_dist")
def fmt_dist(d: float) -> str:
    if d == float("inf"):
        return "∞"
    fd = float(d)
    if fd.is_integer():
        return str(int(fd))
    return str(d)


@app.context_processor
def inject_graph_viz() -> dict:
    g = load_graph()
    return {"graph_viz": g.to_viz_dict()}


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------


def _clean(s: str | None) -> str:
    return (s or "").strip()


def _require_node(node_id: str | None, label: str = "Node") -> str | None:
    g = load_graph()
    nid = _clean(node_id)
    if not nid:
        flash(f"{label} cannot be empty.", "error")
        return None
    if nid not in g.node:
        flash(f'Unknown node "{nid}". Add the node first or check spelling.', "error")
        return None
    return nid


def _require_two_nodes(u_raw: str | None, v_raw: str | None) -> tuple[str | None, str | None]:
    u = _require_node(u_raw, "Source node")
    if u is None:
        return None, None
    v = _require_node(v_raw, "Target node")
    if v is None:
        return None, None
    return u, v


# ---------------------------------------------------------------------------
# HTML routes
# ---------------------------------------------------------------------------


@app.route("/", methods=["GET"])
def home() -> str:
    g = load_graph()
    return render_template("index.html", graph=g)


@app.route("/add_node", methods=["POST"])
@limiter.limit("60 per minute")
def add_n() -> "Response":  # type: ignore[name-defined]
    g = load_graph()
    node_id = _clean(request.form.get("node_id"))
    if not node_id:
        flash("Node id cannot be empty.", "error")
        return redirect(url_for("home"))
    if node_id in g.node:
        flash(f'Node "{node_id}" already exists.', "error")
        return redirect(url_for("home"))
    g.add_node(node_id)
    save_graph(g)
    logger.info("add_node %s", node_id)
    flash(f'Added node "{node_id}".', "success")
    return redirect(url_for("home"))


@app.route("/add_edge", methods=["POST"])
@limiter.limit("60 per minute")
def add_e() -> "Response":  # type: ignore[name-defined]
    g = load_graph()
    u_raw = request.form.get("u")
    v_raw = request.form.get("v")
    u = _clean(u_raw)
    v = _clean(v_raw)
    if not u or u not in g.node:
        flash(f'Unknown source node "{u}". Add it first.', "error")
        return redirect(url_for("home"))
    if not v or v not in g.node:
        flash(f'Unknown target node "{v}". Add it first.', "error")
        return redirect(url_for("home"))
    w_raw = request.form.get("w")
    try:
        w = float(w_raw) if _clean(w_raw) else 1.0
    except (TypeError, ValueError):
        flash("Weight must be a number.", "error")
        return redirect(url_for("home"))
    g.add_edge(u, v, w)
    save_graph(g)
    logger.info("add_edge %s→%s (w=%s)", u, v, w)
    flash(f"Edge {u} → {v} (weight {w}) added.", "success")
    return redirect(url_for("home"))


@app.route("/delete_node", methods=["POST"])
@limiter.limit("60 per minute")
def del_n() -> "Response":  # type: ignore[name-defined]
    g = load_graph()
    node_id = _clean(request.form.get("node_id"))
    if not node_id or node_id not in g.node:
        flash(f'Node "{node_id}" not found.', "error")
        return redirect(url_for("home"))
    g.delete_node(node_id)
    save_graph(g)
    logger.info("delete_node %s", node_id)
    flash(f'Removed node "{node_id}" and its incident edges.', "success")
    return redirect(url_for("home"))


@app.route("/delete_edge", methods=["POST"])
@limiter.limit("60 per minute")
def del_e() -> "Response":  # type: ignore[name-defined]
    g = load_graph()
    u = _clean(request.form.get("u"))
    v = _clean(request.form.get("v"))
    if not u or u not in g.node:
        flash(f'Node "{u}" not found.', "error")
        return redirect(url_for("home"))
    if not v or v not in g.node:
        flash(f'Node "{v}" not found.', "error")
        return redirect(url_for("home"))
    if v not in g.adjacency.get(u, {}):
        flash(f'No edge from "{u}" to "{v}".', "error")
        return redirect(url_for("home"))
    g.delete_edge(u, v)
    save_graph(g)
    logger.info("delete_edge %s→%s", u, v)
    flash(f"Removed edge {u} → {v}.", "success")
    return redirect(url_for("home"))


@app.route("/bfs", methods=["POST"])
def bfs_traversal() -> str:
    g = load_graph()
    node_id = _clean(request.form.get("node_id"))
    if not node_id or node_id not in g.node:
        flash(f'Node "{node_id}" not found.', "error")
        return redirect(url_for("home"))  # type: ignore[return-value]
    result = BFS(node_id, g.adjacency)
    return render_template("index.html", graph=g, bfs_result=result, viz_traversal=result)


@app.route("/dfs", methods=["POST"])
def dfs_traversal() -> str:
    g = load_graph()
    node_id = _clean(request.form.get("node_id"))
    if not node_id or node_id not in g.node:
        flash(f'Node "{node_id}" not found.', "error")
        return redirect(url_for("home"))  # type: ignore[return-value]
    out = DFS(node_id, g.adjacency)
    order, trace = out  # type: ignore[misc]
    return render_template(
        "index.html", graph=g, dfs_result=order, viz_traversal=order, viz_trace=trace
    )


@app.route("/dijkstra", methods=["POST"])
def dijkstra_path() -> str:
    g = load_graph()
    node_id = _clean(request.form.get("node_id"))
    if not node_id or node_id not in g.node:
        flash(f'Node "{node_id}" not found.', "error")
        return redirect(url_for("home"))  # type: ignore[return-value]
    result = Dijkstra(node_id, g.adjacency)
    distances, visit_order = result  # type: ignore[misc]
    return render_template(
        "index.html", graph=g, dijkstra_result=distances, viz_traversal=visit_order
    )


@app.route("/bellman_ford", methods=["POST"])
def bellman_ford_path() -> str:
    from algorithms.bellman_ford import bellman_ford

    g = load_graph()
    node_id = _clean(request.form.get("node_id"))
    if not node_id or node_id not in g.node:
        flash(f'Node "{node_id}" not found.', "error")
        return redirect(url_for("home"))  # type: ignore[return-value]
    result = bellman_ford(node_id, g.adjacency)
    distances, visit_order, _prev, has_neg_cycle = result  # type: ignore[misc]
    return render_template(
        "index.html",
        graph=g,
        bellman_ford_result=distances,
        bellman_ford_neg_cycle=has_neg_cycle,
        viz_traversal=visit_order,
    )


@app.route("/mst", methods=["POST"])
def mst_compute() -> str:
    from algorithms.mst import kruskal

    g = load_graph()
    mst_edges, total_w = kruskal(g.adjacency, g.directed)
    return render_template(
        "index.html",
        graph=g,
        mst_edges=mst_edges,
        mst_total=total_w,
        viz_mst_edges=mst_edges,
    )


@app.route("/scc", methods=["POST"])
def scc_compute() -> str:
    from algorithms.scc import tarjan_scc

    g = load_graph()
    if not g.directed:
        flash("SCC applies to directed graphs. Switch mode first.", "error")
        return redirect(url_for("home"))  # type: ignore[return-value]
    sccs = tarjan_scc(g.adjacency)
    return render_template("index.html", graph=g, scc_result=sccs, viz_sccs=sccs)


@app.route("/reset", methods=["POST"])
def reset() -> "Response":  # type: ignore[name-defined]
    from session_store import clear_graph

    g = load_graph()
    directed = g.directed
    clear_graph()
    from graph import Graph as G

    save_graph(G(directed))
    flash("Graph cleared (mode unchanged).", "success")
    return redirect(url_for("home"))


@app.route("/set_mode", methods=["POST"])
def set_mode() -> "Response":  # type: ignore[name-defined]
    from graph import Graph as G
    from session_store import clear_graph

    value = request.form.get("direction")
    directed = value == "Directed Graph"
    clear_graph()
    save_graph(G(directed=directed))
    flash(
        "Switched to directed graph (empty)." if directed else "Switched to undirected graph (empty).",
        "success",
    )
    return redirect(url_for("home"))


@app.route("/cycle", methods=["POST"])
def detect_cycle() -> str:
    g = load_graph()
    if g.directed:
        has = has_cycle_directed(g.adjacency)
        msg = "Cycle detected (directed)." if has else "No cycle (directed graph is acyclic so far)."
    else:
        has = has_cycle_undirected(g.adjacency)
        msg = "Cycle detected (undirected)." if has else "No cycle (forest / acyclic)."
    return render_template("index.html", graph=g, cycle_result=msg)


@app.route("/topological", methods=["POST"])
def topo_sort() -> str:
    g = load_graph()
    if not g.directed:
        flash("Topological sort applies to directed graphs. Switch mode and rebuild.", "error")
        return redirect(url_for("home"))  # type: ignore[return-value]
    order = topological_sort(g.adjacency)
    if order is None:
        return render_template(
            "index.html",
            graph=g,
            topo_result="No topological order — the graph has a directed cycle.",
            viz_traversal=[],
        )
    return render_template(
        "index.html", graph=g, topo_result=" → ".join(order), viz_traversal=order
    )

# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.errorhandler(404)
def not_found(e: Exception) -> tuple[str, int]:
    return render_template("index.html", graph=load_graph(), error_404=True), 404


@app.errorhandler(429)
def rate_limited(e: Exception) -> tuple[str, int]:
    flash("Too many requests — slow down a little.", "error")
    return render_template("index.html", graph=load_graph()), 429


@app.errorhandler(500)
def server_error(e: Exception) -> tuple[str, int]:
    logger.exception("Unhandled exception")
    return render_template("index.html", graph=load_graph(), error_500=True), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="0.0.0.0", port=port)
