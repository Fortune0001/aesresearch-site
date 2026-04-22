---
name: aes-two-tier-memory
description: Scan a two-tier memory (MEMORY.md index + per-topic files) and decide which entries to load for the current task. Returns the loaded set and the reason each was selected or skipped. Use when the agent has a memory directory available and needs to decide what to pull into context.
---

# Two-tier memory scan

## When to use

Invoke at the **start of a session** or **when the task shifts** to a topic the agent hasn't been reasoning about. The goal is to populate the agent's working context with load-bearing facts from persistent memory without dragging in every entry.

## How to use

Given:
- A path to a `MEMORY.md` index file
- A path to a `memory/` directory of per-topic files
- The current `task` (one-sentence description)

Produce a **load plan**:

1. Read `MEMORY.md` (always). It's the index — short, one line per entry.
2. For each index entry, decide if it is relevant to the task:
   - Entry is about the user's role / preferences AND the task involves the user → relevant
   - Entry is about a project AND the task touches that project → relevant
   - Entry is a feedback/correction AND the topic overlaps → relevant
   - Entry is a reference pointer AND the task needs the external resource → relevant
   - Otherwise → skip
3. Read only the topic files for relevant entries.
4. Return the load plan: which entries loaded, which skipped, one-line reason each.

## Rules

- **Prefer skipping over loading.** Every loaded entry costs context. If you wouldn't cite it, don't load it.
- **Respect the "why" in each entry.** A feedback entry's reason tells you when it applies and when it doesn't — use the reason, not just the rule.
- **Trust observation over memory.** If a memory entry references code paths or state that the current codebase contradicts, flag the stale memory entry rather than acting on it.

## Output format

```
<memory loaded="N/M" entries="slug_a, slug_b" skipped="slug_c, slug_d"
        note="<one-sentence summary of why these were relevant>" />
```

Where `N` is loaded count and `M` is total entries in the index.

## Why this pattern matters

Memory systems that grow without gates turn into context bloat. A two-tier split — index always loaded, topic files loaded on demand — caps the always-carried cost at the index size while keeping the archive available. The skill is the policy that decides which topic files cross into context each turn.

## Related

- [Two-tier memory for production agents](https://aesresearch.ai/writing/two-tier-memory.html) — full deep-dive on the pattern
- [The context window is a battery](https://aesresearch.ai/writing/context-window-battery.html) — why loading discipline matters during compaction
- `aes-skeptic-membrane` skill — vets outputs that cite loaded memory
