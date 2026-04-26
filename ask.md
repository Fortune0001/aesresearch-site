# Ask

*Try the AES Research Q&A agent — answers grounded in the published essays and skills, with citations.*

---

The AES Research Q&A agent is a lightweight interface to the ideas in the writing here. Ask it to explain a concept from the essays, walk through a pattern, compare approaches, or help you figure out whether a particular architecture applies to your situation. Every answer cites the source essay or skill it draws from.

What the agent is good at: questions about the specific patterns documented here — two-tier memory, skeptic membranes, attention routing, context-window discipline, the maturity model, the geometry-of-calibration framing. It reads the published corpus and cites from it.

What the agent is not: it doesn't have access to the internet, your codebase, or any live data. It won't act on your behalf. It's a read-only interface to a fixed corpus. For questions that go deeper than what the essays cover — architecture reviews, bespoke analysis, extended back-and-forth — use the "Send to research agent" button. That fires Daniel's research agent, which writes a thorough response and sends it to Daniel for review. You'll get a response within a few business days.

---

<div class="ask-widget">

<form class="ask-form" id="ask-form" novalidate>
  <label class="honeypot" aria-hidden="true">
    Leave this field empty
    <input type="text" name="company_url" id="ask-honeypot" tabindex="-1" autocomplete="off">
  </label>

  <div class="ask-field">
    <label for="ask-input" class="ask-label">Your question</label>
    <textarea
      id="ask-input"
      class="ask-textarea"
      name="message"
      rows="4"
      maxlength="2000"
      placeholder="e.g. How does the two-tier memory index prevent context bloat?"
      required
    ></textarea>
    <div class="ask-charcount"><span id="ask-charcount">0</span> / 2000</div>
  </div>

  <!-- Cloudflare Turnstile widget -->
  <div class="cf-turnstile" data-sitekey="0x4AAAAAADDznW5kWs34FNOD" id="ask-turnstile"></div>

  <div class="ask-buttons">
    <button type="submit" id="ask-submit" class="ask-submit-button">Ask</button>
    <button type="button" id="ask-deep-trigger" class="ask-deep-button">Send to research agent &rarr;</button>
  </div>
</form>

<!-- Deep-ask overlay — prompts for visitor email before firing -->
<div id="ask-deep-overlay" class="ask-deep-overlay" style="display:none" aria-modal="true" role="dialog">
  <div class="ask-deep-dialog">
    <p class="ask-deep-dialog-title">Send to research agent</p>
    <p class="ask-deep-dialog-body">Daniel's research agent will write a thorough answer drawing on the full corpus. Daniel reviews responses personally before they go out — you'll hear back within a few business days.</p>
    <label for="ask-deep-email" class="ask-label">Your email <span class="ask-optional">(optional — to be CC'd after review)</span></label>
    <input type="email" id="ask-deep-email" class="ask-deep-email-input" placeholder="you@example.com" maxlength="200">
    <div class="ask-deep-dialog-buttons">
      <button type="button" id="ask-deep-confirm" class="ask-submit-button">Send request</button>
      <button type="button" id="ask-deep-cancel" class="ask-deep-cancel-button">Cancel</button>
    </div>
  </div>
</div>

<!-- Conversation transcript -->
<div id="ask-transcript" class="ask-transcript" aria-live="polite" aria-atomic="false"></div>

<!-- Status message -->
<div id="ask-status" class="ask-status" role="status" aria-live="polite"></div>

</div>

<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<script>
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Config
  // ---------------------------------------------------------------------------
  const API_BASE = 'https://api.aesresearch.ai';
  const ASK_ENDPOINT = API_BASE + '/ask';
  const ASK_DEEP_ENDPOINT = API_BASE + '/ask-deep';
  const TIMEOUT_MS = 45000; // SSE may take longer than a JSON round-trip

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let sessionId = '';
  let conversationHistory = []; // [{role, content}]
  let abortController = null;

  function generateSessionId() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
    return 'sess-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }

  // ---------------------------------------------------------------------------
  // DOM refs
  // ---------------------------------------------------------------------------
  const form = document.getElementById('ask-form');
  const textarea = document.getElementById('ask-input');
  const charCount = document.getElementById('ask-charcount');
  const submitBtn = document.getElementById('ask-submit');
  const deepTrigger = document.getElementById('ask-deep-trigger');
  const deepOverlay = document.getElementById('ask-deep-overlay');
  const deepEmailInput = document.getElementById('ask-deep-email');
  const deepConfirmBtn = document.getElementById('ask-deep-confirm');
  const deepCancelBtn = document.getElementById('ask-deep-cancel');
  const transcript = document.getElementById('ask-transcript');
  const statusEl = document.getElementById('ask-status');
  const honeypot = document.getElementById('ask-honeypot');

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function setStatus(msg, isError) {
    statusEl.textContent = msg;
    statusEl.className = 'ask-status' + (isError ? ' ask-status-error' : '');
  }

  function clearStatus() {
    statusEl.textContent = '';
    statusEl.className = 'ask-status';
  }

  function getTurnstileToken() {
    if (typeof turnstile === 'undefined') return '';
    try { return turnstile.getResponse(document.getElementById('ask-turnstile')); } catch { return ''; }
  }

  function resetTurnstile() {
    if (typeof turnstile !== 'undefined') {
      try { turnstile.reset(document.getElementById('ask-turnstile')); } catch {}
    }
  }

  function setFormBusy(busy) {
    submitBtn.disabled = busy;
    deepTrigger.disabled = busy;
    textarea.disabled = busy;
    submitBtn.textContent = busy ? 'Asking…' : 'Ask';
  }

  // Append a turn block to the transcript
  function appendTurn(role, html) {
    const div = document.createElement('div');
    div.className = role === 'user' ? 'ask-message-user' : 'ask-message-agent';
    div.innerHTML = html;
    transcript.appendChild(div);
    div.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return div;
  }

  // Append a citation pill after an agent turn
  function appendCitation(container, essay, snippet) {
    const pill = document.createElement('span');
    pill.className = 'ask-citation';
    pill.title = snippet || essay;
    pill.textContent = '📄 ' + essay;
    let citationsRow = container.querySelector('.ask-citation-row');
    if (!citationsRow) {
      citationsRow = document.createElement('div');
      citationsRow.className = 'ask-citation-row';
      container.appendChild(citationsRow);
    }
    citationsRow.appendChild(pill);
  }

  // Minimal markdown-to-HTML: bold, italic, inline code, line breaks.
  // Full markdown is not needed; the agent output is prose, not complex docs.
  function minimalMarkdown(text) {
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');
  }

  // ---------------------------------------------------------------------------
  // /ask — SSE streaming
  // ---------------------------------------------------------------------------
  async function submitQuestion(message) {
    if (!sessionId) sessionId = generateSessionId();

    // Append user turn
    appendTurn('user', minimalMarkdown(message));

    // Append empty agent turn that we'll fill as deltas arrive
    const agentTurn = appendTurn('agent', '');
    let agentText = '';

    setFormBusy(true);
    clearStatus();

    abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), TIMEOUT_MS);

    let ok = false;
    try {
      const payload = {
        session_id: sessionId,
        message: message,
        history: conversationHistory.slice(-10),
        cf_turnstile_token: getTurnstileToken(),
      };

      const resp = await fetch(ASK_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: abortController.signal,
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || 'Request failed (' + resp.status + ')');
      }

      // SSE reader
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let sseBuffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        sseBuffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = sseBuffer.indexOf('\n\n')) !== -1) {
          const frame = sseBuffer.slice(0, idx);
          sseBuffer = sseBuffer.slice(idx + 2);
          let eventName = 'message';
          let dataStr = '';
          for (const line of frame.split('\n')) {
            if (line.startsWith('event:')) eventName = line.slice(6).trim();
            else if (line.startsWith('data:')) dataStr = line.slice(5).trim();
          }
          if (!dataStr) continue;
          let data;
          try { data = JSON.parse(dataStr); } catch { continue; }

          if (eventName === 'delta') {
            agentText += data.text || '';
            agentTurn.innerHTML = '<p>' + minimalMarkdown(agentText) + '</p>';
          } else if (eventName === 'citation') {
            appendCitation(agentTurn, data.essay, data.snippet);
          } else if (eventName === 'escalate') {
            const note = document.createElement('div');
            note.className = 'ask-escalate-note';
            note.innerHTML = 'This question is outside the corpus scope'
              + (data.reason ? ' (' + minimalMarkdown(data.reason) + ')' : '') + '. '
              + 'Try the <button class="ask-escalate-deep-btn" type="button">research agent</button> for a thorough response.';
            note.querySelector('.ask-escalate-deep-btn').addEventListener('click', openDeepOverlay);
            agentTurn.appendChild(note);
          } else if (eventName === 'done') {
            ok = true;
            // Save to history
            conversationHistory.push({ role: 'user', content: message });
            conversationHistory.push({ role: 'assistant', content: agentText });
            if (conversationHistory.length > 20) conversationHistory = conversationHistory.slice(-20);
          } else if (eventName === 'error') {
            throw new Error(data.message || 'Stream error');
          }
        }
      }
      if (!ok) {
        // Stream closed without done event — still treat as success if we got text
        if (agentText) {
          conversationHistory.push({ role: 'user', content: message });
          conversationHistory.push({ role: 'assistant', content: agentText });
        }
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        setStatus('Request timed out. Please try again.', true);
      } else {
        setStatus(e.message || 'Something went wrong. Please try again.', true);
      }
      if (!agentText) agentTurn.remove();
    } finally {
      clearTimeout(timeoutId);
      abortController = null;
      setFormBusy(false);
      resetTurnstile();
    }
  }

  // ---------------------------------------------------------------------------
  // /ask-deep — async Routine fire
  // ---------------------------------------------------------------------------
  function openDeepOverlay() {
    deepOverlay.style.display = '';
    deepEmailInput.focus();
  }

  async function fireDeepRequest(requestedByEmail) {
    if (!sessionId) sessionId = generateSessionId();
    const message = textarea.value.trim();
    if (!message) {
      setStatus('Enter a question first, then click "Send to research agent".', true);
      return;
    }

    deepConfirmBtn.disabled = true;
    deepConfirmBtn.textContent = 'Sending…';
    clearStatus();

    try {
      const payload = {
        session_id: sessionId,
        message: message,
        history: conversationHistory.slice(-10),
        requested_by_email: requestedByEmail,
        cf_turnstile_token: getTurnstileToken(),
      };

      const abortCtrl = new AbortController();
      const tid = setTimeout(() => abortCtrl.abort(), 15000);

      const resp = await fetch(ASK_DEEP_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: abortCtrl.signal,
      });
      clearTimeout(tid);

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || 'Request failed (' + resp.status + ')');
      }

      const data = await resp.json().catch(() => ({}));
      if (!data.ok) throw new Error(data.error || 'Failed to queue request');

      deepOverlay.style.display = 'none';
      appendTurn('agent',
        '<p><strong>Sent to research agent.</strong> Daniel reviews these personally; '
        + 'you\'ll get a response within a few business days.'
        + (requestedByEmail ? ' We have your email.' : '') + '</p>');
      resetTurnstile();
    } catch (e) {
      if (e.name === 'AbortError') {
        setStatus('Request timed out. Please try again.', true);
      } else {
        setStatus(e.message || 'Something went wrong. Please try again.', true);
      }
    } finally {
      deepConfirmBtn.disabled = false;
      deepConfirmBtn.textContent = 'Send request';
    }
  }

  // ---------------------------------------------------------------------------
  // Event wiring
  // ---------------------------------------------------------------------------
  textarea.addEventListener('input', function () {
    charCount.textContent = textarea.value.length;
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (honeypot && honeypot.value) return; // bot trap
    const message = textarea.value.trim();
    if (!message) { setStatus('Please enter a question.', true); return; }
    submitQuestion(message);
    textarea.value = '';
    charCount.textContent = '0';
  });

  deepTrigger.addEventListener('click', function () {
    if (honeypot && honeypot.value) return;
    openDeepOverlay();
  });

  deepConfirmBtn.addEventListener('click', function () {
    const email = deepEmailInput.value.trim();
    fireDeepRequest(email);
  });

  deepCancelBtn.addEventListener('click', function () {
    deepOverlay.style.display = 'none';
  });

  // Close overlay on backdrop click
  deepOverlay.addEventListener('click', function (e) {
    if (e.target === deepOverlay) deepOverlay.style.display = 'none';
  });

  // Close overlay on Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && deepOverlay.style.display !== 'none') {
      deepOverlay.style.display = 'none';
    }
  });

})();
</script>

<!--
CSS classes used by this page (add to style.css in a follow-up pass):

  .ask-widget           — outer container for the form + transcript
  .ask-form             — the question form
  .ask-field            — label + textarea wrapper
  .ask-label            — field label
  .ask-textarea         — question textarea
  .ask-charcount        — character count row below textarea
  .ask-buttons          — flex row holding the two buttons
  .ask-submit-button    — primary "Ask" button (and "Send request" in dialog)
  .ask-deep-button      — secondary "Send to research agent" button
  .ask-transcript       — scrollable conversation area
  .ask-message-user     — a user turn in the transcript
  .ask-message-agent    — an agent turn in the transcript
  .ask-citation-row     — flex row of citation pills below an agent turn
  .ask-citation         — a single citation pill (essay name, hover = snippet)
  .ask-escalate-note    — inline note when agent emits <escalate/>
  .ask-escalate-deep-btn — inline text-button inside escalate note
  .ask-status           — status / error message below the form
  .ask-status-error     — modifier: red text for errors
  .ask-optional         — muted secondary text (e.g., "optional" label hint)
  .ask-deep-overlay     — full-screen semi-transparent overlay for deep-ask dialog
  .ask-deep-dialog      — the dialog box inside the overlay
  .ask-deep-dialog-title    — dialog heading
  .ask-deep-dialog-body     — dialog explanatory paragraph
  .ask-deep-email-input     — email input inside the dialog
  .ask-deep-dialog-buttons  — flex row holding confirm + cancel buttons
  .ask-deep-cancel-button   — cancel button inside the dialog
-->
