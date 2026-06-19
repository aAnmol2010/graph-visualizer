# Graph Visualizer

[![CI](https://github.com/aAnmol2010/graph-visualizer/actions/workflows/ci.yml/badge.svg)](https://github.com/aAnmol2010/graph-visualizer/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/aAnmol2010/graph-visualizer/branch/main/graph/badge.svg)](https://codecov.io/gh/aAnmol2010/graph-visualizer)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Flask 3](https://img.shields.io/badge/flask-3.1.3-green.svg)](https://flask.palletsprojects.com/)

A production-grade, interactive web application for building, visualising, and animating classic graph algorithms. Built from scratch with zero dependency on graph libraries (no NetworkX), this project is designed to demonstrate robust backend architecture, REST API design, session state management, and core CS fundamentals.

## Features

- **Interactive Canvas:** Click to add nodes, drag to connect edges, alt-drag to arrange the layout.
- **Algorithm Playback:** Step-by-step animation of search traversals, shortest paths, and components.
- **Session Isolation:** Graph state is strictly tied to your session (no shared mutable globals).
- **REST API:** Fully documented JSON API (via Swagger UI) to programmatically manipulate the graph.
- **Tested:** 100+ unit and integration tests covering algorithmic edge cases and API behaviour.

---

## Supported Algorithms

All algorithms are implemented from scratch in pure Python and include detailed type hints, deterministic execution, and protection against maximum recursion depth limits.

| Algorithm | Graph Type | Time Complexity | Space Complexity | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Breadth-First Search** | Any | $\mathcal{O}(V + E)$ | $\mathcal{O}(V)$ | Level-order traversal. |
| **Depth-First Search** | Any | $\mathcal{O}(V + E)$ | $\mathcal{O}(V)$ | Preorder traversal with live call-stack tracing. |
| **Dijkstra** | Non-negative | $\mathcal{O}((V + E) \log V)$ | $\mathcal{O}(V)$ | Shortest paths from a source using a binary min-heap. |
| **Bellman-Ford** | Any | $\mathcal{O}(V \cdot E)$ | $\mathcal{O}(V)$ | Shortest paths handling negative weights & cycle detection. |
| **Kruskal (MST)** | Undirected | $\mathcal{O}(E \log E)$ | $\mathcal{O}(V)$ | Minimum Spanning Tree using Union-Find (DSU). |
| **Tarjan (SCC)** | Directed | $\mathcal{O}(V + E)$ | $\mathcal{O}(V)$ | Strongly Connected Components via iterative DFS stack. |
| **Kahn (Topo Sort)** | Directed DAG | $\mathcal{O}(V + E)$ | $\mathcal{O}(V)$ | Topological ordering via in-degree reduction. |

---

## Architecture

This application strictly separates the **Graph ADT** from the web delivery layer.

1. **State Management:** The original global `g = Graph()` anti-pattern was removed. State is scoped per-user using securely signed HTTP-only cookies (`session_store.py`).
2. **API & Routing:** HTML routes handle the frontend interaction, while a dedicated `api/v1.py` Blueprint serves JSON.
3. **Rate Limiting:** `flask-limiter` protects against simple abuse while keeping the application responsive.

### REST API Docs

The application exposes a fully documented OpenAPI specification. Start the server and navigate to:
👉 `http://localhost:5000/api/docs`

---

## Quickstart

### Option A: Local Development (Virtual Environment)

Requires Python 3.12+.

```bash
# 1. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python app.py
```
*The app will be available at http://localhost:5000*

### Option B: Docker

Requires Docker and Docker Compose.

```bash
docker-compose up --build
```
*The app will be available at http://localhost:5000*

---

## Testing

The project uses `pytest` with 100% coverage on core logic.

```bash
# Install dev dependencies
pip install pytest pytest-cov mypy ruff

# Run unit and integration tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=. --cov-report=term-missing
```

## Linting & Typing

```bash
# Type check with mypy
mypy . --ignore-missing-imports --disallow-untyped-defs

# Lint and format with Ruff
ruff check .
```