---
name: aes-pattern-map
description: Given a concrete agent-system task or design problem, identify which AES Research architectural patterns apply and how they compose. Returns a short map — which pattern, applied where, in what order. Use at the architecture-design phase of a project, or when explaining an existing system to someone who hasn't seen it.
---

# Pattern map

## When to use

Invoke when the question is **architectural**, not tactical:

- "How should I structure memory for this agent?"
- "What pairs with a skeptic membrane in a production system?"
- "Which AES Research pattern solves X?"
- "Explain this agent design in terms of the AES Research body of work."

Do not invoke for narrow tactical questions that one other skill already handles (`aes-skeptic-membrane`, `aes-two-tier-memory`, `aes-attention-routing`). This skill is about *composition*, not individual layer decisions.

## The AES Research primitive set

The skill operates on these architectural primitives. Each pairs with others; the map shows *which* and *how*.

1. **Two-tier memory** — index + topic files. Handles persistence of load-bearing facts across sessions.
2. **Cross-project director agent** — role-tagged addressing, role-boundary self-monitoring, coordinated sub-agent dispatch. Handles multi-project coordination and isolation.
3. **UAT harness** — surfaces residual context gap. Handles the specific failure mode where tests pass because of carry-forward context but would fail on a cold run.
4. **Skeptic membrane** — output-boundary verification. Handles silent wrongness and prompt injection at the output layer.
5. **Attention routing** — native / tool-augmented / skill-dispatch / sub-agent decisions per step. Handles the cost/latency/reliability trade-off.
6. **Atomic memory writes** — temp-file-then-move discipline. Handles corruption risk during compaction.
7. **Sub-agent response discipline** — ten tokens instead of book reports. Handles battery life on long-running sessions.

## How to use

Given a `question` or `task_description`, produce:

1. **Primary pattern** — which one is most load-bearing for the task
2. **Paired patterns** — 1-3 that compose with it
3. **Composition** — one sentence on how they work together
4. **Writeup pointers** — which AES Research writeups explain each in depth

## Output format

```
<pattern_map
  primary="<pattern name>"
  paired="<pattern 1>, <pattern 2>"
  composition="<one sentence>"
  references="<urls or writeup titles>"
/>
```

## Composition rules

- **Memory pairs with context survival.** Two-tier memory is *what* to keep; atomic writes + compaction discipline are *when* and *how*.
- **Output layers stack.** Attention routing decides *where* a step runs; the skeptic membrane decides *whether* the output crosses the boundary.
- **Multi-agent systems need hierarchy + scope.** Director agent + two-tier memory per scope + attention routing across scopes.
- **Every primitive is orthogonal to capability.** The pattern doesn't dictate whether the LLM, a tool, or a skill implements the step — only the shape of the decision.

## Why this pattern matters

Most agent architectures are presented as recipes — "use pattern X." The AES Research approach is that each pattern is a *primitive*, and the value is in composition. The map skill exists so that a user asking "which pattern?" gets "here's the composition" instead of a single-pattern recommendation that misses the architectural shape.

## Related

- [Two-tier memory](https://aesresearch.ai/writing/two-tier-memory.html)
- [Context window as battery](https://aesresearch.ai/writing/context-window-battery.html)
- [Attention management](https://aesresearch.ai/writing/attention-management.html)
- All three other `aes-*` skills
