"""Breadth-first search.

Complexity: O(V + E) time, O(V) space.
"""

from __future__ import annotations

from collections import deque


def bfs(
    start: str,
    adjacency: dict[str, dict[str, float]],
) -> list[str] | None:
    """BFS from *start*, returning nodes in visit order.

    Returns None if *start* is not in the graph.
    Emits every visited node so the canvas can animate step-by-step.
    """
    if start not in adjacency:
        return None

    visited: set[str] = {start}
    queue: deque[str] = deque([start])
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbour in sorted(adjacency[node].keys(), key=str):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(neighbour)

    return order


# ---------------------------------------------------------------------------
# Legacy alias — keeps old import in app.py working during transition
# ---------------------------------------------------------------------------
BFS = bfs