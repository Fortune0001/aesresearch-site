# aesresearch.ai — P0/P1 Deploy Runbook

**Status as of 2026-04-26 evening:** all code in place, blitz-tested, NOT deployed. This runbook is what you run when you're back and have reviewed.

Nothing here hits the Anthropic API. P0 has zero LLM endpoints; the new `/ask` endpoints in P1 are scaffolded but won't execute until corpus is loaded (deferred to a P2 sweep).

---

## 0. Pre-flight checks (5 min)

Verify state before any deploy:

```bash
cd /c/Users/DH/Documents/AI_Space/Career/artifacts/landing_site

# Static site builds clean
python build.py
# Expected: builds index, contact, skills, about, writing/index, all 5 essays

# Worker JS parses
node -e "import('./worker/worker.js').then(()=>console.log('OK'))" --input-type=module
node -e "import('./email-worker/worker.js').then(()=>console.log('OK'))" --input-type=module
```

All three must print OK before proceeding.

---

## 1. Provision the Worker secret (one-time, ~1 min)

Turnstile site key is already in `contact.html` (`0x4AAAAAADDznW5kWs34FNOD`).
Turnstile secret key is in `~/.keys.env` as `TURNSTILE_SECRET_AESRESEARCH` — push it to the Worker:

```bash
cd worker
echo $(grep TURNSTILE_SECRET_AESRESEARCH ~/.keys.env | cut -d= -f2) | wrangler secret put TURNSTILE_SECRET_KEY
```

(Or run `wrangler secret put TURNSTILE_SECRET_KEY` and paste the value when prompted.)

If you skip this step, `/contact` will accept all submissions without captcha verification (the Worker logs a warning and proceeds). Once the secret is set, captcha is enforced.

---

## 2. WORKER_BUDGET KV namespace — already provisioned ✓

`WORKER_BUDGET` was created in this session. ID `1b74395677b742ff917ac05ec0516db1` is already wired into `worker/wrangler.toml`. No action needed.

This KV stores two counters:
- `daily_spend:YYYY-MM-DD` — cents spent on Anthropic API today (cap: 500 = $5)
- `routine_fires:YYYY-MM-DD` — Routine fires today across `/fire-routine` + `/ask-deep` (cap: 100)

Both reset at UTC midnight via 48hr TTL.

---

## 3. Deploy the HTTP Worker (1 min)

```bash
cd worker
wrangler deploy
```

This deploys the Worker to `api.aesresearch.ai` — replaces the existing `/chat` + `/fire-routine` Worker with the new version that adds `/contact` (and `/ask` + `/ask-deep` from the Q&A bot scaffold).

After deploy, verify:

```bash
# Should return 405 (only POST allowed)
curl -i https://api.aesresearch.ai/contact

# Should return 400 invalid form data
curl -i -X POST -H 'Content-Type: application/json' -d '{}' https://api.aesresearch.ai/contact
```

---

## 4. Deploy the Email Worker (2 min)

```bash
cd email-worker
wrangler deploy
```

This pushes the auto-acknowledge Worker to Cloudflare. **It does nothing yet** — Email Routing isn't binding to it.

---

## 5. Wire the Email Worker to inbound mail (3 min, dashboard)

Cloudflare dashboard → `aesresearch.ai` zone → **Email** → **Email Routing** → **Routing rules**:

1. Find the existing `contact@aesresearch.ai` rule
2. Click Edit
3. Change Action from "Send to an email" to "Send to a Worker"
4. Select `aesresearch-email-ack`
5. Save

After this, every inbound to `contact@aesresearch.ai` flows through the Email Worker → applies templates / loop guards → fires auto-reply via `message.reply()`. The original message is archived because the Worker doesn't drop it (it just generates a reply alongside).

**Optional:** add a parallel rule `contact@aesresearch.ai` → "Send to an email" → `dhiguera1980@gmail.com` so the original ALSO archives to your Gmail. Otherwise you'll see only auto-replies, not originals.

---

## 6. Deploy the static site (1 min)

```bash
cd /c/Users/DH/Documents/AI_Space/Career/artifacts/landing_site
WRITE_CNAME=1 python build.py --all
```

This builds + commits + force-pushes to `Fortune0001/aesresearch-site` → GitHub Pages picks it up within ~30s. Live at https://aesresearch.ai/ and the new pages: `/contact/`, `/skills/`, `/about/`, `/writing/`, `/ask/`.

**Confirm before running:** the active session (resume + cover letter + draft revisions) hasn't published anything to `writing/_drafts/` since this session started. If they have, your changes will deploy alongside theirs without conflict (different file scopes).

---

## 7. Smoke-test live (5 min)

After all 6 steps, verify end-to-end:

1. **Contact form:** visit https://aesresearch.ai/contact/ — fill out name/email/intent/message → submit. Should land in your Gmail inbox within 30s with subject `[aesresearch:role] ...`. Auto-reply should fire to your test address.
2. **Email auto-ack:** send a test email from a personal address to `contact@aesresearch.ai`. Within 30s, you should receive the T3 (peer template) reply. The original arrives in your Gmail (assuming you added the parallel "send to email" rule from step 5).
3. **DMARC:** wait 24 hours, then check the DMARC dashboard at Cloudflare → aesresearch.ai → Email → DMARC Management. Should show DMARC pass on every email you sent yourself.
4. **Static pages:** click through `/contact/`, `/skills/`, `/about/`, `/writing/`, `/ask/`, all four essays. Verify chrome (breadcrumbs, prev/next, dates, reading time) renders cleanly.
5. **`/ask` page:** the page loads but answers will be vacuous because the corpus stub hasn't been replaced (deferred to P2). The structure works; the substance is one config file away.

---

## 8. DMARC tightening (30 days from now)

Today's DMARC record is `p=none` (monitoring). After 30 days of clean reports:

Cloudflare dashboard → DMARC Management → edit the `_dmarc` record:
- Change `p=none` to `p=quarantine`
- Wait another 30 days
- Then `p=reject`

I'll remind you when the window's up if I'm in the loop.

---

## What to look at if something fails

- **Form fails with "captcha failed"** → you skipped step 1. Re-run `wrangler secret put TURNSTILE_SECRET_KEY`.
- **Form fails silently with no inbox arrival** → check Cloudflare Workers logs: `wrangler tail aesresearch-demo`. Most likely cause: `SEND_EMAIL` binding misconfigured — verify `worker/wrangler.toml` has the `[[send_email]]` block.
- **Auto-reply never arrives** → check `wrangler tail aesresearch-email-ack`. Most likely cause: Email Routing rule still set to "Send to an email" instead of "Send to Worker."
- **Auto-reply lands in spam** → DMARC alignment issue. Check the DMARC dashboard for failure reports. Most likely cause: outbound DKIM signing not happening — verify the `cf2024-1._domainkey` DNS record exists and has the public key (it was added when Email Routing was enabled).
- **Live site shows old content** → GitHub Pages cache or CDN. Force-refresh; wait 60s; try a hard refresh.

---

## What this doesn't cover (P1+ backlog)

- Actually loading the corpus into the `/ask` system prompt (deferred — Q&A scaffold has placeholder)
- Real GitHub Releases for the v0.3 Skills versions claimed in the index (deferred — flag in P2)
- The Routine `/api/ask-deep` deep-response prompt template (scaffolded but not wired to the actual Routine logic)
- Daily cost-monitoring Routine (still on the design table)
- Hybrid review-first → direct-with-CC promotion logic for Routine responses (manual for now)

Each of these is a discrete next step. None are required to launch.
