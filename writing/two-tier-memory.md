# Two-tier memory for production agents: what chat systems don't tell you

*An architectural pattern for agents that need to remember across sessions without choking on their own context.*

---

## The failure case

An agent you talk to for an hour is a different problem than an agent you work with for months. Run a session long enough and the naive approaches — "stuff everything into the context window," "compress the conversation summary," "embed everything and retrieve" — all start to leak.

The specific failure mode I want to name is this: on session seven, the agent has forgotten that on session three you told it not to mock the database. On session twelve, it happily re-derives a convention it already saved a note about on session one. On session twenty, its conversation-summary compression has quietly dropped the constraint that made session four's decision correct, and the agent is now operating on a plausible-but-wrong model of your preferences.

You don't see it happen. You see the output. The output is fine until it isn't. By the time the drift is visible, the compression artifacts are load-bearing.

This is a memory problem, and memory systems built for chat don't solve it. This piece describes one that does.

---

## Why chat memory doesn't work

The default mental model for "agent memory" comes from chat. Chat memory is a scratchpad: everything said in this conversation. Close the tab, start fresh. Some systems layer on a lossy summary for continuity, some attach a vector-embedded retrieval layer, some pin a short "user preferences" block at the top.

These are fine for chat. They break for agents that do work because agents that do work accumulate claims. Claims about the user, claims about the project, corrections from prior sessions, confirmations of non-obvious choices. The claim volume grows monotonically while the value density doesn't. A 40-session history summarized into a scratchpad is either too short to carry the decisions that matter or too long to read on every turn. Vector retrieval fetches the wrong thing half the time because "retrieval relevance" is not the same as "claim validity."

The root issue: chat memory treats every utterance as homogeneous. Production agent memory needs to distinguish between *this is what I'm thinking about right now* and *this is a load-bearing fact I shouldn't have to rediscover.* Those are not the same data structure.

---

## The pattern: two tiers, semantic organization

Two files do the work that one file and a vector store can't:

1. **`MEMORY.md`** — an index. One line per memory. Always loaded into context.
2. **`memory/{topic}.md`** — one file per memory. Read on demand when the index entry looks relevant.

That's it. The novelty isn't in the data structures. It's in the separation between *recall* and *retrieval*.

The index is the agent's standing mental model of what it knows exists. It's small enough (one line each, under 200 characters) to always carry in context without paying for it. Every time the agent runs, it reads the index and knows: "There's a feedback note about database mocking. There's a user note about their role. There's a project note about the auth rewrite that's driven by compliance, not tech-debt cleanup."

The topic files are the actual content. The agent doesn't read them unless the index entry signals the content is relevant to the current task. That read is cheap because it's targeted and the file is small. If a topic file starts growing past a few hundred lines, that's a signal to split it, not to summarize it.

Two tiers, because one tier doesn't work and three tiers are expensive. A single memory file grows without bound. A tree of topic files without an index turns every recall into a directory walk. Two tiers buy you the entire economy — the index is O(entries) to scan, the topic files are O(1) to fetch when named. You pay context budget only on the index, and the index is engineered to stay small.

---

## Types of memory (and why they matter separately)

Not all claims are the same kind. Mixing them means writing bad prompts about how to use the memory. Separating them means the agent can calibrate its own behavior with one rule per kind.

I use four:

- **User memory** — facts about the user's role, goals, responsibilities, and knowledge. What the agent should know about who it's collaborating with. "User is a senior software engineer focused on observability."
- **Feedback memory** — guidance the user has given about how the agent should work. Both corrections and validated choices. "Integration tests must hit a real database, not mocks — prior incident where mock/prod divergence masked a broken migration." (That "Why:" line is load-bearing. More below.)
- **Project memory** — state about ongoing work, initiatives, bugs, incidents, decisions that aren't derivable from the code. "Auth middleware rewrite is compliance-driven, not tech-debt — scope decisions favor compliance over ergonomics."
- **Reference memory** — pointers to where information lives in external systems. "Pipeline bugs are tracked in Linear project 'INGEST'."

These aren't rigid types; they're a calibration device. The agent behaves differently around a feedback note (apply the rule, don't re-derive) than around a project note (this is volatile, verify before acting on it). The categorization IS the prompt.

What matters for the pattern to work:

- Every memory has a **why**. Not just the rule, the reason. "Don't mock the database in these tests" is a rule. "Because we got burned last quarter when mocked tests passed and the prod migration failed" is the rule plus the reason. With the reason, the agent can reason about edge cases. Without it, the rule ossifies and starts misfiring in situations it wasn't written for.
- Every memory is **one topic, not a journal**. The file is organized semantically, not chronologically. A topic file for the auth rewrite accumulates the stable shape of what's known about that rewrite — not a dated log of every mention.
- The index entry is **a hook, not a summary**. "Don't mock the database" in the index, not "In March 2024 the team decided to stop mocking the database after a migration failure caused by mock/prod divergence, details in topic file." The hook triggers the topic-file read when the agent is operating in adjacent territory.

---

## Failure modes this prevents

The pattern earned its structure from watching what fails without it.

**Context bloat.** The naive "append everything to a single file" approach grows without limit. After forty sessions, the memory file is either too long to always load (you start truncating) or too long to read when loaded (context budget vanishes before the task starts). The two-tier split caps the always-loaded footprint at the index size, and the index is engineered to stay under two hundred lines.

**Stale memory acting as current.** When memory grows without review, old facts accumulate alongside new ones, and the agent has no way to tell which is live. A two-tier system with per-topic files lets the agent (and you) treat staleness as the default and freshness as the exception — before acting on a recalled fact, the agent can verify it's still correct by reading the current state of the code or the resource the memory points to. This is a small behavioral rule ("trust observation over memory when they conflict") that pays for itself immediately.

**Duplicate writes.** Without an index, the agent writes new memories that already exist. After a few sessions, there are three slightly-different versions of the same preference, and the agent's behavior is nondeterministic depending on which it reads first. With an index, the pre-write step is "scan the index for an existing entry on this topic." Updates replace; new entries are rare.

**Contradictions.** The sibling of duplication. Memory A says "the user prefers terse responses." Memory B says "the user appreciates detailed explanations." Both are true in different contexts, but if the agent doesn't see them together, it applies one and not the other. The index makes contradictions surface-able — at write time, you can see the conflict and reconcile.

**Confidence drift.** Long-running agents accumulate unverified beliefs. If the memory system doesn't distinguish between "I wrote this down when the user told me" versus "I inferred this from context three sessions ago," confidence erodes silently. The "why" line in every feedback and project memory forces the provenance to be carried forward. If a belief has no why, it gets reviewed before it's acted on.

---

## Implementation recipe

The pattern is easy to implement because it's mostly a prompt-engineering convention and a file layout. Here's the shape.

**Directory:**

```
memory/
  MEMORY.md
  feedback_testing.md
  feedback_communication.md
  user_role.md
  project_auth_rewrite.md
  reference_linear.md
```

**`MEMORY.md` — the index.** One section per memory type. One line per entry. Each line is a markdown link to the topic file plus a one-line hook.

```markdown
# MEMORY.md

## Feedback
- [Database mocking rule](feedback_testing.md) — integration tests hit real DB; prior incident mock/prod divergence
- [Terse responses preferred](feedback_communication.md) — no trailing summaries; reason: user reads the diff

## Project
- [Auth middleware rewrite](project_auth_rewrite.md) — compliance-driven; favor compliance over ergonomics

## User
- [Senior eng role + observability focus](user_role.md) — frame explanations accordingly

## Reference
- [Pipeline bugs in Linear INGEST](reference_linear.md)
```

**Topic file format — frontmatter + body.**

```markdown
---
name: Database mocking rule
description: Integration tests must hit a real database, not mocks
type: feedback
---

Integration tests must hit a real database, not mocks.

**Why:** Prior incident (Q1 2024) where mocked tests passed but the production migration failed — mock/prod divergence masked a broken schema change.

**How to apply:** For any test that touches data (read, write, migration, RLS, etc.), wire it to a real test database. Acceptable: ephemeral per-run DB, pinned schema, deterministic seeds. Not acceptable: in-memory mocks, fake ORMs, test doubles that short-circuit SQL.
```

**When the agent writes a memory:**

1. Scan `MEMORY.md` for an existing entry on the topic. If present, update the topic file and (if needed) the index line.
2. If not present, pick the right type. Create `memory/{type}_{topic}.md` with frontmatter.
3. Add one line to `MEMORY.md` under the right section.
4. Stop. Do not embellish. The economy of the system depends on entries staying tight.

**When the agent reads a memory:**

1. The index is always loaded. Scan it.
2. If a hook looks relevant to the current task, read the topic file.
3. Trust observation over memory when they conflict. If the memory points to a file path or a function name, verify it still exists before citing it.

**When the agent should not use a memory:**

- If the user explicitly tells it to ignore or not use memory for a given task.
- If the memory is about external state (activity, recent changes) and the current moment is asking about *current* state — prefer running the live query over recalling the snapshot.
- If the memory is summary-level and the user's question is about specifics that weren't in the summary.

---

## What pairs with it

The two-tier split is one primitive. A production agent system runs on a composition of primitives, and this section names the pairings I've used in practice — without claiming the base pattern does work it doesn't, and without pretending the pairings don't exist.

**Semantic retrieval at scale.** The index is scanned, not embedded. For most agent-memory catalogs — under a hundred entries per project — LLM scanning of a tight index is cheaper and higher-quality than vector search: the model already knows what's there, it just needs to recognize relevance. At larger scale (thousands of entries spanning multiple domains), a vector layer plugs in as a complementary retrieval path: the vector store returns candidate topic files, the index still carries the canonical *is-this-live* signal. The composition is vector-for-recall, index-for-arbitration. The base pattern doesn't need the vector layer until the catalog demands it; when it does, the layer attaches without restructuring the memory format.

**Cross-session task state.** Memory is for load-bearing facts. Work-in-progress state — partially-completed tasks, open threads, pending decisions — lives in a separate file structure: a `STATE.md` per project, a shared `TASKS.md` for the workspace, checkpointed plan artifacts for active work. The two structures coexist cleanly. Memory carries the stable shape of what's *known*; state files carry the transient shape of what's *happening*. Mixing them is how chat scratchpads metastasize into every other data structure. Keeping them separate is how a long-running agent accumulates institutional knowledge without accumulating stale work-in-progress. In a production system you want both — they pair; they don't overlap.

**Staleness detection.** Fully automatic staleness is hard because the universe changes faster than any timestamp can track — "this memory is still true" usually requires running the relevant verification in the current moment. The pragmatic pairing is a periodic reconciliation pass: a lightweight routine (human-triggered at phase boundaries, or scheduled) that walks the index, flags entries referencing removed code or dead resources, merges duplicates, prunes obsolete facts, and updates or deletes as needed. The routine doesn't need to be smart; it needs to run on a cadence. I run this at phase boundaries on my own work, and the index is engineered for fast scanning so the pass stays cheap.

**Multi-agent memory sharing.** The pattern extends cleanly to an agent hierarchy. A director agent holds a workspace-level memory with the cross-project index; each sub-agent holds its own project-level memory keyed to its scope; the director hands down relevant context on dispatch and receives back update proposals from sub-agents that touched shared entries. The file-scope convention determines who reads what without requiring inter-agent locking or complex synchronization. This is the structure I run across a dozen AI-native projects under a unified agentic architecture — one workspace memory, many project memories, consistent index semantics throughout. The base pattern is single-agent-single-project; the extension to hierarchy is mechanical once the scope convention is set.

---

## Structure is orthogonal to skills and tools

The two-tier split is one instance of a more general property the larger architecture depends on: **structure is orthogonal to capability**. The memory layer specifies how facts are organized. It says nothing about what the agent can *do* with them. At any layer of a production agent system — memory, orchestration, reasoning, output — skills and tools can be plugged in to augment or surpass what the LLM does natively.

This matters because LLM native limitations move. The model that can't do X today may do X fluently in six months, but it also may not, and you shouldn't have to rearchitect around either outcome. A layered architecture where skills and tools slot in at any level lets the system stay correct regardless of which capabilities the LLM carries natively on any given day.

Applied to memory: the two-tier pattern is indifferent to whether recall happens by the LLM scanning the index, by a vector-search tool, by a knowledge-graph traversal, or by a future LLM with the entire index in its context window. The structure is the same; the capability layer is swapped. The same principle applies to orchestration — role-tagged addressing works whether sub-agents are LLM calls, fine-tuned specialists, or hand-coded deterministic tools — and to every other layer of the system.

That orthogonality is deliberate. It's what lets a production agent system survive the next capability shift without a rewrite, and it's why the patterns composed here hold up even as the model tier underneath changes out from under them.

## The meta-point

Memory for agents is infrastructure, not a feature. The moment you treat it as a feature — "the agent has memory now" — you've smuggled in assumptions about what memory is for, and those assumptions are usually about chat.

Production agent memory is a protocol: write under this schema, read under this rule, reconcile under this convention. The two-tier split is the cheapest protocol that holds up across sessions without leaking. It's not the only one. It's the one I've run across a dozen AI-native projects — cross-project director agents, investment research platforms, ML production pipelines — and it has never been the thing that broke. The things that break are above and below: task management, tool-use reliability, outbound-communication safety. Memory, once the two-tier discipline is in place, becomes load-bearing infrastructure you stop thinking about.

Which is the right outcome. The infrastructure you stop thinking about is the infrastructure that's working.

---

*Daniel Higuera — AES Research — 2026*

*Part of a series on agent architecture patterns. Upcoming: cross-project director agents, skeptic membranes, and the UAT residual-context-gap.*
