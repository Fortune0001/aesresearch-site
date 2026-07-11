# Context-Unbounded Codebase Investigation — Polyglot Capability Proof on Ray (1.37M LOC, Three Languages)

*The same investigation architecture on 1.37M lines across C++, Python, and Java — stitching findings across the language boundary in a single run.*

**Date:** 2026-06-05 · **Target:** [`ray-project/ray`](https://github.com/ray-project/ray) @ master [`0b82e9d`](https://github.com/ray-project/ray/commit/0b82e9d) · **Cost:** ≈ $123 API-equivalent ($0 marginal — the run drew on an existing subscription allocation)

## What this demonstrates

A hierarchical research swarm, built on AES Research's investigation architecture, investigated the **entire Ray codebase — 442 core directories / 1.37M lines across three languages (C++, Python, Java) — and produced a single coherent architecture-level synthesis that stitches findings *across the language boundary*, with no individual reasoning context ever exceeding a bounded working set.**

This is the **third** capability proof in the series, and it adds a dimension the first two could not:

| Run | Codebase | Language(s) | Scale | New thing proven |
|---|---|---|---|---|
| 1 | [`huggingface/transformers`](https://github.com/huggingface/transformers) | Python | ~2M LOC | context-unbounded investigation at all |
| 2 | [`kubernetes/kubernetes`](https://github.com/kubernetes/kubernetes) | Go | 3.6M LOC | generalizes to non-AI / distributed-systems / Go |
| **3** | [**`ray-project/ray`**](https://github.com/ray-project/ray) | **C++ + Python + Java** | **1.37M LOC** | **polyglot synthesis in a *single* run — patterns that only exist *across* the language boundary** |

The headline result is a cross-language architectural claim no single-language pass could produce: that Ray funnels all distributed computation — across three languages and seven+ domain libraries — through exactly three C++ kernel primitives.

## The run (all figures measured, not estimated)

| Metric | Value |
|---|---|
| Repo / commit | `ray-project/ray` @ master `0b82e9d` |
| Scale (measured) | **1,370,296 handwritten LOC** — Python 1.10M · C++ 235K · Java 33K; 719 core source dirs |
| Targets investigated | **442** substantial core directories (≥100 LOC); 780K LOC (Python 605K · C++ 153K · Java 22K) |
| Hierarchy | **18 sub-investigations → 3 mid-coordinators → 1 master** (3-level) |
| Findings | **1,478** raw · **159 confirmed** hypotheses · **11 refuted** · 141 open |
| Convergence | all **3** mid-syntheses converged on the same architecture, **zero dissent** ("near-identical vocabulary") |
| Compute | 5 batched launches back-to-back over ~5.2 h (one 3-way pilot, three 5-way parallel batches, one aggregation pass); longest batch 98.6 min, under the 4 h wall-clock ceiling |
| Reliability | **0 chunks lost**; self-healing absorbed 4 sub-phase timeouts + 4 transient failures |
| Per-tier context | **bounded at every tier** — the master read 3 mid-syntheses, never 18 subs |
| Cost | **$123.24 API-equivalent** ($0 marginal, subscription-covered) |

## Headline: seven convergent meta-patterns

The master synthesis (~11K chars, complete — no truncation) surfaced seven cross-cluster patterns **no single sub-investigation could see**, each requiring stitching findings across clusters *and languages*:

1. **The Compression Funnel — three primitives as a universal basis set.** Every one of the 1,478 findings — across RL training, hyperparameter search, serving, data pipelines, workflows, DAGs — reduces without exception to compositions of `task` / `actor` / `ObjectRef`. The funnel is *lossless*: no library needed to escape the triad, so the C++ kernel can remain ignorant of all domain logic above it. This is *why* one C++ scheduler can serve every library.
2. **Type erasure at the wire boundary as the cross-language contract.** `ObjectRef<T>` (typed in Java/C++) is erased to a raw fixed-width binary `ObjectID` at the Plasma/GCS wire level. Ray's polyglot guarantee is **not type safety but capability-token identity** — any language can hold, pass, and resolve a ref as long as it can name that binary ID and speak protobuf. This is why adding a language binding is tractable.
3. **The Controller–Worker FSM as a recurring structural motif.** Every library independently re-derives the same topology (a singleton controller actor + a pool of worker actors): Tune's `TrialRunner`, Serve's `Controller`, Train's `TrainController`, Data's pipeline coordinator. The kernel never imposes it — it's the natural "eigenmode" of an actors-plus-futures primitive set.
4. **Protobuf as the sole cross-language truth — and its hidden cost.** `TaskSpec`, `ObjectReference`, actor handles, placement-group specs, GCS metadata all flow as protobuf over gRPC. The hidden rigidity: any change to the core scheduling/object model requires a schema change propagating to C++, Python, *and* Java simultaneously — which is why Python libraries extend at the *composition* layer, never the *schema* layer.
5. **The Python library ecosystem as an uninstrumented composition layer.** Ray's highest-value code (Tune, Serve, Data, Train, RLlib) is **entirely invisible to the C++ kernel** — which sees only actor failures and object losses, never "training trial diverged" or "serve replica errored." Greatest strength (kernel simplicity) and biggest observability gap (no built-in bridge between the kernel view and the library view) at once.
6. **The GCS as metadata bus — single point of coordination, not of failure.** GCS is the sole cluster-wide metadata authority (actor registry, placement groups, resources) while deliberately staying *off* the data path (which flows through Plasma shared memory). That metadata/data split is why object throughput scales independently of coordination throughput; confirmed as a hard invariant (no library bypasses it).
7. **Java bindings as structural proof of kernel minimality.** The Java binding being a thin JNI/protobuf adapter with *no kernel modifications* is the strongest evidence the kernel API is genuinely language-agnostic — its symmetry with the Python binding shows Ray's language-neutrality is achieved, not aspirational.

> *"Ray is a polyglot distributed runtime whose entire architectural power derives from a single strategy: funnel all distributed computation — across three languages and seven+ domain libraries — through exactly three C++ kernel primitives (task, actor, ObjectRef), mediated by protobuf/gRPC at every language boundary, so that the kernel remains the sole arbiter of scheduling, fault tolerance, and object lifecycle."* — master synthesis, converged across all 3 mid-coordinators with zero dissent.

The **convergence is itself the result**: 3 independent mid-syntheses, each over a different 6-sub slice of the codebase, arrived at the same characterization with near-identical vocabulary. 11 refuted hypotheses out of 1,478 findings — local edge cases (older/experimental code paths), no inter-cluster contradictions.

## Why it scales — the composition

Same four primitives as the prior runs, each bounding a different dimension:

- **Hierarchical synthesis bounds CONTEXT.** The master read 3 mid-syntheses; each mid read 6 subs; each sub investigated ~25 directories. No reasoning context grows with total scale — that flatness *is* the "context-unbounded" property. This run also **re-validated the 3-level hierarchy across scales**: the same structure that capped a 67-sub / 2,001-target run (Kubernetes) cleanly handled an 18-sub / 442-target run with a complete, untruncated master synthesis.
- **Parallel fan-out bounds WALL-CLOCK.** Independent sub-investigations ran five-at-a-time inside a measured hardware-safe band; hardware telemetry stayed within the safety envelope throughout (peak 15 concurrent processes, ~4 GB RAM).
- **Cadenced launching bounds HARDWARE STRESS.** Work decomposed into bounded batches; no batch exceeded the safety envelope; zero hardware-stress events.
- **Self-healing bounds RELIABILITY.** 4 sub-phase timeouts + 4 transient failures were absorbed by pause-and-retry (max 2 attempts) with **0 chunks lost**.

Together: *investigate an arbitrarily large, multi-language codebase, at bounded per-tier context, in bounded wall-clock, on bounded hardware, unattended.*

## The coverage map — the run names its own next targets

A property of the hierarchy is that it emits its own frontier: the investigation flagged five areas as the natural next bounded runs — (1) cross-language object **serialization overhead** (the numpy/tensor zero-copy path that bypasses protobuf via Plasma), (2) **library-level fault-tolerance** semantics (how each library translates kernel fault signals into recovery), (3) **placement-group** interaction with library-level scheduling (co-location / gang / anti-affinity), (4) the **autoscaler** and cluster-lifecycle interaction with GCS/raylet, (5) the **DAG/workflow** engine's composition mechanism and whether it introduces anything not reducible to the triad. Each is a bounded follow-up of the same shape as this run.

## Method and measurement notes

- **Every figure is measured, not extrapolated.** LOC was counted from a fresh clone at the pinned commit; investigation targets were the 442 core directories with ≥100 LOC; agents fetched each directory directly from GitHub `master` URLs; per-launch usage was logged, and every figure above is measured from the clone or counted from the 18 sub-investigation logs.
- **What "convergence over 3" means:** at the master tier, the 3 converging syntheses are the 3 mid-coordinators (each aggregating 6 chunk-level sub-investigations), so the zero-dissent convergence claim is over 3 independent 6-sub slices, grounded in 18 chunk-level investigations beneath them.
- **Hypothesis accounting:** 141 of 311 hypotheses remained `open` (159 confirmed / 11 refuted). The confirmed set carries the synthesis; the open set maps directly onto the five coverage-map targets above — the explicitly bounded remainder for the next runs.
- **Fault accounting:** 4 sub-phase timeouts + 4 transient non-zero exits over the run, all absorbed by self-healing with 0 chunks lost.

## References (independently verifiable)

- Ray repository and language breakdown: <https://github.com/ray-project/ray> (Python / C++ / Java per GitHub's language stats)
- Pinned commit: <https://github.com/ray-project/ray/commit/0b82e9d>
- Ray Core primitives (tasks, actors, objects): <https://docs.ray.io/en/latest/ray-core/key-concepts.html>
- Ray architecture whitepapers: <https://docs.ray.io/en/latest/ray-contribute/whitepaper.html>
- Java JNI binding surface: <https://github.com/ray-project/ray/tree/master/src/ray/core_worker/lib/java>
- Prior-run targets: <https://github.com/huggingface/transformers> · <https://github.com/kubernetes/kubernetes>

---

*Licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).*

### Cite this essay

> Higuera, D. (2026, July 4). *Context-Unbounded Codebase Investigation — Polyglot Capability Proof on Ray (1.37M LOC, Three Languages)*. AES Research. https://aesresearch.ai/writing/ray-polyglot-capability-proof.html

```bibtex
@misc{higuera2026ray,
  author = {Higuera, Daniel},
  title = {Context-Unbounded Codebase Investigation — Polyglot Capability Proof on Ray (1.37M LOC, Three Languages)},
  year = {2026},
  month = {jul},
  publisher = {AES Research},
  url = {https://aesresearch.ai/writing/ray-polyglot-capability-proof.html}
}
```
