# populace.dev

Landing site for **populace** — an open-source stack for building weighted
synthetic populations from survey and administrative data.

- The stack: https://github.com/PolicyEngine/populace
- The site: static HTML/CSS/JS pages, no framework build step.

## Develop

```bash
python3 -m http.server 4399
# open http://localhost:4399
# local static route for the spec page: http://localhost:4399/spec.html
```

## Spec Graph

`/spec` reads `data/spec-graph.json`, which is generated from production
Populace and Ledger source contracts. Do not edit the graph JSON by hand.
CI regenerates it and fails if the committed artifact drifts.

```bash
python3 scripts/generate_spec_graph.py
```

By default the generator reads `PolicyEngine/populace@main` and
`PolicyEngine/arch-data@main` from GitHub raw URLs. Set `POPULACE_REPO_DIR` or
`LEDGER_REPO_DIR` to point at a local checkout while developing against an
unmerged branch.

See `docs/spec-source-audit.md` for the current production-backed surfaces and
the remaining country-pack work.

## Design

Typography: Fraunces (display) · Newsreader (body) · IBM Plex Mono (labels).
The hero canvas (`field.js`) renders one point of light per synthetic household,
brightness scaled by survey weight. Respects `prefers-reduced-motion`.

Deployed to Vercel; static, no framework.
