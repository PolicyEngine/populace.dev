# populace.dev

Landing site for **populace** — an open-source stack for building weighted
synthetic populations from survey and administrative data.

- The stack: https://github.com/PolicyEngine/populace
- The site: a single static page (`index.html` + `style.css` + `field.js`),
  no build step.

## Develop

```bash
python3 -m http.server 4399
# open http://localhost:4399
```

## Design

Typography: Fraunces (display) · Newsreader (body) · IBM Plex Mono (labels).
The hero canvas (`field.js`) renders one point of light per synthetic household,
brightness scaled by survey weight. Respects `prefers-reduced-motion`.

Deployed to Vercel; static, no framework.
