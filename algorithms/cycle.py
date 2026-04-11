"""Cycle detection for directed and undirected graphs."""


def has_cycle_directed(adjacency):
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in adjacency}

    def dfs(u):
        color[u] = GRAY
        for v in adjacency.get(u, {}):
            if color[v] == GRAY:
                return True
            if color[v] == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    for n in adjacency:
        if color[n] == WHITE and dfs(n):
            return True
    return False


def has_cycle_undirected(adjacency):
    visited = set()

    def dfs(u, parent):
        visited.add(u)
        for v in adjacency.get(u, {}):
            if v == parent:
                continue
            if v in visited:
                return True
            if dfs(v, u):
                return True
        return False

    for n in adjacency:
        if n not in visited and dfs(n, None):
            return True
    return False
