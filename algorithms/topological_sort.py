"""Kahn's algorithm for topological ordering of a directed graph.

Complexity: O(V + E) time, O(V) space.
"""

from __future__ import annotations

from collections import deque


def topological_sort(
    adjacency: dict[str, dict[str, float]],
) -> list[str] | None:
    """Return a topological ordering of *adjacency*, or None if a cycle exists.

    Uses Kahn's BFS-based algorithm (in-degree reduction).  Deterministic:
    among nodes with in-degree 0 at the same step, processes them in sorted
    order so the output is reproducible for tests.
    """
    if not adjacency:
        return []

    in_degree: dict[str, int] = {node: 0 for node in adjacency}
    for u in adjacency:
        for v in adjacency[u]:
            in_degree[v] = in_degree.get(v, 0) + 1

    queue: deque[str] = deque(sorted(n for n in adjacency if in_degree[n] == 0))
    order: list[str] = []

    while queue:
        u = queue.popleft()
        order.append(u)
        for v in sorted(adjacency.get(u, {})):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    if len(order) != len(adjacency):
        return None  # cycle detected
    return order
