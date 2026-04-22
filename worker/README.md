# aesresearch-demo Cloudflare Worker

Backend for the live demo on [aesresearch.ai/demo](https://aesresearch.ai/demo/).

Two endpoints:
- `POST /api/chat` — streaming SSE proxy to Claude messages API. System prompt enforces the three architectural layers (skeptic membrane → two-tier memory → attention routing) and emits each as a structured event to the frontend.
- `POST /api/fire-routine` — fires a pre-configured Claude Routine, returns the session URL for the visitor to watch.

---

## First-time deploy

### 1. Install wrangler (one-time)

```bash
npm install -g wrangler
wrangler --version   # 3.x or newer
```

### 2. Authenticate

```bash
wrangler login
```

Opens a browser for Cloudflare OAuth. Approve; you're in.

### 3. Set secrets

From this directory (`Career/artifacts/landing_site/worker/`):

```bash
# Required for /api/chat
wrangler secret put ANTHROPIC_API_KEY
# Paste the key when prompted. Use a dedicated key for the demo (scope-limited + rate-limited).

# Required only if you want /api/fire-routine to work
wrangler secret put ROUTINE_URL
# Paste the full URL from claude.ai/code/routines (looks like https://api.anthropic.com/v1/claude_code/routines/trig_.../fire)

wrangler secret put ROUTINE_TOKEN
# Paste the bearer token shown once when you click Generate token in the routine edit modal
```

### 4. Deploy

```bash
wrangler deploy
```

This pushes the worker, attaches it to `aesresearch.ai/api/*` per the routes in `wrangler.toml`, and prints the final URL.

### 5. Verify

```bash
# Should return a streaming response
curl -N -X POST https://aesresearch.ai/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"what do you remember about db mocking?"}'
```

You should see SSE frames:
- `event: layer` frames for membrane, memory, attention
- `event: delta` frames with the response body
- `event: done` at the end

If the frontend at aesresearch.ai/demo doesn't see responses, check:
1. CORS — origin must be in `ALLOWED_ORIGINS` in `worker.js`
2. Routes — `wrangler.toml` must point at the right zone
3. Secrets — `wrangler secret list` to confirm keys are set

---

## Local dev

```bash
wrangler dev
```

Runs the worker on `http://localhost:8787`. Update `API_BASE` in `demo/app.js` temporarily to point there for local testing.

---

## Routine creation (one-time, UI only)

The Claude Routines platform requires UI creation for new routines. API-only creation is not yet supported.

1. Go to [claude.ai/code/routines](https://claude.ai/code/routines)
2. **New routine**
3. **Name:** `AES Research — deep-dive demo`
4. **Prompt:** use the contents of `routine_prompt.md` in this directory (TODO: to be authored)
5. **Repositories:** (none needed for demo; add `aesresearch-site` read-only if you want the routine to reference published content)
6. **Environment:** Default
7. **Select a trigger → Add another trigger → API**
8. Save, then click **Generate token** and copy it immediately (shown once)
9. Copy the `/fire` URL from the same modal
10. Paste both into `wrangler secret put` commands above

---

## Operation notes

- **Per-account daily routine limit** applies to `/api/fire-routine`. Monitor at [claude.ai/settings/usage](https://claude.ai/settings/usage).
- **Anthropic API key** drives `/api/chat`. Set a monthly spend cap on the key at [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing).
- **Rate limiting:** MVP has no per-visitor rate limit. Add Cloudflare Workers KV + sliding-window counter before public launch if abuse is a concern.
- **Observability:** `wrangler tail` streams request logs. For persistent logs, wire up Workers Analytics Engine.

---

## Architecture rationale

Why a Worker in front of the API instead of calling Claude directly from the browser?

1. **Secret protection.** The Anthropic API key stays server-side. No way for a client to exfiltrate it.
2. **Rate control.** Worker can enforce per-IP or per-visitor limits before burning API budget.
3. **Prompt control.** The system prompt that enforces the architecture layer protocol lives server-side — visitors can't edit it out to bypass the demo structure.
4. **Same-origin routing.** `/api/*` on the same domain as the site avoids CORS complexity and makes the demo feel integrated.

---

## What the demo is *not*

- It is not the real AES Research production memory, orchestration, or skeptic-membrane systems.
- The memory fixture is a tiny throwaway set, not the real body of work.
- The routine prompt is a calibrated teaching demo, not the proprietary work.

The goal is to show the **patterns** in motion, not expose the implementation.
