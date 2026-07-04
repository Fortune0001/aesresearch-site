# Metered Knowledge Extraction at Scale — Efficiency Metrics from a Composable Research Pipeline

**2026-06-06 · Actual spend: $0 (covered by a platform subscription); all dollar figures below are API-equivalents.**

## The task

Turn a large, heterogeneous corpus of expert material — long-form technical YouTube (15-minute tutorials to 3-hour research interviews) plus the live web-practitioner literature — into a **structured, cited, timestamp-anchored, queryable research warehouse**. Done by hand this is hundreds of hours of watching, note-taking, and structuring. The question this run answers: *what does it cost when an agent system does it, and what is the actual binding constraint?*

## The system (the argument is compositional)

No single model call does the work. Four primitives compose:

1. **A decomposition contract (skill).** One schema for "what a faithful extraction is" — frontmatter + thesis + timestamp-anchored claims/frameworks + named tools/numbers + caveats. The same contract applies to a video transcript, a web article, or a paper, so the *output* is uniform regardless of source.
2. **A lean parallel dispatch substrate (tool).** Stateless extraction agents launched as parallel subprocesses with the per-task content in the user message and an **identical system preamble across agents** — so agents share a prompt-cache key. Server integrations and auto-loaded configuration are stripped, cutting preamble tokens. Each agent reads its source, writes one warehouse entry, and reports cost and tokens.
3. **A warehouse schema (architecture).** Frontmatter-validated entries, per-channel and per-category indexes, cross-source syntheses. Knowledge is addressable, not a pile of transcripts.
4. **Cache-aware context design.** Because the preamble is stable and the volatile content sits at the tail, the prompt cache absorbs most of every call. Measured cache-hit share below.

Cheap front-half steps (enumerate → filter → fetch auto-subtitles → clean) are deterministic scripts; only the extraction itself spends model tokens. The expensive primitive is invoked exactly where it adds value.

## The run (measured)

A single instrumented batch decomposed **244 expert videos across three channels**, each into a full cited warehouse entry, in ~2 hours of wall-clock:

| Channel | Videos | Cost (API-equiv) | $/video | Cache-hit (preamble) | Wall |
|---|---|---|---|---|---|
| Channel A (tooling/agents, ~16-min avg) | 118 | $20.39 | $0.17 | 73.8% | 49 min |
| Channel B (research interviews, 1–3 hr) | 55 | $20.41 | $0.37 | **85.3%** | 43 min |
| Channel C (agent/founder, ~25-min avg) | 71 | $12.47 | $0.18 | 69.5% | 35 min |
| **Total** | **244** | **$53.27** | **$0.22 avg** | **~78%** | **~2 hr (concurrency K=5)** |

Token aggregate: ~27.6M cache-read + ~7.4M cache-create + ~1.14M output. **The cache carried ~78% of all input** — the long-form interview channel, with the biggest transcripts, had the *highest* cache hit (85.3%) because the stable preamble amortized hardest there.

Unit economics: **~$0.22 per fully-structured expert-video extraction, $0 actual** (subscription). The same session also produced two web-sourced practitioner syntheses (context engineering; agent evaluation — 12 facet investigations + adversarial coherence audit + deep-dives + synthesis each) and an earlier 75-video channel drain, for a session total of **~319 video decompositions + 2 multi-stage syntheses** at **~8% of one week's subscription quota**.

## The finding: the ceiling is throughput, not cost or context

The batch stopped not because it ran out of budget and not because any context window filled — it stopped because it hit the **platform's 5-hour rolling rate limit** after ~244 calls. At $0.22/video the *budget* wall is hundreds of videos away; the *context* wall never appears (each extraction is independent and bounded); the wall you actually hit is **rate**.

That reframes scaling. The lever isn't a bigger context window or a cheaper model — it's **pacing the same composable pipeline across rate windows** (lower concurrency + spread over time, or schedule across windows). The architecture is already context-unbounded and cost-trivial; the remaining engineering is throughput choreography, which is a scheduling problem, not a model problem.

## Why this is the interesting result

The expensive, hard-to-scale part of research — faithful structured extraction from long, messy expert sources — turns out to be the *cheap, embarrassingly-parallel* part once the contract + dispatch + schema + caching compose. The work that remains scarce is **taste** (which sources, which syntheses matter) and **rate budget** (how fast the platform lets you go). Everything in between is a metered, resumable batch at ~$0.22/source and $0 marginal cost.

---

*All figures come directly from the run's per-batch cost and token telemetry, measured on the day of the run.*
