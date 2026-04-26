# Skills

*Reusable Claude Code skills that encode the patterns from the writing as loadable instructions.*

Four skills authored for direct use by a Claude Code session with this repo cloned. Each encodes a decision rule from production — not as prose guidance but as executable instructions the model loads and runs.

These are independent artifacts, free to use, fork, and adapt. They're also a substrate. The architectural thinking that makes them effective in production lives in [the writing](writing/index.html) — they compose under that thinking. Loaded in isolation they produce partial behavior; the calibration comes from the composition. Treat them as building blocks, not finished systems.

---

## `aes-skeptic-membrane`

Vet an autonomous agent output before it crosses the boundary — file write, API call, message send.

**What it does:** runs a two-layer check on any outbound artifact: first a surface scan for obvious violations, then a read-as-skeptic pass that applies the same scrutiny a well-calibrated human reviewer would. Flags borderline outputs for explicit user decision rather than silently passing or silently blocking.

**When to use:** at the boundary between an autonomous agent and any external destination. Mandatory before any output that cannot be recalled — sent emails, published posts, committed files, API mutations.

[View on GitHub →](https://github.com/Fortune0001/aesresearch-site/blob/main/.claude/skills/aes-skeptic-membrane/SKILL.md)

---

## `aes-two-tier-memory`

Scan an index and topic files, then decide which entries to load into context for the current task.

**What it does:** implements the two-tier memory pattern described in the [writing](writing/two-tier-memory.html). Reads the MEMORY.md index first, selects only the entries relevant to the current task, then loads the referenced topic files — keeping context load proportional to what the task actually needs.

**When to use:** when the agent has a memory store available and the full store would exceed a useful context fraction. Prevents the context-bloat failure mode that accumulates across long-running sessions.

[View on GitHub →](https://github.com/Fortune0001/aesresearch-site/blob/main/.claude/skills/aes-two-tier-memory/SKILL.md)

---

## `aes-attention-routing`

Route a unit of work to the right execution tier: native model capability, tool call, loaded skill, or sub-agent dispatch.

**What it does:** makes the routing decision explicit before each non-trivial step. Evaluates the work unit against four tiers and selects the one with the best accuracy/cost/latency tradeoff for that specific step. The decision and its rationale are surfaced, not implicit.

**When to use:** before any step where the routing choice is non-obvious — particularly in multi-agent or multi-tool systems where the wrong tier costs context, money, or latency without surfacing the error.

[View on GitHub →](https://github.com/Fortune0001/aesresearch-site/blob/main/.claude/skills/aes-attention-routing/SKILL.md)

---

## `aes-pattern-map`

Given an architecture question, identify which patterns compose to address it and how they relate.

**What it does:** takes a concrete agent-system task or design question and maps it against the pattern library — skeptic membrane, two-tier memory, attention routing, director-agent topology, residual context gap detection. Returns the relevant composition and flags any ordering dependencies.

**When to use:** at the architecture-design phase of a new agent system, or when explaining an existing one. Useful both as a design tool and as a communication tool when the audience needs to understand why the system is structured the way it is.

[View on GitHub →](https://github.com/Fortune0001/aesresearch-site/blob/main/.claude/skills/aes-pattern-map/SKILL.md)

