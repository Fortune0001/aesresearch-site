# Attention management: routing between native LLM capability and augmented skills and tools

*What a production agent system decides at every step — when to trust the model, when to reach for a skill, when to call a tool. The control plane that makes the rest of the architecture work.*

---

## The routing problem

An agent with memory, orchestration, and tool access still needs to decide, at every step, *where* the work should happen. The LLM can do some things natively. Some things are better handed to a skill — a bundled instruction set with its own loaded context. Some things need a tool — an external call that returns data or performs an action the model can't produce natively. Most real work is a sequence of these routing decisions stacked on top of each other.

Without explicit attention management, a system picks one default and lives with the consequences:

- Always native. The LLM solves everything in-thread. Works until a problem lands that native capability can't actually solve — a computation that silently hallucinates, a data lookup that returns confabulated values, a multi-step reasoning chain that drifts off the rails with no verification layer. By the time the failure is visible, the output has already moved downstream.
- Always tool. Every step goes through an external call. Reliable for the things tools do well, brittle and slow for the things the LLM could have handled natively and cheaply. Latency piles up. Costs pile up. The agent becomes dependent on tool availability for trivial work.
- Manual routing. The user or the prompt dictates which path to take. Works for a known problem domain, doesn't scale to unknown ones, and puts the routing burden back on humans — which was most of what the agent was supposed to solve.

Attention management is the explicit, architected layer that makes these choices so the system doesn't have to default into one of the three failure modes.

## Why this matters: augmenting Markov-chain limits

An LLM is a Markov chain over tokens. Each output token is a conditional distribution over the prefix, and the prefix is bounded by the context window. That framing is reductive, but it is accurate about where the hard limits live: bounded state, no persistent side-channel memory, no computation outside the token-prediction loop, no feedback between outputs and the underlying weights. Everything an LLM does that looks like reasoning, memory, or tool-use is reasoning-*about*-tokens, memory-*written-into*-tokens, tool-use-*represented-as*-tokens.

External tools, skills, and structured memory are not replacements for that chain — they are augments to it. A vector-retrieval tool extends the effective context beyond the window. A computation tool gives the chain access to operations it cannot produce natively. A skeptic-membrane pass routes the chain's output through a secondary verification the chain itself cannot perform while generating. A two-tier memory structure lets the chain carry the facts it needs across sessions without exceeding its bounded state.

Attention management is what decides, in real time, when to invoke these augments. The value of explicit attention management, then, is not that it makes the LLM smarter. It is that it lets the architecture stretch the Markov chain's practical reach without pretending the limits aren't there.

Put it in human terms. Attention management is the difference between a student trying to memorize an entire textbook and a student who takes notes before the test. The notes aren't a replacement for understanding — they're an augment that lets the student hold more than fits in working memory. The pen and paper is the attention mechanism. The student with notes can point to the right section, cite the right example, and spend their working memory on the reasoning instead of the recall. The student trying to keep everything in their head runs out of capacity on the first hard question.

A Markov-chain LLM is the student without notes. External tools and structured memory are the notes. Attention management is the skill of knowing when to glance at the page and when to reason from what's already in working memory. Agents that try to "remember everything" fail the same way students do — not for lack of intelligence, but for lack of capacity. Agents that use external tools well work the same way prepared students do: they offload what they can, so they can think about what matters.

## The orthogonality restatement

In an earlier writeup I said structure is orthogonal to capability — the memory layer specifies how facts are organized, not what the agent does with them. That orthogonality is what creates the routing problem in the first place. If the architecture locked capability into each layer, there would be nothing to route. Because it doesn't — because every layer can be serviced by native LLM capability *or* a skill *or* a tool, depending on the situation — every step has a choice to make.

Attention management is how the architecture exercises that choice.

## What attention management is

It is a policy layer that sits above the primitives (memory, orchestration, reasoning, output) and decides, per step, which capability tier handles the work. That decision is informed by three things:

1. What the step actually demands. A lookup against a small, known catalog is different from a retrieval against a million-row corpus. A one-off reasoning task is different from one that has to be verifiable. A tentative draft is different from a final artifact.
2. What native capability is available at the model tier currently in use. Models shift over time. A step that needed a tool last year may be native this year. The policy has to be model-aware without being model-specific.
3. What the step costs and what it risks. Tools cost latency and often money. Skills cost context budget. Native reasoning costs nothing extra but carries the highest hallucination risk on problems the model isn't reliable on. The routing choice is a cost/latency/reliability trade-off every time.

It is *not* a hard-coded decision table. It is a small policy that encodes "under these conditions, prefer X." The specific heuristics matter less than the fact that routing decisions are made explicitly, recorded, and revisitable.

## Layer-by-layer routing

The same routing question lands differently at each layer of the system.

**Memory.** When the agent needs to recall something, does it scan the index natively, invoke a vector-retrieval tool, traverse a knowledge graph, or ask a skill that knows the memory layout? For a small catalog, native index-scanning is cheaper and more accurate than anything else — the model already knows what's there. For a thousand-entry catalog across multiple domains, vector retrieval becomes the dominant path. The routing decision is *catalog size and domain specificity*, not a capability check on the LLM.

**Orchestration.** When a task arrives that spans multiple sub-problems, does the agent decompose and reason about the whole thing in-thread, or does it dispatch sub-agents? In-thread is cheaper on context but riskier on long sequences; dispatch is expensive but parallelizable and isolatable. The routing decision is *sequence length and isolation requirement* — if a sub-problem needs a clean context or a specialist role, dispatch; otherwise continue in-thread.

**Reasoning.** When a step requires computation or external data, does the agent try to produce the answer natively, or does it call a tool? For anything numerical where wrong answers are silent, the tool is the only correct choice. For qualitative reasoning where the model's fluency is the value, native is right. The routing decision is *whether wrong answers are silent*. Silent wrongness kills systems; visible wrongness is recoverable.

**Output.** Before an autonomous output goes to an external destination — a message, a file write, an API call — does it get verified? By whom or what? The skeptic-membrane pattern handles this layer: a dedicated routing policy that decides which outputs pass through a verification tool or a secondary model pass, and which are trusted directly. The routing decision is *reversibility and external visibility* — the less reversible the action and the more external eyes on it, the higher the verification threshold.

Each layer has its own flavor of the routing question. The meta-pattern is the same: an explicit policy, not a default.

## The cost / latency / reliability triangle

Every routing decision trades across three dimensions.

- **Cost** — tokens, API fees, compute. Native handling is usually the cheapest unit; tools and skills add per-invocation overhead.
- **Latency** — wall-clock time. Native is fastest when the model can produce the answer in one pass; tools and skill-dispatch add round-trips.
- **Reliability** — the probability the output is correct. Tools and verified skills are the most reliable for the things they're built for; native is the most reliable for the things the model is genuinely good at and fragile for the rest.

A production attention policy doesn't try to optimize all three. It optimizes the right one for the step. A quick internal draft optimizes latency. A final artifact destined for a human optimizes reliability. A background consolidation pass optimizes cost. The policy recognizes which dimension dominates for the step and routes accordingly.

This is why attention management can't be a single global setting. It has to be contextual. The same agent, on the same task, makes different routing choices at different phases — exploratory, drafting, finalizing — because the dominant dimension changes.

## How this evolves with the model tier

A policy layer that routes based on native capability has to handle the fact that native capability changes. The model released this quarter can do things the model from two quarters ago couldn't, and the pattern has to absorb that without rewriting everything.

The working shape: the policy references capability classes, not model names. *"Does the current model reliably handle multi-step arithmetic?"* is a question the policy can re-evaluate. *"Is GPT-4-level reasoning sufficient here?"* is not — it locks the policy to a specific model. When a new model tier arrives, the policy gets re-calibrated against that model's capability profile. The rest of the architecture — memory, orchestration, tools, skills — doesn't move.

This is why structure-orthogonal-to-capability matters so much for attention management. If capability were fused into each layer, every model shift would be a rewrite. With the orthogonality preserved, a model shift is a policy recalibration.

## The meta-point

Attention management is the control plane for a production agent system. Memory gives the agent stable facts; orchestration gives it coordinated execution; tools give it capability beyond the model; skills give it focused expertise; verifiability gives it trust. None of those matter without the layer that decides, at every step, which combination is right for *this* problem *now*.

Most agent work today routes implicitly — whatever the prompt suggested, whatever the framework defaulted to. That produces fragile systems because the routing decisions are happening but they're invisible, unrevisitable, and unmodifiable. Making attention explicit is what turns a collection of patterns into a system that survives real use.

It is also what lets the system evolve. Capability shifts; tools change; skills get added; new primitives enter the architecture. If attention management is an explicit layer, any of those changes is a small edit. If it isn't, every change touches every pattern.

---

*Daniel Higuera — AES Research — 2026*

*Part of a series on agent architecture patterns. See also: [Two-tier memory for production agents](two-tier-memory.html). Upcoming: cross-project director agents, skeptic membranes, and UAT residual-context-gap harnesses.*
