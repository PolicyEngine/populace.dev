# Subpage visuals — progress log

Branch: `subpage-visuals` (from `origin/master`)
Scope: six strategy `index.html` pages + `style.css` only. NOT touching `paper.html` or `web/` dirs (another agent owns those).

Dev server: global `~/.claude/launch.json` `populace-site` config, port 4399, already points at `/Users/maxghenis/PolicyEngine/populace.dev` (this exact checkout — verified byte-for-byte). The repo-local `.claude/launch.json` is NOT read by preview_start (it reads the global registry only), so leave it alone. A separate global entry `populace-site-strategy-pages` (port 4401) points at a stale worktree — do not use it.

## Verification technique (screenshot tool resets scroll to top!)
The preview_screenshot tool always captures the TOP of the page regardless of scroll position. To screenshot a mid-page diagram: clone the `.diagram-figure` into a fixed full-screen overlay div (`#__shot`, `background:var(--ink)`) at the top, screenshot, then remove the overlay. For property/color verification use `preview_inspect` (reliable, resolves CSS vars to rgb). For no-horizontal-scroll at 375px: `preview_resize` mobile then check `document.documentElement.scrollWidth === clientWidth` via preview_eval.

## Plan
1. [x] Shared diagram/SVG CSS in style.css (.diagram-figure, .dg-* classes) — committed 221a162
2. [x] /support — composition diagram + AUC bar comparison — committed 221a162, VERIFIED desktop+375px
3. [x] /calibration — target hierarchy (national→state→program) → gradient-descent box + before→after (1.831→0.022, 22.2%→94.7%, 50×). VERIFIED desktop+375px
4. [ ] /sparsity — records-vs-accuracy chart
5. [ ] /evaluation — harness diagram (one population → views → scoring)
6. [ ] /composition — operator pipeline + landmine illustration
7. [ ] /dynamics — trajectory diagram (one weight per trajectory)
8. [ ] Verify all six at desktop + 375px mobile (no horizontal scroll)
9. [ ] Commit+push per page
10. [ ] Delete this file, final commit
11. [ ] PR via gh pr create --body-file

## Numbers verified verbatim from each page (source of truth — do not introduce new claims)

**support/index.html:**
- classifier AUC: candidate 0.761, hot-deck 0.768, marginal/unconditional weighted draw 0.968
- 0.5 AUC = indistinguishable (stated on /evaluation page, applies as the reference line)
- flow: CPS ASEC spine (demographics) + PUF support channel (tax detail) + ACS channel "planned" → cloned records retain source identity → sequential zero-inflated QRF completion (gate model for zero/participation regime, then QRF draws amount) → weights by construction

**calibration/index.html:**
- calibration loss: 0.022 (from 1.831 at design weights)
- targets within 10%: 94.7% (from 22.2% at design weights)
- max weight ratio: 50x hard bound
- hierarchy: national (Census pop counts), state (AGI, program totals), congressional district mentioned on homepage/sparsity as a driver — NOT explicitly a target level named on calibration page itself (need to check: calibration page says "Census population counts, IRS SOI income and deduction totals, BEA wages, state-level adjusted gross income and program administrative totals" — no explicit congressional-district target level named here; sparsity page says candidate frame sized "to cover state and congressional-district targets at once" — CD is a sparsity-page claim about candidate sizing, not a calibration-page target-hierarchy claim). Diagram hierarchy labels must therefore be: national -> state -> program (not invent "congressional district" on THIS page unless sourced elsewhere on this page).

**sparsity/index.html:**
- dense (no-L0): 5.07% loss, all candidates (337,704... wait check: "57,240 of 337,704 candidates (17.0%)" for L0; dense baseline row not explicit as a metric card — check method cards)
- L0 retained: 57,240 of 337,704 (17.0%), post-L0 refit loss 4.74% vs 5.07% dense, 7.55% random+reweight
- random support scaled no refit: 24.24% (worst of 5 arms)
- 32,633 targets is the surface size for these numbers (not 3,704 — that's the release registry number used elsewhere)

**evaluation/index.html:**
- four blocks: energy distance, coverage (PRDC), classifier AUC, tail block
- survey-view classifier floor: 0.50 AUC indistinguishable
- tail block: weight-blind fit caught at 1.9-2.3x the holdout's p99
- calibration targets within 10%: 94.7% in-fit
- harness: "one latent population is observed through each survey's view... any candidate file gets projected through a view and scored against that survey's own holdout" — anchored by sampling-noise floor (survey's own complementary split scored as candidate)

**composition/index.html:**
- pipeline framing: support (imputation) -> calibration (reweight) -> shipped file; "imputed values get reweighted, and a distortion invisible to either operator's own validation can appear only in that combination"
- landmine reference: "realized landmines" (01), "the interaction blamed for a prior incident in the enhanced CPS pipeline" — this IS the landmine illustration source language
- 4 planned questions: landmines, repairability, target-vs-survey trade-off (Pareto), effective-support collapse (top 99% mass coverage variant)
- all tag-wip / planned, nothing run yet

**dynamics/index.html:**
- design stage, wip tag throughout
- "one weight per full trajectory, with entry and exit markers"
- transitions as conditional models: earnings, family structure, disability, mortality, program participation
- cross-sectional foundation stat: 0.038 holdout loss vs 0.317 (explicitly caveated as describing the layer being EXTENDED, not a dynamics-layer result)
- first domain: U.S. Social Security

## Open questions / decisions log

- **[calibration hierarchy — DECISION]** Task brief asked for "national → state → congressional district" but the live calibration release (populace-us-2024-5da5a95, the exact build the page cites) has ONLY two geographic levels in data/calibration.json: `national` (1,222 targets, 1 geography) and `state` (2,482 targets, 52 geographies). NO congressional-district level exists in the data, and the calibration page never claims one — its method card says "National, state, and program targets jointly". Congressional district appears ONLY on the sparsity page, and only as motivation for a large *candidate frame* ("cover state and congressional-district targets at once"), not as a calibration-release fact. Per the verbatim-numbers rule I built the hierarchy as **national → state → program/agency** (matching both the page copy and the live data), NOT national→state→CD. Flagging for lead: if you want CD shown, it needs a real source on the calibration page first.
