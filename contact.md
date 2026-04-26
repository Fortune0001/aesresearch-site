# Contact

*How to reach me, and what I'll respond to.*

---

I read every message. I respond to those that move research or work forward.

For inquiries about potential engagements: include the organization, the scope of work, and the expected range. With those three, I'll respond personally within a few business days.

For questions about an essay: tell me which one and what you're working on. I'm happy to share more detail or pointers, especially if it changes how I'd write the next piece.

For anything else, the form below works. Or email `contact@aesresearch.ai` directly. Calendar booking is reserved for second-touch, after I've read what you sent.

<form id="contact-form" class="contact-form" method="post" action="https://api.aesresearch.ai/contact" novalidate>
  <label>Your name
    <input type="text" name="name" required maxlength="120" autocomplete="name">
  </label>
  <label>Email
    <input type="email" name="email" required maxlength="200" autocomplete="email">
  </label>
  <label>Intent
    <select name="intent" required>
      <option value="">— Select —</option>
      <option value="role">Inquiry about engagement / consulting / opportunity</option>
      <option value="essay">Question about an essay</option>
      <option value="other">Other</option>
    </select>
  </label>
  <label>Message
    <textarea name="message" required maxlength="4000"></textarea>
  </label>
  <label class="honeypot" aria-hidden="true">
    Leave this field empty
    <input type="text" name="company_url" tabindex="-1" autocomplete="off">
  </label>
  <div class="cf-turnstile" data-sitekey="0x4AAAAAADDznW5kWs34FNOD" data-size="flexible"></div>
  <button type="submit" id="contact-submit">Send</button>
  <p id="contact-status" class="form-status" role="status" aria-live="polite"></p>
</form>

<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<script>
(function () {
  var form = document.getElementById('contact-form');
  var btn = document.getElementById('contact-submit');
  var status = document.getElementById('contact-status');
  if (!form) return;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (form.company_url && form.company_url.value) return; // honeypot
    btn.disabled = true;
    status.className = 'form-status';
    status.textContent = 'Sending…';
    var token = '';
    try {
      var ts = window.turnstile && window.turnstile.getResponse && window.turnstile.getResponse();
      token = ts || '';
    } catch (_) {}
    var payload = {
      name: form.name.value.trim(),
      email: form.email.value.trim(),
      intent: form.intent.value,
      message: form.message.value.trim(),
      cf_turnstile_token: token,
    };
    var ctrl = ('AbortController' in window) ? new AbortController() : null;
    var timeoutId = ctrl ? setTimeout(function () { ctrl.abort(); }, 15000) : 0;
    fetch(form.action, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: ctrl ? ctrl.signal : undefined,
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        if (timeoutId) clearTimeout(timeoutId);
        if (res.ok) {
          status.className = 'form-status success';
          status.textContent = 'Thanks — message received. I’ll respond personally within a few business days.';
          form.reset();
          try { window.turnstile && window.turnstile.reset && window.turnstile.reset(); } catch (_) {}
        } else {
          status.className = 'form-status error';
          status.textContent = res.body && res.body.error ? res.body.error : 'Something went wrong. Try emailing contact@aesresearch.ai instead.';
          btn.disabled = false;
        }
      })
      .catch(function (err) {
        if (timeoutId) clearTimeout(timeoutId);
        status.className = 'form-status error';
        if (err && err.name === 'AbortError') {
          status.textContent = 'Request timed out. Try emailing contact@aesresearch.ai instead.';
        } else {
          status.textContent = 'Network error. Try emailing contact@aesresearch.ai instead.';
        }
        btn.disabled = false;
      });
  });
})();
</script>
