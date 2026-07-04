# PROGRESS — populace.dev strategy pages (issue #17)

STANDING ORDERS v2 — two fleets died to process exits today. Update this file at
EVERY push. Delete it in final cleanup before PR is marked ready (or leave until
lead says otherwise — check before deleting).

Worktree: ~/PolicyEngine/_worktrees/populace-site-strategies
Branch: strategy-pages (pushed to origin), base 9fb969d
PR: not yet opened

## Spec (gh issue view 17 --repo PolicyEngine/populace.dev)
6 strategy pages with nested /paper as stable citation URL:
- /imputation (paper: imputation-paper repo, no live render — POINT not vendor)
- /calibration (paper: calibration-paper repo)
- /sparsity (paper: sparsity-paper repo)
- /evaluation — BOTH validation currencies: survey-view fidelity (popdgp harness,
  its coverage block deliberately calibration-blind, energy/C2ST/tail blocks score
  weighted measure) AND administrative target attainment (in-fit + held-out
  families, fragility, per-release dossier). paper = popdgp paper.
- /composition (paper: composition-paper repo)
- /dynamics (paper: exists already — self-contained HTML)
- / (home) — system story, system paper hangs off it at launch (populace#304, not
  this issue's job to build that paper)

Thin /papers aggregator retained. Redirects: /papers/dynamics -> /dynamics/paper
(permanent), future-proof /papers/{slug} -> /{slug}/paper generally.

Portfolio source of truth: populace#305.

## Predecessor decisions to KEEP (do not relitigate)
- /imputation: NO hero canvas. If a no-op field.js <script> tag references a
  canvas that doesn't exist, REMOVE the script tag rather than adding a canvas.
- /imputation/paper: POINTS rather than vendors (vat-threshold precedent).
  imputation-paper has no live render -> link GitHub repo/PDF with a TODO
  comment for a future stable render URL. Do not try to build a live render.

## Hard rules (from lead)
- Copy DIRECT, never cute. Numbers speak. No subjective claims. Sentence case.
- Design tokens only, never hardcoded hex (see design skill notes below).
- No emoji icons. bun/bunx only. Match existing site patterns.
- Vercel config at repo root (vercel.json already exists there).
- VERIFY VISUALLY before declaring anything done: dev server + screenshots of
  every new/changed page at desktop AND mobile widths. Confirm redirect fires
  and is a permanent (308/301) redirect, not a client-side trick.
- Push after EVERY coherent step. Treat every push as possibly the last thing
  you get to do — leave the tree in a working, committed, pushed state always.
- PR via `gh pr create --body-file` — NO @-mentions. Vercel preview = review
  surface. Do NOT merge. Max merges after lead review.
- Don't block on user input — decide and proceed, note open questions in the
  final report instead of asking.

## Design system notes (this is a static HTML/CSS/JS site, NOT React/Tailwind)
- Tokens live as CSS custom properties in style.css (checked below), not
  Tailwind utility classes or @policyengine/ui-kit imports.
- Brand teal #319795 etc. must be referenced via existing CSS vars in
  style.css, never hardcoded hex in new markup/CSS.
- Font: Inter (body) + JetBrains Mono (code) per PE design system.
- Sentence case headings/UI text throughout.

## State machine (update every push)
- [x] Load design skill — DONE (complete:policyengine-design, noted static-site
      caveat above; this is a no-build static site, ui-kit tokens.css loaded
      via CDN link tag, NOT Tailwind classes)
- [x] Write this PROGRESS.md — DONE
- [x] git diff origin/master...HEAD read (note: repo's trunk is `master`, not
      `main` — `git diff origin/main...HEAD` fails, use `origin/master`)
- [x] Read changed files from predecessor work in detail
- [x] Inventory current page-by-page status vs spec — see table below
- [x] Confirmed /imputation already has NO canvas, NO field.js script tag —
      predecessor decision already correctly applied, nothing to fix
- [x] Confirmed field.js guards `if (!canvas) return` — safe everywhere
- [x] Built /imputation/paper (did not exist despite nav linking to it) —
      points to https://raw.githubusercontent.com/PolicyEngine/imputation-paper/main/paper/main.pdf
      + repo link + explicit TODO block for a future stable HTML render,
      per the vat-threshold "points not vendors" precedent
- [x] Built /calibration + /calibration/paper
  - Confirmed via 2 independent checks (direct gh api reads + a dedicated
    research subagent) that calibration-paper repo is PLAN-STAGE ONLY:
    README + PLAN.md, a WIP unreviewed method-surface branch, ZERO computed
    results, no PDF, no web render. Do NOT cite any calibration-paper
    "finding" as fact anywhere.
  - /calibration strategy page instead cites REAL, live production numbers
    from data/calibration.json (populace-us-2024-5da5a95 release): 3,704
    targets, loss 1.831->0.022, within-10% 22.2%->94.65%, max weight ratio
    50x bound, per-family breakdown (worst: irs·rent_and_royalty_net_losses
    0% within10, n=28). These are real release-registry numbers, NOT paper
    claims — page copy is explicit about that distinction.
  - /calibration/paper states plan-stage status honestly: methods to be
    compared, blocked-on dependencies (l0-paper#17, popdgp#1), target venue
    (Survey Methodology / JOS), explicit "no manuscript exists" not-yet box.
- [ ] Build/fix /sparsity + /sparsity/paper — ALREADY EXISTS from predecessor,
      just need to verify it matches pattern (looked complete on read)
- [x] Build /evaluation + /evaluation/paper (both currencies) — DONE
  - Confirmed via research subagent + direct verification: popdgp's real
    working harness code + all current numbers live INSIDE imputation-paper
    (src/imputation_paper/experiments/); popdgp's own main branch is
    README-stage only, extraction branch in progress unmerged, methods paper
    NOT STARTED (verified: popdgp issues #1 extract-to-PyPI, #2 methods
    paper, both open, neither has a draft)
  - /evaluation page covers BOTH currencies as the issue spec requires:
    survey-view fidelity (popdgp harness, described honestly re: where code
    actually lives) AND administrative target attainment (live in-fit
    numbers from calibration.json + held-out/fragility as PROPOSED release
    gates citing populace#302 + populace-benchmarks#6, both verified open
    and unimplemented)
  - /evaluation/paper states clearly: harness is proven (cites
    imputation-paper's harness_scale.tex numbers), standalone popdgp methods
    paper has NO DRAFT — does not pretend a popdgp paper exists
- [x] Build /composition + /composition/paper — DONE
  - Confirmed composition-paper is design-doc-only (README states 4
    questions, zero code/data/results), blocked on 3 unmet deps
    (populace#302, calibration-paper adapter registry, popdgp extraction)
  - Both composition pages state "not yet run" / "planned" explicitly for
    every claim, cite the real blocking issues
- [ ] Verify /dynamics + /dynamics/paper (should mostly exist) — looked
      complete on read, will re-verify visually
- [x] Build /papers thin aggregator — DONE. Lists all 6 papers with honest
      per-paper status tags (preprint/plan-stage/design-doc/harness-proven),
      links into each /paper page, notes country model papers live on
      policyengine.org research instead.
- [x] Verified /papers/dynamics -> /dynamics/paper AND /papers/l0 ->
      /sparsity/paper AND general /papers/:slug -> /:slug/paper all exist in
      vercel.json already, all marked permanent: true
- [ ] Homepage tells the system story — largely done already (read in full),
      may need small tweaks once /papers exists to link correctly
- [ ] Run dev server, screenshot every new/changed page at desktop + mobile
- [ ] Confirm redirect fires (curl -I or browser network tab, check 301/308)
      — vercel.json redirects only take effect on Vercel, NOT on the local
      python http.server; must verify via Vercel preview deployment, not
      localhost. Note this in final report.
- [x] Push after this batch (calibration + imputation/paper)
- [ ] Open PR via gh pr create --body-file (no @-mentions)
- [ ] Final report to lead: PR + preview URLs, page-by-page status,
      screenshots taken, open questions

## Page-by-page status (living table, update every push)
| Page | Status | Notes |
|---|---|---|
| / (home) | mostly done | tells system story; links to /papers, all 6 strategy pages via strategy-grid; may need minor link tweaks |
| /imputation | done (predecessor) | correctly has no hero canvas |
| /imputation/paper | built this session | points to repo PDF, TODO for stable render |
| /calibration | built this session | live release numbers only, no paper claims |
| /calibration/paper | built this session | honest plan-stage status |
| /sparsity | done (predecessor) | needs visual re-verify only |
| /sparsity/paper | done (predecessor) | needs visual re-verify only |
| /evaluation | built this session | both currencies covered per spec |
| /evaluation/paper | built this session | honest "harness proven, methods paper not started" status |
| /composition | built this session | design-doc stage stated honestly throughout |
| /composition/paper | built this session | same |
| /dynamics | done (predecessor) | needs visual re-verify only |
| /dynamics/paper | done (predecessor) | needs visual re-verify only |
| /papers (aggregator) | built this session | thin index, all 6 papers, honest status tags |
| redirects (vercel.json) | done (predecessor) | /papers/l0, /papers/dynamics, /papers/:slug generic — all permanent:true |

## Notes / decisions log
(append entries here as work proceeds, newest at bottom)
- 2026-07-04: Session start. Resuming after 2 predecessor fleet deaths. Design
  skill loaded (complete:policyengine-design) — flagged as React/Tailwind-
  oriented; this is a static site so translating tokens to CSS custom
  properties matching existing style.css.
- 2026-07-04: FACTUAL ERROR FOUND AND FIXED in /imputation/index.html
  (pre-existing, inherited from predecessor, not something I introduced).
  The harness section said "Hot-deck matching is a genuine near-peer... at
  populace scale the classifier separates it almost perfectly (AUC 0.97
  against the candidate's 0.76)" — misattributing the 0.97 AUC to hot-deck.
  Verified against the actual source table
  (imputation-paper paper/tables/harness_scale.tex, populace-scale profile,
  mean over 10 seeds): NND hot deck AUC = 0.768, populace-fit (candidate)
  AUC = 0.761 — these are NEAR-IDENTICAL, i.e. hot-deck genuinely is a
  near-peer on this axis, the opposite of "separates it almost perfectly."
  The 0.968 AUC belongs to a THIRD method, "weighted marginal draw" (an
  unconditional draw that discards every predictor) — that's the method the
  classifier catches almost perfectly, illustrating why marginal-only
  metrics are insufficient. Fixed the copy to state the correct comparison:
  hot-deck (0.768) vs candidate (0.761) are near-identical; weighted
  marginal draw (0.968) is what gets caught. Root cause: the paper's own
  abstract compresses two findings into one dense sentence
  ("Hot-deck... near-peer; marginal metrics rank an unconditional weighted
  draw... at populace scale the classifier separates it... [0.97 vs 0.76]")
  — read literally the 0.97/0.76 clause modifies "an unconditional weighted
  draw," not hot-deck, but the site copy compressed this into an incorrect
  single-method attribution. Also double-checked the other two numeric
  claims on the same page against the abstract text directly: "6x worse
  Wasserstein-1" and "7-11x understated" both verified verbatim correct,
  no changes needed there. This fix must ship in the same push as the
  calibration/imputation-paper pages — do not lose it.
