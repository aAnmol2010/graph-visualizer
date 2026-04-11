import os

from flask import Flask, flash, redirect, render_template, request, url_for

from algorithms.bfs import BFS
from algorithms.cycle import has_cycle_directed, has_cycle_undirected
from algorithms.dfs import DFS
from algorithms.dijkstra import Dijkstra
from algorithms.topological_sort import topological_sort
from graph import Graph

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-in-production")


@app.template_filter("fmt_dist")
def fmt_dist(d):
    if d == float("inf"):
        return "∞"
    fd = float(d)
    if fd.is_integer():
        return str(int(fd))
    return str(d)


@app.context_processor
def inject_graph_viz():
    return {"graph_viz": g.to_viz_dict()}


g = Graph()


def _clean(s):
    return (s or "").strip()


def _require_node(graph, node_id, label="Node"):
    nid = _clean(node_id)
    if not nid:
        flash(f"{label} cannot be empty.", "error")
        return None
    if nid not in graph.node:
        flash(f'Unknown node "{nid}". Add the node first or check spelling.', "error")
        return None
    return nid


def _require_two_nodes(graph, u_raw, v_raw):
    u = _require_node(graph, u_raw, "Source node")
    if u is None:
        return None, None
    v = _require_node(graph, v_raw, "Target node")
    if v is None:
        return None, None
    return u, v


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", graph=g)


@app.route("/add_node", methods=["POST"])
def add_n():
    node_id = _clean(request.form.get("node_id"))
    if not node_id:
        flash("Node id cannot be empty.", "error")
        return redirect(url_for("home"))
    if node_id in g.node:
        flash(f'Node "{node_id}" already exists.', "error")
        return redirect(url_for("home"))
    g.add_node(node_id)
    flash(f'Added node "{node_id}".', "success")
    return redirect(url_for("home"))


@app.route("/add_edge", methods=["POST"])
def add_e():
    u, v = _require_two_nodes(g, request.form.get("u"), request.form.get("v"))
    if u is None:
        return redirect(url_for("home"))
    w_raw = request.form.get("w")
    try:
        w = float(w_raw) if _clean(w_raw) else 1.0
    except (TypeError, ValueError):
        flash("Weight must be a number.", "error")
        return redirect(url_for("home"))
    if w < 0:
        flash("Use non-negative weights for Dijkstra.", "error")
        return redirect(url_for("home"))
    g.add_edge(u, v, w)
    flash(f'Edge {u} → {v} (weight {w}) added.', "success")
    return redirect(url_for("home"))


@app.route("/delete_node", methods=["POST"])
def del_n():
    node_id = _require_node(g, request.form.get("node_id"), "Node")
    if node_id is None:
        return redirect(url_for("home"))
    g.delete_node(node_id)
    flash(f'Removed node "{node_id}" and its incident edges.', "success")
    return redirect(url_for("home"))


@app.route("/delete_edge", methods=["POST"])
def del_e():
    u, v = _require_two_nodes(g, request.form.get("u"), request.form.get("v"))
    if u is None:
        return redirect(url_for("home"))
    if v not in g.adjacency.get(u, {}):
        flash(f'No edge from "{u}" to "{v}".', "error")
        return redirect(url_for("home"))
    g.delete_edge(u, v)
    flash(f'Removed edge {u} → {v}.', "success")
    return redirect(url_for("home"))


@app.route("/bfs", methods=["POST"])
def bfs_traversal():
    node_id = _require_node(g, request.form.get("node_id"), "Start node")
    if node_id is None:
        return redirect(url_for("home"))
    result = BFS(node_id, g.adjacency)
    return render_template(
        "index.html",
        graph=g,
        bfs_result=result,
        viz_traversal=result,
    )


@app.route("/dfs", methods=["POST"])
def dfs_traversal():
    node_id = _require_node(g, request.form.get("node_id"), "Start node")
    if node_id is None:
        return redirect(url_for("home"))
    out = DFS(node_id, g.adjacency)
    order, trace = out
    return render_template(
        "index.html",
        graph=g,
        dfs_result=order,
        viz_traversal=order,
        viz_trace=trace,
    )


@app.route("/dijkstra", methods=["POST"])
def dijkstra_path():
    node_id = _require_node(g, request.form.get("node_id"), "Start node")
    if node_id is None:
        return redirect(url_for("home"))
    distances, visit_order = Dijkstra(node_id, g.adjacency)
    return render_template(
        "index.html",
        graph=g,
        dijkstra_result=distances,
        viz_traversal=visit_order,
    )


@app.route("/reset", methods=["POST"])
def reset():
    global g
    g = Graph(g.directed)
    flash("Graph cleared (mode unchanged).", "success")
    return redirect(url_for("home"))


@app.route("/set_mode", methods=["POST"])
def set_mode():
    global g
    value = request.form.get("direction")
    directed = value == "Directed Graph"
    g = Graph(directed=directed)
    flash(
        "Switched to directed graph (empty)." if directed else "Switched to undirected graph (empty).",
        "success",
    )
    return redirect(url_for("home"))


@app.route("/cycle", methods=["POST"])
def detect_cycle():
    if g.directed:
        has = has_cycle_directed(g.adjacency)
        msg = "Cycle detected (directed)." if has else "No cycle (directed graph is acyclic so far)."
    else:
        has = has_cycle_undirected(g.adjacency)
        msg = "Cycle detected (undirected)." if has else "No cycle (forest / acyclic)."
    return render_template("index.html", graph=g, cycle_result=msg)


@app.route("/topological", methods=["POST"])
def topo_sort():
    if not g.directed:
        flash("Topological sort applies to directed graphs. Switch mode and rebuild the graph.", "error")
        return redirect(url_for("home"))
    order = topological_sort(g.adjacency)
    if order is None:
        return render_template(
            "index.html",
            graph=g,
            topo_result="No topological order — the graph has a directed cycle.",
            viz_traversal=[],
        )
    return render_template(
        "index.html",
        graph=g,
        topo_result=" → ".join(order),
        viz_traversal=order,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="0.0.0.0", port=port)
