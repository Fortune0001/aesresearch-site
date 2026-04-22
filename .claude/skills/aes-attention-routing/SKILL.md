---
name: aes-attention-routing
description: Decide where a unit of work should run — native LLM reasoning, an external tool, a specialized skill, or a sub-agent dispatch. Returns the routing choice plus a one-sentence reason grounded in the cost/latency/reliability trade-off. Use before each non-trivial step to make the routing decision explicit rather than implicit.
---

# Attention routing

## When to use

Invoke at the **top of each non-trivial step** the agent is about to take. The skill exists because every step has a routing choice, and unrouted steps default to native LLM reasoning regardless of whether that's the right tier.

## How to use

Given:
- A `task_step` — one-sentence description of the work to do next
- Optionally, a `context` — what's already loaded / what constraints apply

Produce a routing decision from these four:

- **native** — Claude handles this directly in-context. Cheap, low-latency, highest hallucination risk for factual or numerical work.
- **tool-augmented** — Claude calls an external tool (web fetch, calculator, code execution, API). Higher cost/latency, much higher reliability for things the model can't reliably produce.
- **skill-dispatch** — Claude invokes a focused skill (like `aes-skeptic-membrane`) that encodes a calibrated procedure. Appropriate when the step has a repeatable shape.
- **sub-agent** — Claude dispatches a fresh sub-agent session with its own context. Appropriate for long-horizon or isolation-required work.

## Decision rules

1. If wrong answers would be **silent** (numerical, factual, operational) → `tool-augmented`. Never let Claude produce silent-wrong.
2. If the step **has a repeatable shape** we've encoded as a skill → `skill-dispatch`. Use the skill; don't re-derive each time.
3. If the step requires **isolation or parallelism** (independent research paths, separate context budget) → `sub-agent`.
4. Otherwise → `native`.

## The cost/latency/reliability triangle

The right route isn't the one that wins all three — it's the one that wins the dimension that dominates for THIS step.

- Quick internal draft → optimize latency → prefer `native`
- Final artifact going to a human → optimize reliability → prefer `tool-augmented` or `skill-dispatch`
- Background consolidation pass → optimize cost → `native` or `sub-agent` batching

## Output format

```
<attention route="native|tool-augmented|skill-dispatch|sub-agent"
           reason="<one sentence on why this route fits the step>" />
```

## Why this pattern matters

Most agent work routes implicitly — whatever the framework defaulted to. Implicit routing produces fragile systems because the decisions are invisible, unrevisitable, unmodifiable. Making attention explicit is what turns a collection of primitives into a working whole.

## Related

- [Attention management](https://aesresearch.ai/writing/attention-management.html) — full deep-dive
- `aes-skeptic-membrane` skill — the output-layer instance of the same policy
- `aes-two-tier-memory` skill — the memory-layer instance
