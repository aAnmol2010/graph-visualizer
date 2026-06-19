"""Bellman-Ford single-source shortest-path algorithm.

Unlike Dijkstra, Bellman-Ford:
- Handles **negative edge weights** correctly.
- Detects **negative-weight cycles** (a cycle whose total weight < 0,
  making "shortest path" undefined).
- Is slower: O(V · E) time vs Dijkstra's O((V+E) log V).

This makes the three algorithms a coherent story to tell in interviews:
  BFS        — unweighted graphs
  Dijkstra   — weighted, non-negative edges
  Bellman-Ford — weighted, negative edges allowed

Complexity: O(V · E) time, O(V) space.
"""

from __future__ import annotations


def bellman_ford(
    start: str,
    adjacency: dict[str, dict[str, float]],
) -> tuple[dict[str, float], list[str], dict[str, str | None], bool] | None:
    """Bellman-Ford from *start*.

    Returns ``(distances, visit_order, prev, has_negative_cycle)`` where:
    - *distances*: node → best known distance (inf if unreachable).
    - *visit_order*: order in which nodes were first relaxed to a finite
      distance (used for canvas animation).
    - *prev*: predecessor map for path reconstruction.
    - *has_negative_cycle*: True if a negative cycle is reachable from *start*.

    Returns None if *start* is absent from the graph.
    """
    if start not in adjacency:
        return None

    nodes = list(adjacency.keys())
    n = len(nodes)

    distances: dict[str, float] = {node: float("inf") for node in nodes}
    distances[start] = 0.0
    prev: dict[str, str | None] = {node: None for node in nodes}

    # Track animation order: nodes are added to visit_order the first time
    # their distance becomes finite (i.e. they become reachable).
    visit_order: list[str] = [start]
    finalised: set[str] = {start}

    # Build a flat edge list for efficient iteration.
    edges: list[tuple[str, str, float]] = [
        (u, v, float(w))
        for u, nbrs in adjacency.items()
        for v, w in nbrs.items()
    ]

    # Relax all edges V-1 times.
    for _ in range(n - 1):
        updated = False
        for u, v, w in edges:
            if distances[u] == float("inf"):
                continue
            candidate = distances[u] + w
            if candidate < distances[v]:
                distances[v] = candidate
                prev[v] = u
                updated = True
                if v not in finalised:
                    finalised.add(v)
                    visit_order.append(v)
        if not updated:
            break  # Early exit: no relaxation happened, converged.

    # V-th relaxation pass: if any distance still improves, a negative cycle
    # is reachable.
    has_negative_cycle = False
    for u, v, w in edges:
        if distances[u] == float("inf"):
            continue
        if distances[u] + w < distances[v]:
            has_negative_cycle = True
            break

    return distances, visit_order, prev, has_negative_cycle


def reconstruct_path(
    prev: dict[str, str | None],
    target: str,
    max_steps: int = 10_000,
) -> list[str] | None:
    """Walk *prev* backwards from *target*.

    *max_steps* guards against infinite loops in case of a negative cycle
    that corrupted the prev map.  Returns None if unreachable.
    """
    path: list[str] = []
    node: str | None = target
    steps = 0
    while node is not None and steps < max_steps:
        path.append(node)
        node = prev.get(node)
        steps += 1
    if steps >= max_steps:
        return None  # negative cycle
    path.reverse()
    return path
