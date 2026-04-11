import heapq


def Dijkstra(start, adjacency):
    if start not in adjacency:
        return None
    distances = {node: float("inf") for node in adjacency}
    distances[start] = 0
    heap = [(0, start)]
    visited = set()
    visit_order = []
    while heap:
        current_dist, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        visit_order.append(node)
        for neighbor, weight in adjacency[node].items():
            weight = float(weight)
            new_dist = current_dist + weight
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                heapq.heappush(heap, (new_dist, neighbor))

    return distances, visit_order