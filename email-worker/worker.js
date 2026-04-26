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

function selectTemplate(fromAddr) {
  const addr = fromAddr.toLowerCase();
  for (const dom of RECRUITER_DOMAINS) {
    if (addr.includes(dom)) return T2;
  }
  // Personal-domain heuristic: free-mail providers => T3 peer
  if (/@(gmail|outlook|hotmail|yahoo|icloud|fastmail|protonmail|proton\.me|aol)\./i.test(addr)) {
    return T3;
  }
  return T1;
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

async function readHeaders(message) {
  // Read just the headers portion of the raw RFC822 stream. Cap at 64KB to bound
  // memory on hostile / malformed input. Try both \r\n\r\n and \n\n (some MTAs
  // normalize line endings).
  const reader = message.raw.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  while (true) {
    if (buf.length >= HEADERS_BUFFER_LIMIT) {
      try { reader.cancel(); } catch {}
      break;
    }
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const sepCRLF = buf.indexOf('\r\n\r\n');
    const sepLF = buf.indexOf('\n\n');
    const sep = sepCRLF !== -1
      ? sepCRLF
      : (sepLF !== -1 ? sepLF : -1);
    if (sep !== -1) {
      buf = buf.slice(0, sep);
      try { reader.cancel(); } catch {}
      break;
    }
  }
  return buf;
}

function buildReply(originalHeaders, originalMessageId, fromAddr, template) {
  const today = new Date().toUTCString();
  const headers = [
    `From: contact@aesresearch.ai`,
    `To: ${fromAddr}`,
    `Subject: Re: ${(/^Subject:\s*(.+)$/im.exec(originalHeaders)?.[1] || '(your message)').replace(/[\r\n]/g, ' ').slice(0, 200)}`,
    `Date: ${today}`,
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
      const headers = await readHeaders(message);
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

      // Per-sender 7-day rate limit — keyed on envelope sender (envelope is the
      // routable identity; header can be spoofed without affecting deliverability).
      if (env.AUTO_ACK_KV) {
        const senderKey = `ack:sender:${replyTo.toLowerCase()}`;
        const last = await env.AUTO_ACK_KV.get(senderKey);
        if (last) return;
        await env.AUTO_ACK_KV.put(senderKey, '1', { expirationTtl: 7 * 24 * 3600 });
      }

      // Build + send the reply. Increment global counter only after a successful
      // send; if reply throws (DMARC, rate, etc.), the per-sender lock is already
      // set which prevents retry loops, but the global counter doesn't burn.
      const template = selectTemplate(replyTo);
      const rawMessageId = (/^Message-ID:\s*(.+)$/im.exec(headers)?.[1] || '').trim();
      const messageId = rawMessageId || `<unknown@aesresearch.ai>`;
      const replyRaw = buildReply(headers, messageId, displayTo, template);

      try {
        const { EmailMessage } = await import('cloudflare:email');
        const reply = new EmailMessage('contact@aesresearch.ai', replyTo, rawToStream(replyRaw));
        await message.reply(reply);
        if (globalKey && env.AUTO_ACK_KV) {
          await env.AUTO_ACK_KV.put(globalKey, String(nextCount), { expirationTtl: 48 * 3600 });
        }
        // Forward the ORIGINAL message to Daniel's gmail so it archives. Without
        // this, the Worker consumes the mail and only the auto-reply persists.
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
