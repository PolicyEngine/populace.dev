#!/usr/bin/env python3
"""Validate that the generated /spec graph is internally consistent."""

from __future__ import annotations

import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    graph_path = ROOT / "data/spec-graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    ids = {node["id"] for node in graph["nodes"]}
    if len(ids) != len(graph["nodes"]):
        seen: set[str] = set()
        duplicates = []
        for node in graph["nodes"]:
            node_id = node["id"]
            if node_id in seen:
                duplicates.append(node_id)
            seen.add(node_id)
        print("Duplicate graph node id(s):", file=sys.stderr)
        for node_id in duplicates[:10]:
            print(f"  {node_id}", file=sys.stderr)
        raise SystemExit(1)
    missing = [
        edge
        for edge in graph["edges"]
        if edge["from"] not in ids or edge["to"] not in ids
    ]
    if missing:
        print(f"{len(missing)} graph edge(s) reference missing nodes:", file=sys.stderr)
        for edge in missing[:10]:
            print(f"  {edge}", file=sys.stderr)
        raise SystemExit(1)

    if graph.get("generated_at") is not None:
        raise SystemExit(
            "data/spec-graph.json should be deterministic; generated_at must be null "
            "unless a caller explicitly opts into a timestamp for local debugging."
        )

    repositories = graph.get("source", {}).get("repositories", {})
    for key in ("populace", "ledger"):
        repo = repositories.get(key)
        if not repo or not repo.get("commit"):
            raise SystemExit(f"Missing source commit provenance for {key}.")

    HTMLParser().feed((ROOT / "spec.html").read_text(encoding="utf-8"))
    subprocess.run(["node", "--check", "spec.js"], cwd=ROOT, check=True)
    print(
        f"spec graph ok: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges"
    )


if __name__ == "__main__":
    main()
