def DFS(node_id, adjacency):
    """
    Recursive depth-first traversal (preorder). Returns (order, trace) where
    trace[i] is {"focus": node, "stack": [...]} — the call stack when that node
    is visited (like a recursive call entering that frame).
    """
    if node_id not in adjacency:
        return None

    order = []
    trace = []
    visited = set()

    def dfs(u, ancestors):
        visited.add(u)
        stack_path = ancestors + [u]
        trace.append({"focus": u, "stack": stack_path})
        order.append(u)
        for v in sorted(adjacency[u].keys(), key=str):
            if v not in visited:
                dfs(v, stack_path)

    dfs(node_id, [])
    return order, trace
