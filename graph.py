"""Graph ADT backed by an adjacency map.

Nodes are arbitrary strings.  Edge weights are floats (default 1.0).
The graph is either fully directed or fully undirected — mixing is not
supported (consistent with the rest of the app).
"""

from __future__ import annotations

import json
from typing import Any


class Graph:
    """Adjacency-map graph supporting directed and undirected modes."""

    def __init__(self, directed: bool = False) -> None:
        self.directed: bool = directed
        # node presence map — value is always True; using dict for O(1) lookup
        self.node: dict[str, bool] = {}
        # adjacency[u][v] = weight
        self.adjacency: dict[str, dict[str, float]] = {}

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_node(self, node_id: str) -> bool:
        """Add *node_id*.  Returns False if it already exists."""
        if node_id in self.node:
            return False
        self.node[node_id] = True
        self.adjacency[node_id] = {}
        return True

    def add_edge(self, u: str, v: str, w: float = 1.0) -> bool:
        """Add edge u→v with weight *w*.

        Returns False (without raising) if either endpoint is not in the
        graph, so callers that skip the guard still get a detectable signal.
        Silently replacing the weight of an existing edge returns True.
        """
        if u not in self.node or v not in self.node:
            return False
        self.adjacency[u][v] = w
        if not self.directed:
            self.adjacency[v][u] = w
        return True

    def delete_node(self, node_id: str) -> bool:
        """Remove *node_id* and all incident edges.  Returns False if absent."""
        if node_id not in self.node:
            return False
        del self.node[node_id]
        del self.adjacency[node_id]
        for neighbours in self.adjacency.values():
            neighbours.pop(node_id, None)
        return True

    def delete_edge(self, u: str, v: str) -> bool:
        """Remove edge u→v.  Returns False if it does not exist."""
        if u not in self.adjacency or v not in self.adjacency.get(u, {}):
            return False
        del self.adjacency[u][v]
        if not self.directed and v in self.adjacency:
            self.adjacency[v].pop(u, None)
        return True

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_neighbors(self, node_id: str) -> dict[str, float]:
        """Return the neighbor→weight mapping for *node_id* (empty dict if absent)."""
        return self.adjacency.get(node_id, {})

    @property
    def node_count(self) -> int:
        return len(self.node)

    @property
    def edge_count(self) -> int:
        total = sum(len(nbrs) for nbrs in self.adjacency.values())
        return total if self.directed else total // 2

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict that round-trips through :meth:`from_dict`."""
        return {
            "directed": self.directed,
            "nodes": list(self.node.keys()),
            "adjacency": {
                u: {v: float(w) for v, w in nbrs.items()}
                for u, nbrs in self.adjacency.items()
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Graph:
        """Reconstruct a Graph from the dict produced by :meth:`to_dict`."""
        g = cls(directed=bool(data.get("directed", False)))
        for node_id in data.get("nodes", []):
            g.node[node_id] = True
            g.adjacency[node_id] = {}
        for u, nbrs in data.get("adjacency", {}).items():
            if u in g.node:
                for v, w in nbrs.items():
                    if v in g.node:
                        g.adjacency[u][v] = float(w)
        return g

    @classmethod
    def from_json(cls, raw: str) -> Graph:
        return cls.from_dict(json.loads(raw))

    # ------------------------------------------------------------------
    # Canvas visualization helper (unchanged contract, just type-annotated)
    # ------------------------------------------------------------------

    def to_viz_dict(self) -> dict[str, Any]:
        """Stable JSON-friendly snapshot for 2D client-side layout."""
        node_ids = sorted(self.node.keys(), key=str)
        nodes = node_ids
        edges: list[dict[str, Any]] = []
        if self.directed:
            for u in node_ids:
                for v, w in sorted(
                    self.adjacency.get(u, {}).items(), key=lambda t: str(t[0])
                ):
                    edges.append({"u": u, "v": v, "w": float(w)})
        else:
            seen: set[tuple[str, str]] = set()
            for u in node_ids:
                for v, w in sorted(
                    self.adjacency.get(u, {}).items(), key=lambda t: str(t[0])
                ):
                    key = tuple(sorted((u, v), key=str))  # type: ignore[assignment]
                    if key in seen:
                        continue
                    seen.add(key)  # type: ignore[arg-type]
                    edges.append({"u": u, "v": v, "w": float(w)})
        return {"directed": self.directed, "nodes": nodes, "edges": edges}
