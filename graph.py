class Graph:
    def __init__(self,directed=False):
        self.directed = directed
        self.node = {}
        self.adjacency = {}
    
    def add_node(self,node_id):
        if node_id not in self.node:
            self.node[node_id] = True
            self.adjacency[node_id] = {}

    def add_edge(self,u,v,w=1):
        if u in self.node and v in self.node:
            self.adjacency[u][v] = w 
            if not self.directed:
                self.adjacency[v][u] = w
    
    def delete_node(self,node_id):
        if node_id in self.node:
            del self.node[node_id]
            del self.adjacency[node_id]
            for neighbours in self.adjacency.values():
                neighbours.pop(node_id, None)

    def delete_edge(self,u,v):
        if u in self.adjacency:
            self.adjacency[u].pop(v,None)
        if not self.directed and v in self.adjacency:
            self.adjacency[v].pop(u,None)

    def get_neighbors(self,node_id):
        return self.adjacency.get(node_id,{})

    def to_viz_dict(self):
        """Stable JSON-friendly snapshot for 2D client-side layout."""
        node_ids = sorted(self.node.keys(), key=str)
        nodes = [{"id": nid} for nid in node_ids]
        edges = []
        if self.directed:
            for u in node_ids:
                for v, w in sorted(
                    self.adjacency.get(u, {}).items(), key=lambda t: str(t[0])
                ):
                    edges.append({"from": u, "to": v, "w": float(w)})
        else:
            seen = set()
            for u in node_ids:
                for v, w in sorted(
                    self.adjacency.get(u, {}).items(), key=lambda t: str(t[0])
                ):
                    key = tuple(sorted((u, v), key=str))
                    if key in seen:
                        continue
                    seen.add(key)
                    edges.append({"from": u, "to": v, "w": float(w)})
        return {"directed": self.directed, "nodes": nodes, "edges": edges}

