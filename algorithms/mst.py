"""Kruskal's Minimum Spanning Tree algorithm with Union-Find.

Kruskal's algorithm finds the MST (or MSF for disconnected graphs) by
greedily adding the cheapest edge that doesn't create a cycle.

Union-Find (Disjoint Set Union) with union-by-rank and path compression
makes the cycle check nearly O(1) amortised — this data structure is a
strong interview talking point on its own.

Complexity: O(E log E) dominated by edge sort, O(α(V)) per union/find op.
"""

from __future__ import annotations


class UnionFind:
    """Union-Find with union-by-rank and path compression.

    This is the standard implementation that achieves the inverse-Ackermann
    O(α(n)) amortised per-operation complexity.
    """

    def __init__(self, nodes: list[str]) -> None:
        self.parent: dict[str, str] = {n: n for n in nodes}
        self.rank: dict[str, int] = {n: 0 for n in nodes}

    def find(self, x: str) -> str:
        """Find the representative of *x*'s component with path compression."""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # path compression
        return self.parent[x]

    def union(self, x: str, y: str) -> bool:
        """Merge *x* and *y*'s components.

        Returns True if they were in different components (edge is useful),
        False if already connected (would create a cycle).
        """
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False  # already in the same component — cycle
        # Union by rank: attach smaller tree under larger
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        return True

    def components(self) -> dict[str, list[str]]:
        """Return a mapping representative → list of nodes in that component."""
        groups: dict[str, list[str]] = {}
        for node in self.parent:
            root = self.find(node)
            groups.setdefault(root, []).append(node)
        return groups


def kruskal(
    adjacency: dict[str, dict[str, float]],
    directed: bool = False,
) -> tuple[list[tuple[str, str, float]], float]:
    """Compute the MST (or MSF) of the graph using Kruskal's algorithm.

    Works on both directed and undirected graphs by treating all edges as
    undirected for MST purposes (standard MST is defined on undirected graphs).

    Returns ``(mst_edges, total_weight)`` where *mst_edges* is a list of
    ``(u, v, weight)`` tuples in the order they were added to the MST.
    """
    nodes = list(adjacency.keys())

    # Collect edges (de-duplicate for undirected: keep canonical u < v)
    seen_edges: set[tuple[str, str]] = set()
    edges: list[tuple[float, str, str]] = []
    for u, nbrs in adjacency.items():
        for v, w in nbrs.items():
            key = (min(u, v), max(u, v))
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append((float(w), u, v))

    edges.sort()  # sort by weight ascending

    uf = UnionFind(nodes)
    mst_edges: list[tuple[str, str, float]] = []
    total_weight = 0.0

    for w, u, v in edges:
        if uf.union(u, v):  # True → no cycle → add to MST
            mst_edges.append((u, v, w))
            total_weight += w
            if len(mst_edges) == len(nodes) - 1:
                break  # MST complete for a connected graph

    return mst_edges, total_weight
