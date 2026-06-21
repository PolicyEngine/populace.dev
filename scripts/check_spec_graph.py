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

    groups = {group["id"] for group in graph.get("groups", [])}
    if "populace_country_packages" not in groups:
        raise SystemExit("Missing Populace country-package graph group.")

    country_package_nodes = [
        node
        for node in graph["nodes"]
        if node.get("kind") == "country_package"
    ]
    countries = {node.get("symbol") for node in country_package_nodes}
    if not {"us", "uk"}.issubset(countries):
        raise SystemExit(
            "Spec graph must include production US and UK country package manifests."
        )

    country_packages = graph.get("source", {}).get("country_packages", [])
    manifest_paths = {
        package.get("manifest_path")
        for package in country_packages
    }
    package_node_paths = {
        node.get("source", {}).get("path")
        for node in country_package_nodes
    }
    missing_manifest_nodes = sorted(manifest_paths - package_node_paths)
    if missing_manifest_nodes:
        raise SystemExit(
            "Missing country package manifest node(s): "
            + ", ".join(missing_manifest_nodes)
        )

    expected_resource_paths = {
        resource
        for package in country_packages
        for resource in package.get("resources", [])
    }
    resource_node_paths = {
        node.get("source", {}).get("path")
        for node in graph["nodes"]
        if node.get("kind") == "country_resource"
    }
    missing_resource_nodes = sorted(expected_resource_paths - resource_node_paths)
    if missing_resource_nodes:
        raise SystemExit(
            "Missing country package resource node(s): "
            + ", ".join(missing_resource_nodes)
        )

    extra_resource_nodes = sorted(resource_node_paths - expected_resource_paths)
    if extra_resource_nodes:
        raise SystemExit(
            "Country package resource node(s) are not listed in source metadata: "
            + ", ".join(extra_resource_nodes)
        )

    us_resource_nodes = [
        node
        for node in graph["nodes"]
        if node.get("kind") == "country_resource"
        and node.get("source", {}).get("path", "").startswith(
            "packages/populace-build/src/populace/build/us/"
        )
    ]
    if not us_resource_nodes:
        raise SystemExit("Spec graph must include US country package resources.")

    HTMLParser().feed((ROOT / "spec.html").read_text(encoding="utf-8"))
    subprocess.run(["node", "--check", "spec.js"], cwd=ROOT, check=True)
    print(
        f"spec graph ok: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges"
    )


if __name__ == "__main__":
    main()
