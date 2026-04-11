# Graph visualizer

A small **Flask** web app to build a graph in the browser, toggle **directed / undirected** mode, and run **BFS**, **DFS**, **Dijkstra** (binary min-heap), **cycle detection**, and **topological sort** (directed acyclic graphs). The right-hand panel shows **live nodes and edges**.

## Features

- Add and delete nodes and weighted edges
- Directed ↔ undirected mode (clears the graph when switching so the model stays consistent)
- Clear graph without changing mode
- Breadth-first and depth-first traversals from any start node
- Single-source shortest paths with Dijkstra (non-negative weights)
- Cycle check (directed: DFS coloring; undirected: DFS with parent)
- Topological order via Kahn’s algorithm (directed; reports a cycle if one exists)
- Flash messages for invalid or empty input (unknown nodes, bad weights, missing edges)
- Responsive layout with a dark theme

## Screenshots

Add your own captures here for portfolio or README polish:

1. `docs/screenshots/home.png` — main UI with sample graph and algorithm output  
2. `docs/screenshots/dijkstra.png` — distances after running Dijkstra  

Then embed in this section, for example:

```markdown
![Home](docs/screenshots/home.png)
```

## How to run locally

```bash
cd graph_visualizer
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export FLASK_DEBUG=1        # optional
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Deploy (free tier)

### Render

1. Push this repo to GitHub.  
2. In Render: **New → Web Service**, connect the repo.  
3. **Runtime:** Python 3.12 (or match `render.yaml`).  
4. **Build:** `pip install -r requirements.txt`  
5. **Start:** `gunicorn app:app --bind 0.0.0.0:$PORT`  
6. Add an environment variable **`SECRET_KEY`** (any long random string).  

You can also use the included `render.yaml` with **Blueprint** deploy.

### Railway

1. **New project → Deploy from GitHub repo.**  
2. Railway detects Python; ensure the start command is:

   `gunicorn app:app --bind 0.0.0.0:$PORT`

3. Set **`SECRET_KEY`** in **Variables**.  
4. `$PORT` is provided automatically.

## Project layout

| Path | Role |
|------|------|
| `app.py` | Flask routes, validation, flashes |
| `graph.py` | Graph ADT (adjacency map) |
| `algorithms/bfs.py` | BFS |
| `algorithms/dfs.py` | DFS (iterative) |
| `algorithms/dijkstra.py` | Dijkstra with `heapq` |
| `algorithms/cycle.py` | Cycle detection |
| `algorithms/topological_sort.py` | Kahn’s topological sort |
| `templates/index.html` | UI |
| `static/style.css` | Styling |

## License

Use freely for learning and portfolio projects.
