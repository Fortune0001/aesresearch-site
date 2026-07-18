# Context-unbounded codebase investigation: one method, three codebases, three languages

*A multi-agent architecture investigated huggingface/transformers, kubernetes/kubernetes, and ray-project/ray — ~6.9M lines across Python, Go, C++, and Java — and produced a coherent architecture-level synthesis of each, with no single model context ever holding more than a bounded working set. This is the method paper for the three runs.*

---

## The claim, and why it needs three proofs

Most LLM-based code analysis is bounded by the model's context window: the working memory of a single session is fixed, so the size of what you can understand appears fixed too. The architecture demonstrated here makes the opposite claim: **investigation scope can be unbounded, because no reasoning context ever needs to hold the whole target.** Scope lives in the orchestration structure; the window only ever holds one bounded chunk.

A claim like that is cheap to state and easy to fake at small scale, which is why it took three runs to earn it:

| Run | Codebase | Language(s) | Scale (measured) | What it proves |
|---|---|---|---|---|
| 1 | `huggingface/transformers` | Python | ~2M-LOC repo; ~962K LOC analyzed across 450 model families | The capability exists at all |
| 2 | `kubernetes/kubernetes` | Go | 3.6M-LOC repo; ~2.38M LOC investigated across 2,001 packages | Generalizes across domain — non-AI, distributed-systems, a different language |
| 3 | `ray-project/ray` | C++ / Python / Java | 1.37M-line repo; 780K analyzed across 442 core directories | Generalizes across *languages in a single run* — synthesis that stitches findings across the language boundary |

Three codebases, four languages, ~2,893 investigated targets, **100 sub-investigations**, 9,484 raw findings, 770 confirmed hypotheses — and, run end to end on one local workstation, unattended, for a combined **~$795 API-equivalent ($0 out of pocket, subscription-covered), with zero lost work units across all three runs.**

The rest of this piece is how, and what the runs measured about their own method along the way.

---

## The composition

Four primitives compose into the capability. Each bounds a different dimension, and the argument is the composition, not any single piece.

**Hierarchical synthesis bounds context.** The target is partitioned into independent sub-investigations, each running a complete map → hypothesize → confirm → synthesize loop inside a working set of roughly one chunk (~64K LOC in run 1). Sub-syntheses feed coordinators; coordinators feed a master. At every tier, the fan-in is capped — the master reads a dozen mid-syntheses, never a hundred raw investigations. That flatness *is* the context-unbounded property: adding scope adds chunks, not context.

**Parallel fan-out bounds wall-clock.** Independent subs run concurrently inside a measured hardware-safe band (run 3 peaked at 15 concurrent processes and ~4 GB RAM without leaving the envelope). Total time tracks the depth of the hierarchy, not the breadth of the target.

**Cadenced execution bounds hardware stress.** Work decomposes into scheduled, time-capped executions — 90-minute caps in run 1, ~74-minute caps in run 2, a 4-hour batch ceiling in run 3. No single execution can exceed the machine's safety envelope, so a 14-day investigation is as safe as a 14-minute one.

**Self-healing bounds reliability.** Timeouts, budget-cap hits, and transient failures pause and retry rather than losing work. Run 2 absorbed 10 timeouts and 5 budget-cap hits — and crossed a provider quota-reset boundary unattended — with zero chunks lost. Run 3 absorbed 8 more. The reliability claim is exercised, not assumed.

Together: *investigate an arbitrarily large codebase, at bounded per-tier context, in bounded wall-clock, on bounded hardware, unattended.*

---

## The spine: how the hierarchy earned its third level

The most useful result in the series is not any single synthesis. It is a scaling measurement the method produced about itself.

**Run 1 found the ceiling.** Transformers ran as a two-level hierarchy: 15 sub-investigations feeding one master directly. It completed — but the cross-investigation briefing, at 15 sub-syntheses of ~1.5K characters each, hit a soft size cap and clipped the tail of the final pattern. That was the first *measured* datapoint for a limit that had previously only been projected: a two-level hierarchy's master brief grows linearly with sub-count, and saturates around 15 subs.

**Run 2 removed it.** Kubernetes required 67 sub-investigations — far past the measured ceiling — so the hierarchy grew a middle tier: 67 subs → 12 mid-coordinators → 1 master. Fan-in stayed bounded at every level (the master read 12 mids; each mid read ~6 subs; each sub investigated ~30 packages). Targets grew 4.4× over run 1; the master's brief did not grow at all. The synthesis came back complete — 12,056 characters, untruncated.

**Run 3 re-validated it at a different scale.** Ray ran the same three-level structure at 18 → 3 → 1 and returned a complete, untruncated master synthesis again — confirming the structure works when it is barely needed, not just when it is stressed.

That arc — *measure the ceiling, build the tier that removes it, re-validate across scales* — is what "the architecture scales" actually means in this series. Not a projection from a small demo: a limit found empirically, a structural fix, and a confirmation on the other side.

---

## What the investigations found

Each run produced an architecture-level account of its target that converged across independent, mutually-blind sub-investigations. The convergence is itself the epistemic result: sub-investigations that never saw each other's work arriving at the same structural account means the patterns belong to the system under study, not to any one analysis.

**Transformers** resolved into a registry-driven, configuration-first federation: ~450 self-contained model packages held coherent not by deep inheritance but by a small set of contracts — the configuration object as the architectural spine beneath the public API, a backbone-plus-task-head seam as the universal composability point, containment (not inheritance) for multimodal composition, and a quiet architectural fact with a future: the contract does not privilege attention, which is why FFT cores, state-space models, and linear-recurrence models already live in the library without breaking it. Six cross-cluster patterns, all 15 subs blind to one another; 117 confirmed hypotheses, 1 refuted.

**Kubernetes** resolved into a single architectural cell stamped out at scale: nearly every controller-managed resource traverses the same define → generate → cache → reconcile pipeline (a handful of review-style APIs like TokenReview are the exception), the watch-reconcile loop recurs across several layers, and ~11 code-generator templates — not the ~2,000 packages — are the real codebase. All 12 mid-syntheses converged on that account with zero dissent; 494 confirmed hypotheses, 12 refuted, 0 left open.

**Ray** produced the finding the series exists to demonstrate — a claim that requires holding three languages in one investigation: *all* distributed computation in Ray, across seven-plus domain libraries in three languages, funnels losslessly through exactly three C++ kernel primitives (task, actor, ObjectRef), with type erasure at the wire boundary as the actual cross-language contract. No single-language pass can even state that claim, because the evidence for it lives on both sides of the language boundary at once. Three mid-syntheses, zero dissent, near-identical vocabulary; 159 confirmed, 11 refuted.

Each run also emitted its own coverage frontier — the ranked list of what a next bounded run should investigate. The refuted-hypothesis counts (1, 12, 11) are worth reading as what they are: the investigations generate falsifiable hypotheses and then kill the ones that fail confirmation, which is the property that separates investigation from summarization.

---

## The economics, measured

| Run | Productive compute | Calendar | API-equivalent | Out-of-pocket |
|---|---|---|---|---|
| transformers | ~18.3 hr across 16 executions | 14 days, unattended | ≈$35 | $0 |
| kubernetes | 11 cadenced fires | ~2 days, unattended | ~$637 | $0 |
| ray | 5 batched launches, ~5.2 hr | one afternoon | $123.24 | $0 |

The pattern in the cost column matters more than the totals. Nothing here required a cluster, an enterprise contract, or a research budget — one workstation, subscription-covered model capacity, and an orchestration layer that treats calendar time as the elastic resource. The binding constraints, in practice, were scheduling constraints: execution caps, rate windows, safety envelopes. Those are engineering problems with engineering answers, which is the entire reason the method scales.

---

## What this composes with

This method is one layer of a larger discipline I have written about elsewhere. The hierarchy's bounded tiers are an application of the same geometry the calibration essays describe — keeping every decision inside territory where the distance between yes and no stays wide. The unattended runs sit on the self-tuning human-in-the-loop machinery described in the orchestration essays: phase-gated execution, health telemetry, interrupts that come back when the environment shifts. And the verification posture — hypotheses confirmed against source, refutations recorded, truncations disclosed and reconstructed from cited underlying material — is the same adversarial-review discipline the rest of the stack runs on.

The three full run reports — per-run metrics, the complete pattern catalogs, fault accounting, and independently-verifiable target commits — accompany this piece: [transformers](transformers-capability-proof.html), [Kubernetes](kubernetes-capability-proof.html), and [Ray](ray-polyglot-capability-proof.html). A fourth companion, [Metered knowledge extraction at scale](research-pipeline-efficiency.html), measures the same orchestration discipline applied to a research-corpus workload rather than a codebase.

---

*Daniel Higuera builds production agentic systems through AES Research. Companion essays: [Calibration, boundary layers, and the distance between yes and no](distance-yes-and-no.html), [The 6-tier agent maturity model](6-tier-maturity.html), [Two-tier memory for production agents](two-tier-memory.html), [The context window is a battery](context-window-battery.html), and [Attention management](attention-management.html).*

---

*Licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).*

### Cite this essay

> Higuera, D. (2026, July 4). *Context-unbounded codebase investigation: one method, three codebases, three languages*. AES Research. https://aesresearch.ai/writing/context-unbounded-investigation.html

```bibtex
@misc{higuera2026unbounded,
  author = {Higuera, Daniel},
  title = {Context-unbounded codebase investigation: one method, three codebases, three languages},
  year = {2026},
  month = {jul},
  publisher = {AES Research},
  url = {https://aesresearch.ai/writing/context-unbounded-investigation.html}
}
```
