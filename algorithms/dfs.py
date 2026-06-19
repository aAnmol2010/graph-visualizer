"""Depth-first search — recursive preorder with call-stack trace.

Complexity: O(V + E) time, O(V) space (call stack depth).
"""

from __future__ import annotations


def dfs(
    start: str,
    adjacency: dict[str, dict[str, float]],
) -> tuple[list[str], list[dict]] | None:
    """Recursive DFS from *start*.

    Returns ``(order, trace)`` where:
    - *order*: nodes in preorder visit sequence.
    - *trace*: one entry per visited node with keys
      ``{"focus": str, "stack": list[str]}`` — the call-stack snapshot
      when that node was entered.  Used by the canvas to animate the
      recursive call stack live.

    Returns None if *start* is absent from the graph.
    """
    if start not in adjacency:
        return None

    order: list[str] = []
    trace: list[dict] = []
    visited: set[str] = set()

    def _dfs(u: str, ancestors: list[str]) -> None:
        visited.add(u)
        stack_path = ancestors + [u]
        trace.append({"focus": u, "stack": stack_path})
        order.append(u)
        for v in sorted(adjacency[u].keys(), key=str):
            if v not in visited:
                _dfs(v, stack_path)

    _dfs(start, [])
    return order, trace


# Legacy alias
DFS = dfs
