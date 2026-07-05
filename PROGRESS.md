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
1. [ ] Support paper = imputation-paper (Quarto → self-contained HTML). Vendor to `support/web/`. Update `support/paper.html`: "Read on the web" primary → /support/web; keep PDF + repo links.
2. [ ] Evaluation paper = popdgp JOSS paper (paper.md + paper.bib → HTML via pandoc+citeproc, styled like sparsity). Vendor to `evaluation/web/`. Update `evaluation/paper.html` same way. Author line = Max Ghenis; ensure `<!-- TODO(authorship) -->` HTML comment does NOT leak as visible text.
3. [ ] Calibration + composition: NO papers — leave paper.html untouched.
4. [ ] Verify each: local http.server + curl status/markers; check a math expr, a figure, a citation render in HTML source; check every changed link resolves.

## Source repo state (verified)
- imputation-paper @ main: Quarto project, source `paper/index.qmd` (+ index.tex, macros.tex, preamble.tex). CI renders HTML-only; TinyTeX local.
- popdgp @ main (pulled 402fb23): `paper.md` + `paper.bib` at root exist (added 493458d). Complete JOSS paper, author = Max Ghenis (sole, TODO(authorship) seeded). Body has one `<!-- TODO(authorship) -->` HTML comment in Acknowledgements — watch for leak.

## Log
- Studied exemplars, confirmed pattern. Branch + isolated worktree created. Source repos pulled + inspected.
