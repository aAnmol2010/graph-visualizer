"""Dijkstra's single-source shortest-path algorithm (non-negative weights).

Complexity: O((V + E) log V) via binary min-heap.

Key addition over the original: predecessor tracking so callers can
reconstruct the shortest path to any reachable node, not just the distance.
"""

from __future__ import annotations

import heapq


def dijkstra(
    start: str,
    adjacency: dict[str, dict[str, float]],
) -> tuple[dict[str, float], list[str], dict[str, str | None]] | None:
    """Dijkstra from *start*.

    Returns ``(distances, visit_order, prev)`` where:
    - *distances*: node → shortest distance from *start* (inf if unreachable).
    - *visit_order*: nodes in the order they were finalised (good for animation).
    - *prev*: node → preceding node on the shortest path (None for *start*).

    Returns None if *start* is not in the graph.
    """
    if start not in adjacency:
        return None

    distances: dict[str, float] = {node: float("inf") for node in adjacency}
    distances[start] = 0.0
    prev: dict[str, str | None] = {node: None for node in adjacency}

    heap: list[tuple[float, str]] = [(0.0, start)]
    visited: set[str] = set()
    visit_order: list[str] = []

    while heap:
        current_dist, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        visit_order.append(node)

        for neighbour, weight in adjacency[node].items():
            w = float(weight)
            new_dist = current_dist + w
            if new_dist < distances[neighbour]:
                distances[neighbour] = new_dist
                prev[neighbour] = node
                heapq.heappush(heap, (new_dist, neighbour))

    return distances, visit_order, prev


def reconstruct_path(prev: dict[str, str | None], target: str) -> list[str] | None:
    """Walk *prev* backwards from *target* to build the shortest path.

    Returns the path as a list from source → target, or None if *target*
    is unreachable (i.e., its prev chain never reaches a node with prev=None
    that is the source).
    """
    path: list[str] = []
    node: str | None = target
    while node is not None:
        path.append(node)
        node = prev.get(node)
    path.reverse()
    # If path[0] has no predecessor in prev it is the source; if it is
    # still "inf" distance the target was unreachable.
    return path if len(path) > 1 or path[0] == target else None


# Legacy alias — preserves the original (distances, visit_order) two-tuple
# contract that the old app.py route relies on.
def Dijkstra(  # noqa: N802
    start: str,
    adjacency: dict[str, dict[str, float]],
) -> tuple[dict[str, float], list[str]] | None:
    result = dijkstra(start, adjacency)
    if result is None:
        return None
    distances, visit_order, _ = result
    return distances, visit_order