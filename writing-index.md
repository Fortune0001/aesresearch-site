# Writing

*Long-form essays on agent architecture, calibration, and the patterns that hold up in production.*

---

## Featured

**[Calibration, boundary layers, and the distance between yes and no: a practitioner's geometry of LLM reliability](distance-yes-and-no.html)**

The geometric framing that ties context decay, retrieval failure, memory architecture, and agent calibration into one system. · 12 min · 2026-04-26

**[Two-tier memory for production agents: what chat systems don't tell you](two-tier-memory.html)**

An architectural pattern for agents that need to remember across sessions without choking on their own context. · 13 min · 2026-04-26

**[The 6-tier agent maturity model: why most enterprise AI is failing on a calibration mismatch, not a tooling gap](6-tier-maturity.html)**

A practitioner's tier ladder for self-locating an AI initiative — and the diagnostic that names the canonical enterprise failure in three questions. · 18 min · 2026-04-26

## Research

**[When does ML actually help LP dispatch? An honest characterization](when-does-ml-help-lp-dispatch.html)**

A predict-then-correct pipeline for production-cost dispatch, measured until it broke — where the error actually lives, three negative results with nailed mechanisms, and the case that ±1% is a solver result, not a prediction result. · 43 min · 2026-07-11

## More essays

**[Attention management: routing between native LLM capability and augmented skills and tools](attention-management.html)**

What a production agent system decides at every step — when to trust the model, when to reach for a skill, when to call a tool. · 9 min · 2026-04-26

**[The context window is a battery: surviving compaction on long-running agents](context-window-battery.html)**

What happens to your calibration when the context fills up, why compaction drops the work you need most, and the operational discipline that protects you from it. · 7 min · 2026-04-26

**[The Membrane, Traffic Cop, and Director stack: how to stop prompt injection without killing your agent pipeline](membrane-traffic-cop-director.html)**

Defense in depth for agentic workflows — five named roles that compose into a self-tuning human-in-the-loop system. · 14 min · 2026-07-04

**[The adversarial skeptic: calibration that challenges itself](adversarial-skeptic.html)**

The wrong answer that looks right is the expensive one — and the skeptic that catches it has to be suspicious of agreement, not just error. · 11 min · 2026-07-04

## Capability proofs

**[Million-row datasets, in the browser, instantly usable](million-rows-in-the-browser.html)**

The browser "can't handle" a million-row editable grid — measured proof that it's the naive architecture that can't: a million rows usable in a second or two, UI memory flat, no install. · 7 min · 2026-07-11

**[Context-unbounded codebase investigation: one method, three codebases, three languages](context-unbounded-investigation.html)**

transformers, Kubernetes, and Ray — ~6.9M lines across four languages — investigated with no reasoning context ever holding more than a bounded working set. · 8 min · 2026-07-04

**[Run report: huggingface/transformers (Python, ~2M-LOC repo)](transformers-capability-proof.html)** · 12 min · 2026-07-04

**[Run report: kubernetes/kubernetes (Go, 3.6M LOC)](kubernetes-capability-proof.html)** · 5 min · 2026-07-04

**[Run report: ray-project/ray (C++/Python/Java, polyglot)](ray-polyglot-capability-proof.html)** · 7 min · 2026-07-04

**[Metered knowledge extraction at scale: efficiency metrics from a composable research pipeline](research-pipeline-efficiency.html)** · 4 min · 2026-07-04
