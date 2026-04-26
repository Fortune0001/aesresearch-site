/**
 * AES Research inbound email auto-acknowledge Worker.
 *
 * Bound to Email Routing for contact@aesresearch.ai (and any other custom address).
 * Behavior:
 *   1. RFC 3834 loop guards — refuse to reply if Auto-Submitted, List-Unsubscribe, or
 *      List-Id headers are present, or if From matches noreply/donotreply/etc.
 *   2. Per-sender 7-day rate limit via KV (one auto-reply per sender per week).
 *   3. Global 50/day circuit breaker via KV (catastrophic-spam defense).
 *   4. Rule-based template selection: T2 (recruiter) if From domain looks like
 *      an ATS / recruiter platform; T3 (peer) otherwise. T1 fallback.
 *   5. Forward the original message to Daniel's gmail (handled by Email Routing
 *      rules at the dashboard level — this Worker doesn't need to do it explicitly).
 *
 * Bindings (wrangler.toml):
 *   AUTO_ACK_KV   — KV namespace for per-sender + global counters
 *
 * No secrets needed for P0 (rule-based, no LLM).
 */

const RECRUITER_DOMAINS = [
  'workable.com', 'lever.co', 'greenhouse.io', 'ashbyhq.com',
  'recruitee.com', 'jobvite.com', 'icims.com', 'taleo.net',
  'avature.net', 'smartrecruiters.com', 'bamboohr.com',
  'myworkday.com', 'workdayjobs.com', 'workday.com',
  'successfactors.com', 'sapsf.com',
  'oraclecloud.com', 'oracle.com', // OracleHR / Taleo Cloud
  'breezy.hr', 'pinpointhq.com', 'rippling.com',
  'recruiter.', // catch-all prefix matches like 'recruiter.linkedin.com'
];

const NEVER_REPLY_FROM = /^(noreply|no-reply|donotreply|do-not-reply|do_not_reply|noresponse|no-response|auto-reply|autoreply|auto_reply|mailer-daemon|postmaster|bounce|notification|notifications|alert|alerts|hello|info|support|sales|admin|robot|system|daemon|cron)@/i;

const HEADERS_BUFFER_LIMIT = 64 * 1024; // 64KB; well above typical header sizes

const T1 = `Thanks for the message. I read every email and reply personally to those I can engage with. If your message is about a role, please share the company, the specific position, and a compensation range — that helps me prioritize.

— Daniel`;

const T2 = `Thanks for reaching out. I respond personally to recruiter inquiries that include the company name, the specific role and team, and a compensation band. With those three, I'll get back to you within a few business days.

— Daniel`;

const T3 = `Got it — thanks for writing. I'll reply personally within a few days. If it's time-sensitive, please flag in a follow-up.

— Daniel`;

// Map a classifier label → template (or null to skip the auto-reply entirely).
function templateForLabel(label) {
  switch ((label || '').toLowerCase()) {
    case 'recruiter_specific':
    case 'recruiter_generic':
    case 'recruiter':
      return { template: T2, skip: false };
    case 'peer':
    case 'researcher':
    case 'colleague':
      return { template: T3, skip: false };
    case 'spam':
    case 'notification':
    case 'transactional':
      return { template: null, skip: true };
    case 'other':
    default:
      return { template: T1, skip: false };
  }
}

// Fallback rule-based classifier — used when both Gemini and Haiku are unavailable.
function ruleBasedLabel(fromAddr) {
  const addr = fromAddr.toLowerCase();
  for (const dom of RECRUITER_DOMAINS) {
    if (addr.includes(dom)) return 'recruiter_generic';
  }
  if (/@(gmail|outlook|hotmail|yahoo|icloud|fastmail|protonmail|proton\.me|aol)\./i.test(addr)) {
    return 'peer';
  }
  return 'other';
}

// Format the excerpt sent to the LLM classifier. Body has already been captured
// by readHeadersAndBody; this just shapes it (strips quotes / signatures / caps).
function shapeClassifierExcerpt(headers, bodyExcerpt, fromAddr) {
  const subject = (/^Subject:\s*(.+)$/im.exec(headers)?.[1] || '').replace(/[\r\n]/g, ' ').slice(0, 200);
  const cleaned = (bodyExcerpt || '')
    .replace(/^>+.*$/gm, '')              // strip quoted reply chains
    .replace(/--\s*\n[\s\S]*$/m, '')      // strip signature delimiter onward
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 600);
  return `From: ${fromAddr}\nSubject: ${subject}\n\n${cleaned}`;
}

const CLASSIFIER_SYSTEM = `You are an email-triage classifier for an independent AI researcher's inbox. Read the email excerpt and reply with ONE word from this fixed set, nothing else:

- recruiter_specific: Recruiter pitch with named company AND specific role/title AND (compensation OR specific team)
- recruiter_generic: Generic recruiter outreach without specifics ("exciting opportunity", "your profile", no comp / no specific role)
- peer: Researcher, practitioner, or colleague writing about ideas, work, or essays — NOT a hiring inquiry
- spam: Promotional, marketing, scam, low-effort outreach
- notification: Auto-generated alert, billing notice, calendar invite, system notification
- other: Anything that doesn't clearly fit above

Respond with ONLY the label word. No explanation. No punctuation.`;

async function classifyWithGemini(env, excerpt) {
  if (!env.GEMINI_API_KEY) return null;
  try {
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=${env.GEMINI_API_KEY}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: CLASSIFIER_SYSTEM }] },
        contents: [{ parts: [{ text: excerpt }] }],
        generationConfig: { temperature: 0, maxOutputTokens: 16 },
      }),
    });
    if (!r.ok) {
      console.warn(`[classifier:gemini] HTTP ${r.status}`);
      return null;
    }
    const j = await r.json();
    const text = j.candidates?.[0]?.content?.parts?.[0]?.text || '';
    return text.trim().toLowerCase().split(/\s+/)[0] || null;
  } catch (e) {
    console.warn(`[classifier:gemini] error: ${(e.message || e).toString().slice(0, 200)}`);
    return null;
  }
}

async function classifyWithHaiku(env, excerpt) {
  if (!env.ANTHROPIC_API_KEY) return null;
  try {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 16,
        system: CLASSIFIER_SYSTEM,
        messages: [{ role: 'user', content: excerpt }],
      }),
    });
    if (!r.ok) {
      console.warn(`[classifier:haiku] HTTP ${r.status}`);
      return null;
    }
    const j = await r.json();
    const text = j.content?.[0]?.text || '';
    return text.trim().toLowerCase().split(/\s+/)[0] || null;
  } catch (e) {
    console.warn(`[classifier:haiku] error: ${(e.message || e).toString().slice(0, 200)}`);
    return null;
  }
}

// Three-layer classifier: Gemini primary → Haiku fallback → rule-based final.
// Returns { label, source } where source is 'gemini' | 'haiku' | 'rule'.
async function classify(env, excerpt, fromAddr) {
  const gem = await classifyWithGemini(env, excerpt);
  if (gem) return { label: gem, source: 'gemini' };
  const hai = await classifyWithHaiku(env, excerpt);
  if (hai) return { label: hai, source: 'haiku' };
  return { label: ruleBasedLabel(fromAddr), source: 'rule' };
}

function unfoldHeaders(raw) {
  // RFC 5322 line folding: a header can span multiple lines if continuation lines
  // start with whitespace. Unfold by joining the wrap.
  return raw.replace(/\r?\n[ \t]+/g, ' ');
}

function extractFromAddr(rawHeaders) {
  const unfolded = unfoldHeaders(rawHeaders);
  const m = /^From:\s*(.+)$/im.exec(unfolded);
  if (!m) return '';
  // "Display Name <addr@host>" or bare addr or with comments "(human) <addr@host>"
  const angled = /<([^>]+)>/.exec(m[1])?.[1];
  let email = angled || m[1].trim();
  // Strip RFC 5322 comments and extra fields after the address
  email = email.replace(/\s*\([^)]*\)\s*/g, '').replace(/[\s,;].*$/, '').trim();
  return email;
}

function hasHeader(rawHeaders, name) {
  const re = new RegExp(`^${name}\\s*:`, 'im');
  return re.test(rawHeaders);
}

async function readHeadersAndBody(message) {
  // Single-pass read of the RFC-822 stream. Returns { headers, bodyExcerpt }.
  // Caps headers at 64KB and body excerpt at 4KB so the classifier never sees
  // the full message body — privacy mitigation for free-tier LLM retention.
  const HEADER_LIMIT = HEADERS_BUFFER_LIMIT; // 64KB
  const BODY_EXCERPT_LIMIT = 4096;
  const reader = message.raw.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  let headers = '';
  let bodyExcerpt = '';
  let pastHeaders = false;
  let bodyBytesRead = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      if (!pastHeaders) {
        const sepCRLF = buf.indexOf('\r\n\r\n');
        const sepLF = buf.indexOf('\n\n');
        const sep = sepCRLF !== -1 ? sepCRLF : (sepLF !== -1 ? sepLF : -1);
        if (sep !== -1) {
          headers = buf.slice(0, sep);
          buf = buf.slice(sep).replace(/^[\r\n]+/, '');
          pastHeaders = true;
        } else if (buf.length >= HEADER_LIMIT) {
          headers = buf.slice(0, HEADER_LIMIT);
          buf = '';
          pastHeaders = true;
        }
      }
      if (pastHeaders) {
        const need = BODY_EXCERPT_LIMIT - bodyBytesRead;
        if (need > 0) {
          const take = Math.min(need, buf.length);
          bodyExcerpt += buf.slice(0, take);
          bodyBytesRead += take;
          buf = buf.slice(take);
        }
        if (bodyBytesRead >= BODY_EXCERPT_LIMIT) break;
      }
    }
  } finally {
    try { reader.cancel(); } catch {}
  }
  return { headers, bodyExcerpt };
}

function buildReply(originalHeaders, originalMessageId, fromAddr, template) {
  const today = new Date().toUTCString();
  // Generate a unique Message-ID for the reply. Cloudflare's send_email path
  // requires this header — without it the reply throws "no message-id set".
  const replyId = `<reply.${Date.now()}.${Math.random().toString(36).slice(2, 10)}@aesresearch.ai>`;
  const headers = [
    `From: contact@aesresearch.ai`,
    `To: ${fromAddr}`,
    `Subject: Re: ${(/^Subject:\s*(.+)$/im.exec(originalHeaders)?.[1] || '(your message)').replace(/[\r\n]/g, ' ').slice(0, 200)}`,
    `Date: ${today}`,
    `Message-ID: ${replyId}`,
    `MIME-Version: 1.0`,
    `Content-Type: text/plain; charset=utf-8`,
    `Auto-Submitted: auto-replied`,
    `Precedence: auto_reply`,
    `In-Reply-To: ${originalMessageId}`,
    `References: ${originalMessageId}`,
  ].join('\r\n');
  return `${headers}\r\n\r\n${template}\r\n`;
}

function rawToStream(raw) {
  // EmailMessage's third argument is documented as a ReadableStream. Coercion of a
  // plain string works today but is undocumented and a silent failure risk on any
  // runtime update. Encode explicitly.
  const bytes = new TextEncoder().encode(raw);
  return new ReadableStream({
    start(controller) {
      controller.enqueue(bytes);
      controller.close();
    },
  });
}

export default {
  async email(message, env, ctx) {
    try {
      const { headers, bodyExcerpt } = await readHeadersAndBody(message);
      const headerFromAddr = extractFromAddr(headers);
      // SMTP envelope sender — required as the `to` argument on EmailMessage so
      // Cloudflare's DMARC-aligned reply path matches the receiving MTA's view of
      // the sender. ATS-sent recruiter mail routinely uses a bounce envelope
      // different from the From: header; using header-from would silently fail on
      // exactly the recruiter use case this worker is built for.
      const envelopeFrom = (message.from || '').trim();
      const replyTo = envelopeFrom || headerFromAddr;
      // Display address used in the To: MIME header inside the reply body — keep
      // the human-readable header-from where present; fall back to envelope.
      const displayTo = headerFromAddr || envelopeFrom;

      // Loop guards (operate on the header-from which is the human-visible identity)
      if (!replyTo) return;
      if (NEVER_REPLY_FROM.test(replyTo)) return;
      if (headerFromAddr && NEVER_REPLY_FROM.test(headerFromAddr)) return;
      if (hasHeader(headers, 'Auto-Submitted')) {
        // RFC 3834: only `no` allows auto-reply. Empty value is conservative-treat
        // as auto-submitted (a common bug is to set an empty header to avoid the
        // attribute; we should NOT auto-reply in that case).
        const m = /^Auto-Submitted:\s*(.*)$/im.exec(headers);
        const val = (m && m[1] || '').trim();
        if (val === '' || !/^no$/i.test(val)) return;
      }
      if (hasHeader(headers, 'List-Unsubscribe') || hasHeader(headers, 'List-Id')) return;
      if (hasHeader(headers, 'Precedence')) {
        const m = /^Precedence:\s*(.+)$/im.exec(headers);
        if (m && /^(bulk|junk|list|auto_reply)$/i.test(m[1].trim())) return;
      }

      // Global 50/day circuit breaker — checked BEFORE per-sender lock so a tripped
      // breaker doesn't cause the sender to be locked out for 7 days without ever
      // receiving an auto-ack.
      let globalKey = null;
      let nextCount = 0;
      if (env.AUTO_ACK_KV) {
        const day = new Date().toISOString().slice(0, 10);
        globalKey = `ack:global:${day}`;
        const raw = await env.AUTO_ACK_KV.get(globalKey);
        const count = raw ? parseInt(raw, 10) : 0;
        if (count >= 50) {
          console.warn('email-worker: daily circuit breaker tripped');
          return;
        }
        nextCount = count + 1;
      }

      // Per-sender 7-day rate limit — keyed on envelope sender. Check first; defer
      // the WRITE until after the reply succeeds (otherwise a failed send locks
      // the sender out for 7 days without ever receiving an acknowledgement).
      let senderKey = null;
      if (env.AUTO_ACK_KV) {
        senderKey = `ack:sender:${replyTo.toLowerCase()}`;
        const last = await env.AUTO_ACK_KV.get(senderKey);
        if (last) return;
      }

      // Three-layer LLM classifier (Gemini primary → Haiku fallback → rule-based).
      // Pick template OR skip the auto-reply if classifier flags spam/notification.
      // Excerpt is body-capped + signature-stripped before leaving our infra.
      const excerpt = shapeClassifierExcerpt(headers, bodyExcerpt, replyTo);
      const { label, source } = await classify(env, excerpt, replyTo);
      const decision = templateForLabel(label);
      console.log(`[classifier:${source}] ${replyTo} → ${label} → ${decision.skip ? 'SKIP' : 'reply'}`);
      if (decision.skip) return;
      const template = decision.template;

      // Build + send the reply. Increment global counter only after a successful
      // send; if reply throws (DMARC, rate, etc.), the per-sender lock is already
      // set which prevents retry loops, but the global counter doesn't burn.
      const rawMessageId = (/^Message-ID:\s*(.+)$/im.exec(headers)?.[1] || '').trim();
      const messageId = rawMessageId || `<unknown@aesresearch.ai>`;
      const replyRaw = buildReply(headers, messageId, displayTo, template);

      try {
        const { EmailMessage } = await import('cloudflare:email');
        const reply = new EmailMessage('contact@aesresearch.ai', replyTo, rawToStream(replyRaw));
        await message.reply(reply);
        // Reply succeeded — commit the per-sender lock and increment global counter.
        if (senderKey && env.AUTO_ACK_KV) {
          await env.AUTO_ACK_KV.put(senderKey, '1', { expirationTtl: 7 * 24 * 3600 });
        }
        if (globalKey && env.AUTO_ACK_KV) {
          await env.AUTO_ACK_KV.put(globalKey, String(nextCount), { expirationTtl: 48 * 3600 });
        }
        // Forward the ORIGINAL message to Daniel's gmail so it archives.
        try {
          await message.forward('dhiguera1980@gmail.com');
        } catch (fwdErr) {
          console.error(`forward to gmail failed: ${(fwdErr.message || fwdErr).slice(0, 200)}`);
        }
      } catch (sendErr) {
        // DMARC failures, rate-limit-from-Cloudflare, malformed-message rejects
        // all surface as exceptions from message.reply(). Classify by message
        // shape so observability isn't a single blob.
        const msg = (sendErr && (sendErr.message || String(sendErr))) || 'unknown';
        let kind = 'send_failed';
        if (/dmarc/i.test(msg)) kind = 'dmarc_fail';
        else if (/rate/i.test(msg)) kind = 'send_rate_limited';
        else if (/sender|recipient|address/i.test(msg)) kind = 'addr_invalid';
        console.error(`email-worker reply ${kind}: ${msg.slice(0, 300)} (envelopeFrom=${envelopeFrom}, headerFrom=${headerFromAddr})`);
      }
    } catch (e) {
      console.error('email-worker error:', e.message || e);
    }
  },
};
