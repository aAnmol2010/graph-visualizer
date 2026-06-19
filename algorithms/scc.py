"""Tarjan's Strongly Connected Components algorithm — iterative.

A Strongly Connected Component (SCC) is a maximal set of nodes where every
node is reachable from every other node.  Applications include:
  - Detecting circular dependencies (build systems, package managers)
  - Finding 2-SAT solutions
  - Condensation graphs for DAG reductions

The recursive version of Tarjan's hits Python's recursion limit on graphs
with > ~500 nodes, so this implementation is fully iterative using an
explicit stack that simulates the call stack.

Complexity: O(V + E) time, O(V) space.
"""

from __future__ import annotations

from collections import defaultdict


def tarjan_scc(
    adjacency: dict[str, dict[str, float]],
) -> list[list[str]]:
    """Compute all SCCs using Tarjan's iterative algorithm.

    Returns a list of SCCs, each SCC is a list of node IDs.
    SCCs are returned in reverse topological order of the condensation DAG
    (i.e., a sink SCC comes before its predecessors).
    """
    index_counter = [0]
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: dict[str, bool] = defaultdict(bool)
    stack: list[str] = []
    sccs: list[list[str]] = []

    # Iterative Tarjan using an explicit call-stack simulation.
    # Each frame: (node, iterator-over-neighbours, entry-index)
    call_stack: list[tuple[str, "iter[str]"]] = []

    def _start(v: str) -> None:
        idx = index_counter[0]
        index[v] = idx
        lowlink[v] = idx
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True
        call_stack.append((v, iter(adjacency.get(v, {}))))

    for node in adjacency:
        if node in index:
            continue
        _start(node)

        while call_stack:
            v, neighbours = call_stack[-1]
            advanced = False
            for w in neighbours:
                if w not in index:
                    # Tree edge — recurse into w
                    _start(w)
                    advanced = True
                    break
                if on_stack[w]:
                    # Back edge / cross edge to node on stack
                    lowlink[v] = min(lowlink[v], index[w])
            else:
                advanced = False

            if not advanced:
                # All neighbours of v processed — pop frame
                call_stack.pop()
                if call_stack:
                    parent, _ = call_stack[-1]
                    lowlink[parent] = min(lowlink[parent], lowlink[v])

                # v is the root of an SCC if lowlink[v] == index[v]
                if lowlink[v] == index[v]:
                    scc: list[str] = []
                    while True:
                        w = stack.pop()
                        on_stack[w] = False
                        scc.append(w)
                        if w == v:
                            break
                    sccs.append(scc)

    return sccs
