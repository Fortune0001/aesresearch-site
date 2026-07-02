# Demo Worker source

*The Cloudflare Worker behind the interactive tools on this site — published source.*

---

The API at `api.aesresearch.ai` is a single Cloudflare Worker that fronts every interactive tool on this site: the [live architecture demo](../demo/), the [Q&A agent](../ask.html), and the [contact form](../contact.html). It keeps API keys server-side, enforces per-IP rate limits and a shared daily spend ceiling before any upstream call, and re-emits model output as the structured SSE events the frontends render.

## Source files

- [worker.js](worker.js) — the Worker itself: routing, rate limiting, budget ceiling, SSE transforms, and the per-endpoint handlers
- [corpus.js](corpus.js) — the published-essay corpus the Q&A agent cites from (generated from the same markdown sources as the site)
- [wrangler.toml](wrangler.toml) — deploy config: routes and KV bindings (secrets are set via `wrangler secret`, never stored here)
- [README.md](README.md) — deploy and operations notes

## Why a Worker in front of the model API

1. **Secret protection** — the API keys stay server-side; nothing a client can exfiltrate.
2. **Rate control** — per-IP hourly limits plus a shared daily budget cap, enforced before any upstream spend.
3. **Prompt control** — the system prompt that drives the demo's layer protocol lives server-side, so visitors can't edit it out to bypass the demo structure.
4. **Same-origin simplicity** — one proxied subdomain for every endpoint keeps the frontends plain `fetch` calls.
