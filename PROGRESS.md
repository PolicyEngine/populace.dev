# Paper web views — progress

Branch: `paper-webviews` (from `origin/master`). Isolated worktree: `/Users/maxghenis/PolicyEngine/_worktrees/populace-paper-webviews` (kept out of the shared checkout so it never collides with the concurrent strategy-pages agent's untracked files). Scope: `support/web/`, `evaluation/web/`, `support/paper.html`, `evaluation/paper.html` only. Do NOT touch the six strategy `index.html` pages, `style.css`, or `paper-page.css` (another agent owns those).

## Exemplar pattern (from sparsity/web + dynamics/web)
- `sparsity/web/index.html`: pandoc self-contained HTML. Site chrome injected via a `<style id="paper-inline-css">` block that `@import`s Google Fonts (Inter/JetBrains Mono) + `@policyengine/ui-kit@0.12.1/src/theme/tokens.css`, then maps design tokens (`--primary`, `--foreground`, ...) and styles the pandoc DOM. Math via MathJax 3 CDN (`cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml-full.js`). Figures vendored to `sparsity/web/figures/`, referenced with absolute paths `/sparsity/web/figures/...`.
- `dynamics/web/index.html`: single ~1.2 MB fully-inlined file (base64 imgs). Task says match SPARSITY.
- `paper.html`: site chrome (nav/footer) + hero with CTAs + a `<section id="web" class="paper-viewer">` with `<iframe class="paper-frame" src="/<slug>/web">`. Primary CTA `Read online` → `#web`; `Open full page` → `/<slug>/web`. I make the primary CTA "Read on the web" per the task.
- Design tokens only; sentence case; the vendored pandoc paper CSS block (with hex fallbacks mirroring tokens) is the exemplar-established acceptable exception.

## The injected paper-inline-css block (copy verbatim from sparsity for consistency)
Saved to scratchpad `paper-inline-css.css`. Reused for both new web renders.

## Tasks
1. [x] Support paper = imputation-paper. DONE. Vendored `support/web/index.html`; updated `support/paper.html` ("Read on the web" primary → #web/iframe /support/web; PDF + repo retained).
2. [x] Evaluation paper = popdgp JOSS paper. DONE. Vendored `evaluation/web/index.html`; updated `evaluation/paper.html` ("Read on the web" primary; repo + imputation-paper reference retained). Author = Max Ghenis + PolicyEngine affiliation (from JOSS meta). TODO(authorship) comment verified INVISIBLE (0 visible, 1 well-formed HTML comment).
3. [x] Calibration + composition: untouched (git diff = 0). Confirmed.
4. [x] Verified both: http.server all 200; math/citation/table markers present; TODO non-leak proven; ALL internal links resolve under cleanUrls; external links (popdgp, imputation-paper, raw PDF) HEAD 200.

## Task 2 render notes (popdgp → evaluation/web)
- **Input**: `paper.md` (JOSS software paper) + `paper.bib`, markdown — much simpler than task 1.
- **pandoc**: `-f markdown -t html5 --standalone --toc --toc-depth=1 --metadata-file=popdgp_meta.yaml --citeproc --bibliography=paper.bib --mathjax --section-divs --include-in-header=header_include.html`. Metadata override supplies pandoc-template title/author/date (JOSS `authors:`/`affiliations:` structure isn't consumed by the default template); author rendered honestly as "Max Ghenis" + "PolicyEngine, Washington, DC, United States", sole author, no invented co-authors.
- **THE comment bug (the class I was told to check)**: markdown `<!-- TODO(authorship) ... -->` in Acknowledgements → pandoc passes it through as a real, well-formed HTML comment (`<!-- ... -->`, closed). Proof: strip all comments from the rendered HTML → 0 occurrences of "TODO"/"authorship"; the raw file still contains exactly 1 `<!-- TODO(authorship)` (invisible). The YAML frontmatter `#` comments (the seeded-authorship block) are stripped by the YAML parser: 0 visible. No leak of either class.
- **Embedded**: same CDN triad (fonts + ui-kit tokens + MathJax 3). No figures — text + 4 math spans only.
- **Verified**: 0 pandoc warnings; 4 math spans (energy-distance D², k, reweighting bounds), 10 citations, 5 bib entries, 8 section headings.
- **Honesty edit to paper.html**: the page previously said "methods paper NOT started / no manuscript to embed"; that's now stale because paper.md exists. Reframed as the JOSS *software* paper (real, draft) while keeping honest that the broader methods study (power analysis, multi-view generalization) is still future work. Updated eyebrow, lede, one fact card, viewer, and head meta/og tags accordingly.

## Task 1 render notes (imputation → support/web)
- **Problem**: `index.qmd` is LaTeX-first — body is `\input{sections/*.tex}` (9 sections) + `\input{tables/*.tex}` (7 tables). `quarto render --to html` DROPS all `\input{}` content (produced a 1.18 MB file with an empty body). Confirmed.
- **Fix**: assembler `scratchpad/build_imputation_standalone.py` expands `\input{}` recursively, strips PDF-only `\resizebox{A}{B}{BODY}`→BODY (brace-matched), prepends `macros.tex` so pandoc expands custom `\newcommand`s. Abstract split out to land in the pandoc title block (like sparsity `.abstract`), converted `-t markdown` for the metadata block scalar (raw HTML in metadata gets escaped; markdown does not).
- **pandoc**: `-f latex -t html5 --standalone --toc --toc-depth=2 --metadata-file=meta.yaml --citeproc --bibliography=paper/bibliography/references.bib --mathjax --section-divs --include-in-header=header_include.html`. `--metadata-file` MUST be a flag; positional YAML leaks as body + wrong `<title>`.
- **Embedded**: same CDN triad as sparsity (Google Fonts + ui-kit tokens + MathJax 3) via the verbatim `paper-inline-css` block + MathJax `<script>` in a header-include. NO figures in this paper — nothing to vendor.
- **Verified**: 0 pandoc warnings; 7 tables, 43 math spans, 49 citations, 38–41 bib entries, 41 internal `#sec/#tab` links; macros expanded; index.qmd authorship HTML comment did NOT leak (assembled from sections/, not index.qmd); funding `[TODO: Funding statement.]` renders loudly as the paper's own `\todo{}` intends — preserved honestly. http.server: all 200; iframe + "Read on the web" primary confirmed.

## Source repo state (verified)
- imputation-paper @ main: Quarto project, source `paper/index.qmd` (+ index.tex, macros.tex, preamble.tex). CI renders HTML-only; TinyTeX local.
- popdgp @ main (pulled 402fb23): `paper.md` + `paper.bib` at root exist (added 493458d). Complete JOSS paper, author = Max Ghenis (sole, TODO(authorship) seeded). Body has one `<!-- TODO(authorship) -->` HTML comment in Acknowledgements — watch for leak.

## Log
- Studied exemplars, confirmed pattern. Branch + isolated worktree created. Source repos pulled + inspected.
