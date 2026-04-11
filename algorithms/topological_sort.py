"""Kahn's algorithm for topological ordering of a directed graph."""

from collections import deque


def topological_sort(adjacency):
    if not adjacency:
        return []

    in_degree = {node: 0 for node in adjacency}
    for u in adjacency:
        for v in adjacency[u]:
            in_degree[v] = in_degree.get(v, 0) + 1

    queue = deque(n for n in adjacency if in_degree[n] == 0)
    order = []

    while queue:
        u = queue.popleft()
        order.append(u)
        for v in adjacency.get(u, {}):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    if len(order) != len(adjacency):
        return None
    return order
