# Graph Visualizer

A **Flask** web app to build graphs interactively in the browser — toggle between directed and undirected mode, visualize the structure in a live 2D canvas, and run classic graph algorithms with animated traversal highlighting.

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square)
![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## Features

- **Add / delete nodes and weighted edges** interactively
- **Directed ↔ undirected mode** — toggle anytime (clears graph to keep adjacency consistent)
- **Live 2D canvas** — auto-layout with shuffle button; directed mode shows arrowheads
- **Breadth-first search (BFS)** — level-order traversal from any start node
- **Depth-first search (DFS)** — recursive preorder with call-stack trace
- **Dijkstra's algorithm** — single-source shortest paths via binary min-heap (`heapq`)
- **Cycle detection** — DFS coloring (directed) / DFS with parent tracking (undirected)
- **Topological sort** — Kahn's algorithm; reports a cycle if one exists
- **Flash messages** for invalid input — unknown nodes, bad weights, missing edges
- Responsive dark-theme UI

---

## Project Structure

```
graph_visualizer/
│
├── app.py                    # Flask routes and validation
├── graph.py                  # Graph ADT (adjacency map)
│
├── algorithms/
│   ├── __init__.py
│   ├── bfs.py                # Breadth-first search
│   ├── dfs.py                # Depth-first search (recursive)
│   ├── dijkstra.py           # Dijkstra with heapq
│   ├── cycle.py              # Cycle detection (directed + undirected)
│   └── topological_sort.py   # Kahn's topological sort
│
├── templates/
│   └── index.html            # Jinja2 UI template
│
├── static/
│   ├── style.css             # Dark theme styles
│   └── graph-viz.js          # Canvas-based 2D graph renderer
│
├── requirements.txt
├── Procfile                  # For Heroku / Railway
└── render.yaml               # Render Blueprint config
```

---

## Getting Started

### Prerequisites

- Python 3.10+

### Run Locally

```bash
git clone https://github.com/your-username/graph-visualizer.git
cd graph-visualizer

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt

export FLASK_DEBUG=1            # Windows: set FLASK_DEBUG=1
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## Algorithms

| Algorithm | Approach | Time Complexity |
|---|---|---|
| BFS | Queue-based level order | O(V + E) |
| DFS | Recursive preorder | O(V + E) |
| Dijkstra | Binary min-heap (`heapq`) | O((V + E) log V) |
| Cycle Detection | DFS coloring / parent tracking | O(V + E) |
| Topological Sort | Kahn's (in-degree / BFS) | O(V + E) |

---

## Deployment

### Render (recommended — free tier)

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → **New → Web Service** → connect your repo.
3. Render auto-detects `render.yaml` — just add a `SECRET_KEY` environment variable and deploy.

### Railway

1. **New project → Deploy from GitHub repo.**
2. Set the start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
3. Add `SECRET_KEY` in **Variables**.

### Heroku

```bash
heroku create your-app-name
heroku config:set SECRET_KEY=your-secret-key
git push heroku main
```

---

## Screenshots

> Add your own screenshots here.

```
docs/screenshots/home.png      — main UI with graph and algorithm output
docs/screenshots/dijkstra.png  — distances after running Dijkstra
```

---

## License

Free to use for learning and portfolio projects.