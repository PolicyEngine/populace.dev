#!/usr/bin/env python3
"""Generate the /spec concept graph from production Populace/Ledger contracts.

The web page should not own a parallel architecture model. This script reads the
public production source files that define the current contracts, extracts
classes, dataclass fields, constants, and gate functions, then writes the graph
JSON consumed by spec.js.

By default it reads PolicyEngine/populace@main and PolicyEngine/arch-data@main
from GitHub raw URLs. Set POPULACE_REPO_DIR or LEDGER_REPO_DIR to use a local
checkout instead while developing.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
COMMIT_BY_REPO_KEY: dict[str, str] = {}


@dataclass(frozen=True)
class SourceRepo:
    key: str
    label: str
    github_repo: str
    ref: str
    local_env: str
    default_local: str


@dataclass(frozen=True)
class SourceFile:
    repo: str
    path: str
    group: str
    module_label: str


REPOS = {
    "populace": SourceRepo(
        key="populace",
        label="Populace",
        github_repo="PolicyEngine/populace",
        ref=os.environ.get("POPULACE_REF", "main"),
        local_env="POPULACE_REPO_DIR",
        default_local="/Users/maxghenis/PolicyEngine/populace",
    ),
    "ledger": SourceRepo(
        key="ledger",
        label="Ledger",
        github_repo="PolicyEngine/arch-data",
        ref=os.environ.get("LEDGER_REF", "main"),
        local_env="LEDGER_REPO_DIR",
        default_local="/Users/maxghenis/.codex-worktrees/ledger-target-contracts-20260620",
    ),
}


SOURCE_FILES = (
    SourceFile(
        "ledger",
        "arch/core.py",
        "ledger_facts",
        "Ledger fact schema",
    ),
    SourceFile(
        "ledger",
        "arch/sources/specs.py",
        "ledger_sources",
        "Ledger source record specs",
    ),
    SourceFile(
        "ledger",
        "arch/source_package.py",
        "ledger_sources",
        "Ledger source packages",
    ),
    SourceFile(
        "ledger",
        "arch/consumer_contract.py",
        "ledger_contracts",
        "Ledger consumer contracts",
    ),
    SourceFile(
        "populace",
        "packages/populace-frame/src/populace/frame/schema.py",
        "populace_frame",
        "Populace frame schema",
    ),
    SourceFile(
        "populace",
        "packages/populace-frame/src/populace/frame/weights.py",
        "populace_frame",
        "Populace weights",
    ),
    SourceFile(
        "populace",
        "packages/populace-build/src/populace/build/plan.py",
        "populace_build",
        "Populace build plan",
    ),
    SourceFile(
        "populace",
        "packages/populace-calibrate/src/populace/calibrate/target.py",
        "populace_calibration",
        "Populace target constraints",
    ),
    SourceFile(
        "populace",
        "packages/populace-calibrate/src/populace/calibrate/registry.py",
        "populace_calibration",
        "Populace target registry",
    ),
    SourceFile(
        "populace",
        "packages/populace-calibrate/src/populace/calibrate/solve.py",
        "populace_calibration",
        "Populace calibration solver",
    ),
    SourceFile(
        "populace",
        "packages/populace-build/src/populace/build/gates.py",
        "populace_release",
        "Populace release gates",
    ),
    SourceFile(
        "populace",
        "packages/populace-data/src/populace/data/registry.py",
        "populace_release",
        "Populace published datasets",
    ),
)


GROUPS = (
    {"id": "ledger_sources", "label": "Ledger sources"},
    {"id": "ledger_facts", "label": "Ledger facts"},
    {"id": "ledger_contracts", "label": "Ledger contracts"},
    {"id": "populace_frame", "label": "Populace frame"},
    {"id": "populace_build", "label": "Populace build"},
    {"id": "populace_calibration", "label": "Populace calibration"},
    {"id": "populace_release", "label": "Populace release"},
)


SHAPE_LEGEND = (
    {"shape": "input", "label": "source/input contract"},
    {"shape": "rule", "label": "compiled rule or function"},
    {"shape": "attribute", "label": "declared field or parameter"},
    {"shape": "output", "label": "release/output contract"},
)


EXTRA_CLASSES = {
    "StagePlan",
    "TargetRegistry",
    "TargetSet",
}


GATE_FUNCTIONS = {
    "calibrate",
    "formula_owned_export_gate",
    "exported_nonzero_gate",
    "parity_gate",
    "support_gate",
    "aggregate_admin_gate",
    "per_family_fit_gate",
    "relative_error_loss",
}


CONSTANTS = {
    "ALLOWED_PERIOD_TYPES",
    "ALLOWED_GEOGRAPHY_LEVELS",
    "ALLOWED_ENTITIES",
    "ALLOWED_AGGREGATIONS",
    "ALLOWED_CONSTRAINT_OPERATORS",
    "ALLOWED_CONCEPT_RELATIONS",
    "FACT_KEY_PREFIX",
    "CONSUMER_FACT_SCHEMA_VERSION",
    "SOURCE_PACKAGE_ALIASES",
    "SOURCE_ARTIFACT_CACHE_ENV",
    "AGGREGATIONS",
    "_FORMAT_KEY",
    "_FORMAT_VERSION",
}


RELATIONSHIP_EDGES = (
    ("SourcePackage", "SourceArtifactSpec", "owns artifact metadata"),
    ("SourcePackage", "SourceRecordSetSpec", "expands compact records"),
    ("SourceRecordSetSpec", "SourceRecordSetRow", "groups rows"),
    ("SourceRecordSetSpec", "SourceRecordSetMeasure", "groups measures"),
    ("SourceRecordSpec", "CellSelectorSpec", "selects cells"),
    ("SourceRecord", "SourceRecordSpec", "resolves spec"),
    ("AggregateFact", "PeriodDimension", "declares period"),
    ("AggregateFact", "GeographyDimension", "declares geography"),
    ("AggregateFact", "EntityDimension", "declares entity"),
    ("AggregateFact", "Measure", "declares measure"),
    ("AggregateFact", "Aggregation", "declares aggregation"),
    ("AggregateFact", "SourceProvenance", "carries provenance"),
    ("AggregateFact", "AggregateConstraint", "scopes universe"),
    ("AggregateFact", "SourceRecordLayout", "keeps source layout"),
    ("ConsumerFactContractReport", "ConsumerFactContractIssue", "reports issues"),
    ("StagePlan", "Stage", "runs ordered stages"),
    ("Stage", "DonorSpec", "uses donor"),
    ("StagePlan", "StageRecord", "emits records"),
    ("EntitySchema", "LinkSpec", "declares links"),
    ("TargetRegistry", "TargetSpec", "stores declared facts"),
    ("TargetRegistry", "TargetSet", "compiles solver surface"),
    ("TargetSpec", "Target", "compiles target"),
    ("TargetSet", "Target", "orders constraints"),
    ("calibrate", "TargetSet", "solves target set"),
    ("aggregate_admin_gate", "TargetSpec", "checks anchors"),
    ("aggregate_admin_gate", "GateResult", "returns verdict"),
    ("per_family_fit_gate", "GateResult", "returns verdict"),
    ("support_gate", "GateResult", "returns verdict"),
    ("parity_gate", "GateResult", "returns verdict"),
    ("exported_nonzero_gate", "GateResult", "returns verdict"),
    ("formula_owned_export_gate", "GateResult", "returns verdict"),
    ("GateReport", "GateResult", "aggregates verdicts"),
    ("DatasetSpec", "REGISTRY", "is published through"),
)


def main() -> None:
    repo_meta = {key: repo_metadata(repo) for key, repo in REPOS.items()}
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    symbol_to_id: dict[str, str] = {}
    source_texts: dict[str, str] = {}

    for source in SOURCE_FILES:
        text = read_source(source)
        source_texts[f"{source.repo}:{source.path}"] = text
        tree = ast.parse(text)
        line_starts = line_start_index(text)
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and include_class(node):
                item = class_node(source, node, line_starts)
                symbol_to_id[node.name] = item["id"]
                nodes.append(item)
            elif isinstance(node, ast.FunctionDef) and node.name in GATE_FUNCTIONS:
                item = function_node(source, node, line_starts)
                symbol_to_id[node.name] = item["id"]
                nodes.append(item)
            elif is_constant_assignment(node):
                item = constant_node(source, node, line_starts)
                symbol_to_id[item["symbol"]] = item["id"]
                nodes.append(item)

    nodes, edges = add_attribute_nodes(nodes, edges)
    edges.extend(type_reference_edges(nodes, symbol_to_id))
    edges.extend(relationship_edges(symbol_to_id))
    edges = dedupe_edges(edges)
    nodes = layout_nodes(nodes, edges)

    graph = {
        "title": "Production spec graph",
        "description": (
            "Generated from production Populace and Ledger source contracts; "
            "nodes and attributes are extracted from code, not maintained in the page."
        ),
        "generated_at": os.environ.get("SPEC_GRAPH_GENERATED_AT"),
        "source": {
            "repositories": repo_meta,
            "files": [source.__dict__ for source in SOURCE_FILES],
        },
        "canvas": canvas_size(nodes),
        "stats": graph_stats(nodes, edges, repo_meta),
        "groups": list(GROUPS),
        "shapeLegend": list(SHAPE_LEGEND),
        "defaultNode": symbol_to_id.get("AggregateFact") or nodes[0]["id"],
        "nodes": nodes,
        "edges": edges,
    }
    output = ROOT / "data/spec-graph.json"
    output.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {output.relative_to(ROOT)} with "
        f"{len(nodes)} nodes and {len(edges)} edges"
    )


def repo_metadata(repo: SourceRepo) -> dict[str, str]:
    local = Path(os.environ.get(repo.local_env, repo.default_local)).expanduser()
    if os.environ.get(repo.local_env) and local.exists():
        commit = git(local, "rev-parse", "HEAD")
        branch = git(local, "rev-parse", "--abbrev-ref", "HEAD")
        status = git(local, "status", "--short")
        COMMIT_BY_REPO_KEY[repo.key] = commit
        return {
            "label": repo.label,
            "repository": repo.github_repo,
            "ref": branch,
            "commit": commit,
            "source": str(local),
            "dirty": "true" if status else "false",
        }
    commit = ls_remote(repo.github_repo, repo.ref)
    COMMIT_BY_REPO_KEY[repo.key] = commit
    return {
        "label": repo.label,
        "repository": repo.github_repo,
        "ref": repo.ref,
        "commit": commit,
        "source": f"https://github.com/{repo.github_repo}/tree/{commit}",
        "dirty": "false",
    }


def read_source(source: SourceFile) -> str:
    repo = REPOS[source.repo]
    local_env = os.environ.get(repo.local_env)
    if local_env:
        path = Path(local_env).expanduser() / source.path
        if path.exists():
            return path.read_text(encoding="utf-8")
    url = f"https://raw.githubusercontent.com/{repo.github_repo}/{repo.ref}/{source.path}"
    with urlopen(url, timeout=20) as response:
        return response.read().decode("utf-8")


def git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def ls_remote(repo: str, ref: str) -> str:
    output = subprocess.check_output(
        ["git", "ls-remote", f"https://github.com/{repo}.git", f"refs/heads/{ref}"],
        text=True,
    ).strip()
    return output.split()[0] if output else ref


def line_start_index(text: str) -> list[int]:
    starts = [0]
    for match in re.finditer("\n", text):
        starts.append(match.end())
    return starts


def source_url(repo_key: str, path: str, lineno: int) -> str:
    repo = REPOS[repo_key]
    commit = COMMIT_BY_REPO_KEY.get(repo_key) or ls_remote(repo.github_repo, repo.ref)
    return f"https://github.com/{repo.github_repo}/blob/{commit}/{path}#L{lineno}"


def include_class(node: ast.ClassDef) -> bool:
    return has_dataclass_decorator(node) or node.name in EXTRA_CLASSES


def has_dataclass_decorator(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
            return True
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name) and func.id == "dataclass":
                return True
    return False


def is_constant_assignment(node: ast.AST) -> bool:
    if isinstance(node, ast.Assign):
        return any(isinstance(target, ast.Name) and target.id in CONSTANTS for target in node.targets)
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id in CONSTANTS
    return False


def class_node(source: SourceFile, node: ast.ClassDef, line_starts: list[int]) -> dict[str, Any]:
    fields = class_fields(node)
    methods = [
        child.name
        for child in node.body
        if isinstance(child, ast.FunctionDef) and not child.name.startswith("_")
    ]
    summary = first_sentence(ast.get_docstring(node) or "")
    attrs = [f"{name}: {annotation}" for name, annotation in fields]
    if not attrs and methods:
        attrs = [f"method: {name}()" for name in methods[:14]]
    shape = "rule"
    if source.group.startswith("ledger"):
        shape = "input"
    if node.name in {"DatasetSpec", "GateReport", "ConsumerFactExportReport"}:
        shape = "output"
    return {
        "id": node_id(source, node.name),
        "symbol": node.name,
        "title": titleize(node.name),
        "kind": "dataclass" if has_dataclass_decorator(node) else "class",
        "group": source.group,
        "shape": shape,
        "summary": summary or f"{node.name} from {source.module_label}.",
        "attributes": attrs,
        "annotationRefs": sorted(annotation_refs([annotation for _, annotation in fields])),
        "source": node_source(source, node.lineno),
    }


def function_node(source: SourceFile, node: ast.FunctionDef, line_starts: list[int]) -> dict[str, Any]:
    args = []
    annotations = []
    for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
        if arg.arg in {"self", "cls"}:
            continue
        annotation = ast.unparse(arg.annotation) if arg.annotation else "Any"
        annotations.append(annotation)
        args.append(f"{arg.arg}: {annotation}")
    if node.returns:
        annotations.append(ast.unparse(node.returns))
        args.append(f"returns: {ast.unparse(node.returns)}")
    return {
        "id": node_id(source, node.name),
        "symbol": node.name,
        "title": titleize(node.name),
        "kind": "function",
        "group": source.group,
        "shape": "rule",
        "summary": first_sentence(ast.get_docstring(node) or "") or f"{node.name} function.",
        "attributes": args,
        "annotationRefs": sorted(annotation_refs(annotations)),
        "source": node_source(source, node.lineno),
    }


def constant_node(source: SourceFile, node: ast.Assign | ast.AnnAssign, line_starts: list[int]) -> dict[str, Any]:
    name = ""
    value: ast.AST | None = None
    lineno = getattr(node, "lineno", 1)
    if isinstance(node, ast.Assign):
        name = next(target.id for target in node.targets if isinstance(target, ast.Name))
        value = node.value
    elif isinstance(node.target, ast.Name):
        name = node.target.id
        value = node.value
    values = literal_preview(value)
    return {
        "id": node_id(source, name),
        "symbol": name,
        "title": titleize(name.strip("_")),
        "kind": "constant",
        "group": source.group,
        "shape": "rule",
        "summary": f"Production constant from {source.module_label}.",
        "attributes": values,
        "annotationRefs": sorted(annotation_refs(values)),
        "source": node_source(source, lineno),
    }


def node_source(source: SourceFile, lineno: int) -> dict[str, str | int]:
    repo = REPOS[source.repo]
    return {
        "repository": repo.github_repo,
        "ref": repo.ref,
        "path": source.path,
        "line": lineno,
        "url": source_url(source.repo, source.path, lineno),
        "module": source.module_label,
    }


def node_id(source: SourceFile, symbol: str) -> str:
    repo_prefix = "ledger" if source.repo == "ledger" else "populace"
    module = (
        source.path.removesuffix(".py")
        .replace("packages/", "")
        .replace("src/", "")
        .replace("/", ".")
        .replace("-", "_")
    )
    return f"{repo_prefix}.{module}.{symbol}"


def class_fields(node: ast.ClassDef) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for child in node.body:
        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            fields.append((child.target.id, ast.unparse(child.annotation)))
    return fields


def literal_preview(value: ast.AST | None) -> list[str]:
    if value is None:
        return []
    try:
        literal = ast.literal_eval(value)
    except Exception:
        return [ast.unparse(value)[:120]]
    if isinstance(literal, dict):
        keys = list(literal.keys())
        return [f"{len(keys)} entries", *[str(key) for key in keys[:18]]]
    if isinstance(literal, set):
        items = sorted(literal, key=str)
        return [f"{len(items)} values", *[str(item) for item in items[:22]]]
    if isinstance(literal, (tuple, list)):
        items = list(literal)
        return [f"{len(items)} values", *[str(item) for item in items[:22]]]
    return [str(literal)]


def annotation_refs(annotations: list[str]) -> set[str]:
    refs = set()
    for annotation in annotations:
        refs.update(re.findall(r"\b[A-Z][A-Za-z0-9_]+\b", annotation))
    return refs


def add_attribute_nodes(
    nodes: list[dict[str, Any]], edges: list[dict[str, str]]
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    result = list(nodes)
    for node in nodes:
        for index, attribute in enumerate(node.get("attributes", [])):
            name = attribute.split(":", 1)[0].removeprefix("method").strip()
            attr_id = f"{node['id']}.{index:02d}.{slug(name)}"
            result.append(
                {
                    "id": attr_id,
                    "symbol": name,
                    "title": name,
                    "kind": "field",
                    "group": node["group"],
                    "shape": "attribute",
                    "summary": attribute,
                    "attributes": [attribute],
                    "annotationRefs": sorted(annotation_refs([attribute])),
                    "source": node["source"],
                    "parent": node["id"],
                    "ordinal": index,
                }
            )
            edges.append(
                {
                    "from": node["id"],
                    "to": attr_id,
                    "label": "declares",
                    "contract": "field extracted from production source",
                }
            )
    return result, edges


def type_reference_edges(
    nodes: list[dict[str, Any]], symbol_to_id: dict[str, str]
) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for node in nodes:
        if node.get("shape") == "attribute":
            continue
        for ref in node.get("annotationRefs", []):
            if ref == node.get("symbol"):
                continue
            target = symbol_to_id.get(ref)
            if target:
                edges.append(
                    {
                        "from": node["id"],
                        "to": target,
                        "label": "references",
                        "contract": "type annotation references production symbol",
                    }
                )
    return edges


def relationship_edges(symbol_to_id: dict[str, str]) -> list[dict[str, str]]:
    edges = []
    for source, target, contract in RELATIONSHIP_EDGES:
        if source in symbol_to_id and target in symbol_to_id:
            edges.append(
                {
                    "from": symbol_to_id[source],
                    "to": symbol_to_id[target],
                    "label": "uses",
                    "contract": contract,
                }
            )
    return edges


def dedupe_edges(edges: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    result = []
    for edge in edges:
        key = (edge["from"], edge["to"], edge["label"])
        if key in seen or edge["from"] == edge["to"]:
            continue
        seen.add(key)
        result.append(edge)
    return result


def layout_nodes(nodes: list[dict[str, Any]], edges: list[dict[str, str]]) -> list[dict[str, Any]]:
    group_order = [group["id"] for group in GROUPS]
    concept_nodes = [node for node in nodes if node["shape"] != "attribute"]
    attrs_by_parent: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        if node["shape"] == "attribute":
            attrs_by_parent.setdefault(node["parent"], []).append(node)

    concept_by_group = {
        group: [
            node
            for node in concept_nodes
            if node["group"] == group
        ]
        for group in group_order
    }
    x_step = 330
    y_start = 96
    y_step = 148
    attr_x_offset = 150
    attr_y_step = 42
    max_y = y_start
    placed: list[dict[str, Any]] = []
    for col, group in enumerate(group_order):
        x = 130 + col * x_step
        y = y_start
        for concept in sorted(concept_by_group[group], key=lambda item: item["title"]):
            concept["x"] = x
            concept["y"] = y
            placed.append(concept)
            attrs = sorted(attrs_by_parent.get(concept["id"], []), key=lambda item: item["ordinal"])
            for idx, attr in enumerate(attrs):
                attr["x"] = x + attr_x_offset
                attr["y"] = y + 48 + idx * attr_y_step
                placed.append(attr)
            y += max(y_step, 74 + max(0, len(attrs) - 1) * attr_y_step)
            max_y = max(max_y, y)
    known = {node["id"] for node in placed}
    placed.extend(node for node in nodes if node["id"] not in known)
    return placed


def canvas_size(nodes: list[dict[str, Any]]) -> dict[str, int]:
    width = max(int(max(node["x"] for node in nodes) + 280), 2200)
    height = max(int(max(node["y"] for node in nodes) + 180), 1600)
    return {"width": width, "height": height}


def graph_stats(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, str]],
    repo_meta: dict[str, dict[str, str]],
) -> list[dict[str, str | int]]:
    attributes = sum(1 for node in nodes if node["shape"] == "attribute")
    concepts = len(nodes) - attributes
    return [
        {"label": "concepts", "value": concepts},
        {"label": "fields", "value": attributes},
        {"label": "source repos", "value": len(repo_meta)},
    ]


def first_sentence(docstring: str) -> str:
    text = " ".join(docstring.strip().split())
    if not text:
        return ""
    if "\n\n" in docstring:
        text = " ".join(docstring.strip().split("\n\n", 1)[0].split())
    match = re.search(r"(?<=[.!?])\s", text)
    return text[: match.start()].strip() if match else text[:220]


def titleize(value: str) -> str:
    value = value.strip("_")
    value = re.sub(r"(?<!^)([A-Z])", r" \1", value)
    value = value.replace("_", " ")
    return value[:1].upper() + value[1:]


def slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return value.strip("_") or "field"


if __name__ == "__main__":
    main()
