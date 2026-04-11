from collections import deque


def BFS(node_id, adjacency):
    if node_id not in adjacency:
        return None
    source = node_id
    visited = set()
    visited.add(source)
    q = deque([source])
    print_list = []
    while q:
        node = q.popleft()
        print_list.append(node)
        for nei_node in adjacency[node]:
            if nei_node not in visited:
                visited.add(nei_node)
                q.append(nei_node)
    return print_list