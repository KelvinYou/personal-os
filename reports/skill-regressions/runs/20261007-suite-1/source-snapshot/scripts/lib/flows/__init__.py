"""Structural flow-graph extraction: Makefile targets, script read/write edges,
submodule touchpoints. See scripts/flow_graph.py for the CLI entrypoint."""

from .doc_paths import agents_md_paths
from .hashing import compute_input_hash
from .makefile_parser import parse_makefile
from .annotations import read_flow_group
from .path_scanner import scan_script
from .submodules import submodule_nodes_and_edges
from .graph import compute_ranks

__all__ = [
    "agents_md_paths",
    "compute_input_hash",
    "parse_makefile",
    "read_flow_group",
    "scan_script",
    "submodule_nodes_and_edges",
    "compute_ranks",
]
