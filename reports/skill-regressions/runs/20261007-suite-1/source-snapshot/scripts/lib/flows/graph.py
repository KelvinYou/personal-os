"""Layout-hint rank computation: a left-to-right column index per node,
derived from a "precedes" ordering distinct from the graph's own edge
semantics (e.g. a `depends-on` edge points target->dep, but the dependency
executes *first*, so it precedes the target for layout purposes).
"""
from __future__ import annotations

_PRECEDES_FROM_EDGE = {
    "depends-on": lambda e: (e["to"], e["from"]),   # dep precedes target
    "invokes": lambda e: (e["from"], e["to"]),      # invoker precedes invoked
    "reads": lambda e: (e["to"], e["from"]),        # data precedes the script reading it
    "writes": lambda e: (e["from"], e["to"]),       # script precedes the data it writes
    "provides": lambda e: (e["from"], e["to"]),     # submodule precedes the script consuming it
}


def compute_ranks(nodes: list[dict], edges: list[dict]) -> dict[str, int]:
    node_ids = [n["id"] for n in nodes]
    rank = {n: 0 for n in node_ids}
    pairs: set[tuple[str, str]] = set()
    for e in edges:
        fn = _PRECEDES_FROM_EDGE.get(e["kind"])
        if fn:
            pairs.add(fn(e))

    # A script that both reads and writes the same documented directory
    # (e.g. archive.py) produces a mutual pair here: (path, script) from
    # `reads` and (script, path) from `writes`. Bellman-Ford-style
    # relaxation assumes a DAG — a real 2-cycle never settles and would
    # otherwise grow every pass for the full iteration budget below.
    # Neither side of a mutual pair actually precedes the other for layout
    # purposes, so both directions are dropped rather than picking one.
    precedes = [(a, b) for a, b in pairs if (b, a) not in pairs]

    for _ in range(len(node_ids) + 1):
        changed = False
        for a, b in precedes:
            if a not in rank or b not in rank:
                continue
            if rank[b] < rank[a] + 1:
                rank[b] = rank[a] + 1
                changed = True
        if not changed:
            break

    return rank
