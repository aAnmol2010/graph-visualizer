"""Cycle detection for directed and undirected graphs.

Both implementations use **iterative** DFS to avoid Python's default
recursion limit (~1 000 frames), which would crash on graphs with
more than ~500 nodes in a chain.

Complexity: O(V + E) time, O(V) space.
"""

from __future__ import annotations


def has_cycle_directed(adjacency: dict[str, dict[str, float]]) -> bool:
    """Detect a cycle in a directed graph using iterative DFS with 3-colour marking.

    WHITE (0) = unvisited, GRAY (1) = on current DFS path, BLACK (2) = done.
    A back-edge to a GRAY node means a cycle.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in adjacency}

    for start in adjacency:
        if color[start] != WHITE:
            continue

        # Iterative DFS — stack holds (node, iterator-over-neighbours)
        stack: list[tuple[str, iter]] = [(start, iter(adjacency.get(start, {})))]
        color[start] = GRAY

        while stack:
            node, neighbours = stack[-1]
            try:
                v = next(neighbours)
                if color[v] == GRAY:
                    return True
                if color[v] == WHITE:
                    color[v] = GRAY
                    stack.append((v, iter(adjacency.get(v, {}))))
            except StopIteration:
                color[node] = BLACK
                stack.pop()

    return False


def has_cycle_undirected(adjacency: dict[str, dict[str, float]]) -> bool:
    """Detect a cycle in an undirected graph using iterative DFS with parent tracking."""
    visited: set[str] = set()

    for start in adjacency:
        if start in visited:
            continue

        # stack holds (node, parent)
        stack: list[tuple[str, str | None]] = [(start, None)]

        while stack:
            node, parent = stack.pop()
            if node in visited:
                # Reached an already-visited node via a non-parent edge.
                return True
            visited.add(node)
            for v in adjacency.get(node, {}):
                if v == parent:
                    continue
                if v in visited:
                    return True
                stack.append((v, node))

    return False
