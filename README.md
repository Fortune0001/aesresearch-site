# aesresearch-site

Source for [aesresearch.ai](https://aesresearch.ai) — AES Research.

Independent AI research program exploring architectural patterns for long-horizon agentic systems: two-tier memory, cross-project director agents, UAT harnesses that surface the residual-context gap, skeptic membranes for verifiable autonomous output, production ML pipelines with multi-year out-of-sample validation.

---

## Structure

```
.
├── index.md                 # landing (source)
├── index.html               # landing (generated)
├── style.css
├── layouts/default.html     # HTML wrapper template
├── writing/                 # deep-dives
│   ├── two-tier-memory.md   # source
│   └── two-tier-memory.html # generated
├── build.py                 # generator + deployer
├── CNAME                    # custom domain for GitHub Pages
└── .nojekyll                # disables Jekyll; serve HTML as-is
```

## Build + deploy

```bash
# Generate HTML from markdown
python build.py

# Build + commit + push to the configured repo
python build.py --deploy

# Full pipeline: build + deploy + enable Pages + custom domain
python build.py --all
```

`build.py` reads `GITHUB_TOKEN_FG_Admin` from the environment or `~/.keys.env`. Configure target repo via `REPO_SLUG` env var; default is `Fortune0001/aesresearch-site`.

## Adding a new writeup

1. Create `writing/<slug>.md` with an H1 title and an italicized one-line description
2. Add a link to it under the "Writing" section of `index.md`
3. Run `python build.py --all`

The tool regenerates `index.html` and `writing/*.html`, commits, pushes, and re-deploys Pages.

## License

All content © Daniel Higuera / AES Research. The `build.py` generator is open for reuse — treat as CC0.
