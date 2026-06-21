# Spec Source Audit

This note records what `/spec` is generated from today and what still needs to
move into declarative contracts before Populace builds are fully spec-driven.

## Production-backed in `/spec`

The graph is generated from source contracts, not a hand-authored architecture
diagram.

- `PolicyEngine/populace`: build stages, donor specs, stage records, entity
  schemas, links, variable metadata, weights, target specs, target registries,
  calibration, release gates, and published dataset registry contracts.
- `PolicyEngine/arch-data`: Ledger fact schemas, dimensions, source provenance,
  source record specs, source package manifests, consumer contracts, and
  contract reports.
- Source provenance is pinned in `data/spec-graph.json` by repository commit so
  reviewers can tell which production contracts the page reflects.

## Remaining imperative surfaces

These are the places that still need follow-up work before country builds are
plain data.

- Target profiles: Populace can still receive target values through generated
  target-registry artifacts. Country content should instead select Ledger
  profile rows whose values resolve from Ledger facts.
- Build stages: Populace stage plans can carry Python callables. Country packs
  should declare source channels, support frames, imputation stages, and runtime
  bindings as JSON or YAML that compiles to the existing stage plan.
- Release gates: release checks exist as functions. Country packs should select
  and parameterize those checks through release contracts.
- Published datasets: the dataset registry is a Python mapping. Published
  bundles should emit a release manifest that consumers and `populace.dev` can
  read directly.
- Ledger source packages: package aliases still live in Python. Ledger should
  publish manifest-backed source package registries.
- Ledger target outputs: source ETL can be imperative. Ledger should emit stable
  target profile and consumer fact artifacts that Populace consumes without
  direct database queries or copied values.

## Implementation sequence

1. Ledger emits target profile artifacts with fact keys, dimensions, source
   periods, uprating policy, measurement bindings, and profile version.
2. Populace consumes Ledger profile artifacts into `TargetRegistry` without
   country target values.
3. Populace country specs declare sources, support channels, imputation stages,
   calibration settings, and release gates.
4. Release bundles publish `spec/` artifacts for graph, target registry, source
   coverage, lineage, and gate results.
5. `populace.dev` renders published bundle artifacts by release id and keeps the
   source-code graph as a development fallback.
