# CHANGELOG

## 2026-04-22 — Live demo, four skills, per-IP rate limiting

Code shipped to `main` continuously across the session via the `build.py --all` deploy pipeline, so the diff against `main` for this branch is just this CHANGELOG. The narrative below documents the work that went live; cross-reference against the `index.html`, `worker/`, `.claude/skills/`, and `demo/` directories on `main` to see the actual shipped artifacts.

### Site

- Skills section added to the landing page with GitHub source links to each `SKILL.md`
- "Honest note on what this demo's memory actually does" added to `/demo/` distinguishing fixture memory from per-session history from the production AES Research memory system

### Skills (new — `.claude/skills/`)

Four reusable Claude Code skills, each with frontmatter (`name`, `description`), when-to-use, decision rules, output format, related-pattern links:

- **`aes-skeptic-membrane`** — vet an autonomous agent output before it crosses an external boundary; classify pass / clarify / reject + reason + next-action
- **`aes-two-tier-memory`** — scan a `MEMORY.md` index + per-topic files; decide which entries to load for the current task; emit a load plan with skipped entries explained
- **`aes-attention-routing`** — decide where a step runs (native / tool-augmented / skill-dispatch / sub-agent) based on the cost/latency/reliability triangle
- **`aes-pattern-map`** — given a system or design problem, identify which AES Research patterns apply and how they compose

### Live demo (`/demo/`)

- `/demo/` published at https://aesresearch.ai/demo/ with chat input, streaming response, "thought stream" sidebar, Reset button, and an honest scope note
- Cloudflare Worker deployed at `api.aesresearch.ai/*` (proxied AAAA `100::` subdomain so Cloudflare intercepts before any origin)
- **`POST /chat`** — streaming SSE proxy to Anthropic messages API. System prompt forces the model to emit `<layer ... />` decisions (membrane, memory, attention) before a `<response>...</response>` body. Worker re-emits each as a structured SSE frame the frontend renders in the thought-stream panel. Streaming logic correctly suppresses the closing `</response>` tag from delta output.
- **`POST /fire-routine`** — fires Claude Routine `trig_01EF2wPF5zgtTW2VPfccX9Da` ("AES Research — demo deep-dive"); returns the session URL for the visitor to watch
- **Multi-turn conversation history** — frontend accumulates `{role, content}` turns in JS memory and ships them with every request; Worker prepends them to the Anthropic `messages` array. Server stays stateless. Closing the tab resets the session.
- **Per-IP rate limiting** — Cloudflare KV namespace `RATE_LIMIT` with fixed-hour buckets. `/chat` capped at 30 req/IP/hr, `/fire-routine` capped at 5 req/IP/hr (tighter because each fire draws down the account-level daily Routine cap). 429 responses include `Retry-After` + JSON body; successful responses include `X-RateLimit-Limit` / `X-RateLimit-Remaining`.
- **Privacy** — visitor IPs coarsened to /16 (IPv4) or /48 (IPv6) before any persistent storage; full IPs never leave Cloudflare's edge

### Observability (deferred)

- Workers Analytics Engine dataset (`aesresearch_demo`) + binding (`ANALYTICS`) created in the Cloudflare dashboard
- `writeAnalytics` helper wired throughout the Worker request handler; no-ops gracefully when `env.ANALYTICS` is undefined
- The `[[analytics_engine_datasets]]` block in `wrangler.toml` is **commented out** pending Cloudflare API token re-scope (existing token uses the "Edit Cloudflare Workers" template which doesn't include `Account Analytics: Edit`; fine-grained PATs can't be re-scoped after creation)
- Once a new token with the right permission is added, uncomment the binding and redeploy — the Worker code already writes data points

### Worker source

`worker/` directory in the repo carries the deployable source (`worker.js`, `wrangler.toml`, `README.md`). README documents the deploy flow, secret management, rate-limit ops, and the AE re-scope path.

### Fixed during the session

- Streaming protocol bug — `</response>` close tag was leaking into the final delta. Rewrote the in-response state machine to hold the close-tag length as a sliding buffer; tag never leaves the Worker.
- Worker route mismatch — initial deploy used `aesresearch.ai/api/*` paths with DNS-only records; that fails because GitHub Pages serves at the same hostname. Migrated to a proxied `api.aesresearch.ai` subdomain (AAAA `100::` orange-cloud). Stale routes deleted via the Cloudflare Workers API.
- README merge conflict — auto-init `README.md` from GitHub repo creation conflicted with the rich README. Resolved keeping the full version.

### Pending (carry into next session)

1. **Attach `Fortune0001/aesresearch-site` to the Routine** at https://claude.ai/code/routines (UI-only; requires the Claude GitHub App to be installed on the repo)
2. **Update Routine prompt** to invoke `aes-skeptic-membrane`, `aes-two-tier-memory`, `aes-attention-routing`, `aes-pattern-map` by name instead of inlining their decision logic
3. **Cloudflare API token re-scope** to add `Account Analytics: Edit` (lets the Analytics Engine binding deploy — observability lights up at that point)
4. **Ship 201-course carve-out D** — "Calibration, Boundary Layers, and the Distance Between Yes and No" — flagship Phase 1 piece per the 201 transcript index recommendation. Source paragraphs span `01_pt1`, `02`, `03`, and `06`. Establishes the brand vocabulary all subsequent pieces inherit.
5. **Resume + cover letter URL update** — embed the live `aesresearch.ai` URL; generate ATS-friendly PDFs for Siemens Energy submission
6. **Siemens application** — final user approval, then submit
