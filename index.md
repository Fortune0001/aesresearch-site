# AES Research

**AI R&D for long-horizon agentic systems.**

I build the architectural patterns that let multi-agent systems survive real production work — not demo runs, not controlled benchmarks, but the kind of long-horizon autonomous operation where context compounds, memory matters, and every autonomous output has to be verifiable before it goes anywhere.

---

## What I work on

- **Two-tier memory architectures** that persist across 40+ agent sessions without context bloat
- **Cross-project director agents** coordinating sub-agent swarms via role-tagged addressing and role-boundary self-monitoring
- **UAT harnesses** that surface the residual context gap — the failure modes synthetic benchmarks miss
- **Skeptic membranes** that enforce verifiable outputs and retained human authority on autonomous agent work
- **Production ML pipelines** with factor capture, ensemble clustering, and multi-year out-of-sample validation

## Writing

- **[Two-tier memory for production agents: what chat systems don't tell you](writing/two-tier-memory.html)** — a working architecture for agents that need to remember across sessions without choking on their own context
- **[The context window is a battery: surviving compaction on long-running agents](writing/context-window-battery.html)** — what happens to your calibration when the context fills up, why compaction drops the work you need most, and the discipline that protects you from it
- **[Attention management: routing between native LLM capability and augmented skills and tools](writing/attention-management.html)** — the control plane that decides, at every step, where the work should happen

More deep-dives in progress.

## Live demo

**[Try the live architecture demo &rarr;](demo/)** Type a question and watch the skeptic membrane, two-tier memory lookup, and attention-routing decisions fire in real time alongside the response. Backed by a Cloudflare Worker that keeps the API keys server-side and enforces the demo prompt; the worker source is open at [/worker/](worker/).

---

## About

AES Research is the independent R&D program of **Daniel Higuera**, run since 2017 in parallel with industrial R&D leadership at Hitachi Energy (grid-planning and wholesale-market software for North American ISOs and utilities). The work spans 12+ AI-native projects under a unified agentic architecture.

Twenty years of professional experience across energy markets, production ML, and industrial software. AI and ML expertise developed independently over 15+ years, predating formal academic curricula for most modern sub-disciplines.

[LinkedIn](https://www.linkedin.com/in/daniel-higuera-09053925) · Résumé available on request · Contact via LinkedIn or email
