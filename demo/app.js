/* AES Research live demo — frontend client
 *
 * Talks to the Cloudflare Worker at /api/chat (streaming SSE) and /api/fire-routine.
 * The Worker keeps the Anthropic API key and the Routine bearer token server-side.
 *
 * Wire protocol (SSE events from /api/chat):
 *   event: layer         data: {"layer": "membrane"|"memory"|"attention", "decision": "...", "detail": "..."}
 *   event: delta         data: {"text": "chunk of final response"}
 *   event: done          data: {"stop_reason": "..."}
 *   event: error         data: {"message": "..."}
 */

(() => {
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const fireBtn = document.getElementById('fire-routine-btn');
  const convo = document.getElementById('conversation');
  const streamLog = document.getElementById('stream-log');

  const API_BASE = 'https://api.aesresearch.ai'; // Worker on proxied subdomain

  function renderEmptyStates() {
    if (!convo.childElementCount) {
      convo.innerHTML = '<div class="empty">No conversation yet. Type below.</div>';
    }
    if (!streamLog.childElementCount) {
      streamLog.innerHTML = '<li class="empty">No layers fired yet.</li>';
    }
  }
  renderEmptyStates();

  function clearEmptyStates() {
    const e1 = convo.querySelector('.empty');
    if (e1) e1.remove();
    const e2 = streamLog.querySelector('.empty');
    if (e2) e2.remove();
  }

  function appendTurn(role, text) {
    clearEmptyStates();
    const turn = document.createElement('div');
    turn.className = `turn ${role}`;
    turn.innerHTML = `<div class="role">${role}</div><div class="body"></div>`;
    turn.querySelector('.body').textContent = text;
    convo.appendChild(turn);
    convo.scrollTop = convo.scrollHeight;
    return turn.querySelector('.body');
  }

  function appendLayer(layer, decision, detail) {
    clearEmptyStates();
    const li = document.createElement('li');
    li.innerHTML = `
      <div class="layer layer-${layer}">${layer} &middot; ${decision}</div>
      <div class="detail"></div>
    `;
    li.querySelector('.detail').textContent = detail || '';
    streamLog.appendChild(li);
    streamLog.scrollTop = streamLog.scrollHeight;
  }

  function appendStreamError(msg) {
    clearEmptyStates();
    const li = document.createElement('li');
    li.innerHTML = `<div class="layer layer-error">error</div><div class="detail"></div>`;
    li.querySelector('.detail').textContent = msg;
    streamLog.appendChild(li);
  }

  async function streamChat(userText) {
    appendTurn('user', userText);
    const assistantBody = appendTurn('assistant', '');
    sendBtn.disabled = true;
    fireBtn.disabled = true;

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText }),
      });

      if (!res.ok || !res.body) {
        const errText = await res.text().catch(() => 'unknown');
        throw new Error(`HTTP ${res.status}: ${errText.slice(0, 200)}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE frames: event:<name>\ndata:<json>\n\n
        let idx;
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const lines = frame.split('\n');
          let eventName = 'message';
          let dataText = '';
          for (const line of lines) {
            if (line.startsWith('event:')) eventName = line.slice(6).trim();
            else if (line.startsWith('data:')) dataText += line.slice(5).trim();
          }
          if (!dataText) continue;
          let data;
          try { data = JSON.parse(dataText); } catch { continue; }

          if (eventName === 'layer') {
            appendLayer(data.layer, data.decision, data.detail);
          } else if (eventName === 'delta') {
            assistantBody.textContent += data.text || '';
            convo.scrollTop = convo.scrollHeight;
          } else if (eventName === 'error') {
            appendStreamError(data.message || 'unknown error');
          } else if (eventName === 'done') {
            // completion; do nothing
          }
        }
      }
    } catch (err) {
      appendStreamError(err.message);
      assistantBody.textContent += ` [failed: ${err.message}]`;
    } finally {
      sendBtn.disabled = false;
      fireBtn.disabled = false;
      input.focus();
    }
  }

  async function fireRoutine(userText) {
    if (!userText.trim()) {
      appendStreamError('Type a prompt first.');
      return;
    }
    sendBtn.disabled = true;
    fireBtn.disabled = true;
    appendLayer('attention', 'routing to Claude Routine', 'Dispatching to a pre-configured routine for longer-horizon autonomous work. Response is a session URL; open it in a new tab to watch.');
    try {
      const res = await fetch(`${API_BASE}/fire-routine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: userText }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      const url = data.claude_code_session_url;
      if (url) {
        appendLayer('response', 'routine fired', `Session URL: ${url}`);
        window.open(url, '_blank', 'noopener');
      } else {
        appendStreamError('Routine fire returned no session URL.');
      }
    } catch (err) {
      appendStreamError('Routine fire failed: ' + err.message);
    } finally {
      sendBtn.disabled = false;
      fireBtn.disabled = false;
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    streamChat(text);
  });

  fireBtn.addEventListener('click', () => {
    const text = input.value.trim();
    if (text) input.value = '';
    fireRoutine(text);
  });

  // Enter submits, Shift+Enter newline
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });
})();
