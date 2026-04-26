# aesresearch-email-ack — inbound auto-acknowledge

Cloudflare Email Worker that auto-acknowledges inbound mail to `contact@aesresearch.ai`.

## Deploy

1. Create a KV namespace: `wrangler kv namespace create AUTO_ACK_KV`
2. Copy the returned ID into `wrangler.toml` (`id = "..."`).
3. `wrangler deploy`

## Wire to Email Routing

The Worker handles `email()` events but only fires when Email Routing dispatches mail to it. After deploying:

1. Cloudflare dashboard → aesresearch.ai zone → Email → Email Routing → Email Workers tab
2. Confirm `aesresearch-email-ack` appears in the list
3. Email Routing → Routing rules → edit the `contact@aesresearch.ai` rule
4. Change Action from "Send to an email" to "Send to a Worker"
5. Select `aesresearch-email-ack`
6. (Optional) Add a second rule: matching action "Send to an email" → dhiguera1980@gmail.com so the original still archives to Gmail in addition to the auto-ack firing

Alternatively, the Worker itself could call `message.forward(...)` after replying — but the dashboard-level rule is cleaner.

## Behavior

- RFC 3834 compliant — refuses to reply to anything with `Auto-Submitted`, `List-*`, `Precedence: bulk/list`, or `noreply@`-style senders
- Per-sender rate limit: one auto-reply per sender per 7 days
- Global circuit breaker: 50 auto-replies per day max
- Templates:
  - T2 (recruiter): for known ATS/recruiter platform domains (Workable, Lever, Greenhouse, Ashby, etc.)
  - T3 (peer): for free-mail providers (Gmail, Outlook, Yahoo, etc.)
  - T1 (generic): everything else
- All templates lean on selectivity, not availability — never claim "open to work" or "happy where I am"
- No Cal.com link in any auto-reply (quiet-search discipline)
