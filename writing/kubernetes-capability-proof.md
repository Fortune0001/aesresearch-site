# Context-Unbounded Codebase Investigation — A Capability Proof on Kubernetes (3.6M LOC)

*A hierarchical multi-agent swarm investigated all 2,001 Go packages of Kubernetes — 3.6M lines — and produced one coherent architecture-level synthesis, with no reasoning context ever exceeding a bounded working set.*

**Date:** 2026-06-05 · **Target:** `kubernetes/kubernetes` @ master (`7a1385a3`; full SHA `7a1385a332e503ac051edc39a57e0d84fc5c4e98`) · **Cost:** $0 actual (ran within existing subscription capacity; ~$637 API-equivalent)

## What this demonstrates

AES Research's investigation architecture — a hierarchical, multi-agent research system — investigated the **entire Kubernetes codebase, 2,001 packages / 3.6M lines of Go, and produced a single coherent architecture-level synthesis, with no individual reasoning context ever exceeding a bounded working set.** This is the empirical proof that automated codebase investigation scales to arbitrarily large systems: per-tier context stays *flat* as total scope grows.

The target was deliberately **non-AI** — a distributed-systems codebase in Go — to show the architecture generalizes beyond the ML domain it was first exercised on (a prior run analyzed a 450-model ML library; this run is 4.4× the targets and a different language and domain).

## The run (all figures measured, not estimated)

| Metric | Value |
|---|---|
| Repo / commit | `kubernetes/kubernetes` @ master `7a1385a3` |
| Scale (measured) | **3,598,801 Go LOC** excl. vendor; 12,764 files; 3,082 packages |
| Targets investigated | **2,001** substantial core packages (≥100 LOC) |
| Hierarchy | **67 sub-investigations → 12 mid-coordinators → 1 master** (3-level) |
| Findings | **6,329** raw · **494 confirmed** hypotheses · 12 refuted · 0 left open |
| Convergence | all **12** mid-syntheses converged on the same architecture, **zero dissent** |
| Compute | 11 cadenced fires over ~2 days; no fire exceeded the ~74-min hardware cap |
| Reliability | **0 chunks lost**; self-healing carried the run unattended across a provider quota-reset boundary |
| Per-tier context | **bounded at every tier** — the master read 12 mid-syntheses, never 67 subs |
| Cost | **$0 actual** (subscription capacity); ~$637 API-equivalent |

## Headline: seven convergent meta-patterns

The master synthesis (12,056 characters, complete) surfaced seven cross-cluster patterns **no single sub-investigation could see** — each requires stitching findings across clusters:

1. **Four-Stage Pipeline — Define → Generate → Cache → Reconcile.** Nearly every controller-managed resource traverses the same four stages (imperative review APIs like TokenReview and SubjectAccessReview skip the cache and reconcile stages); the ~2,000 packages are combinatorial expansion (API groups × versions × generated layers), not 2,000 independent designs.
2. **Fractal Reconciliation.** The watch→enqueue→reconcile→requeue loop recurs at five scales (kube-proxy's rate-gated BoundedFrequencyRunner, kubelet's per-domain sub-managers, kube-controller-manager's ~50 controllers, the scheduler's backoff/requeue queue, and kubeadm's phase-based bootstrap — the last an idempotent-convergence analog rather than a literal watch loop) — understanding one controller is architecturally equivalent to understanding all.
3. **Interface-Segregated Chain Composition.** Narrow Go interfaces composed into ordered chains is the universal wiring idiom (auth, admission, storage, HTTP, streaming); Kubernetes replaces inheritance and plugin SDKs with one composition strategy.
4. **Code Generation as Architectural Governance.** ~11 generator templates — not the ~2,000 packages — are the "real" codebase; cross-group drift is structurally impossible because every group passes the same template pipeline.
5. **Generic-Store + Strategy as the API Surface Atom.** Every resource = `genericregistry.Store` + a type-specific `Strategy`; CRDs are projections of the same architecture, sharing identical persistence/serialization/watch semantics with built-in resources, and passing through the same generic admission chain upstream of the store.
6. **Hub-and-Spoke API Versioning.** Internal "hub" types + generated conversions decouple storage from wire format; API compatibility is an *emergent consequence of codegen + hub types*, not a code-review policy.
7. **Phased Component Bootstrap with DI.** Every binary boots through a phased, dependency-ordered sequence — a run-once analog of the reconcile pattern used elsewhere, converging at startup rather than watching continuously.

> *"Kubernetes is a declarative, level-triggered reconciliation engine whose ~2,000-package codebase is not 2,000 independent designs but a single architectural cell — versioned types → generated clients → informer caches → reconcile loops — stamped out by code generators and composed through narrow Go interfaces."* — master synthesis, converged across all 12 mid-coordinators with zero dissent.

The **convergence is itself the result**: 12 independent mid-syntheses, each over a different ~5–6-sub slice of the codebase, arrived at the same characterization. 12 refuted hypotheses out of 6,329 — all local edge cases, no inter-cluster contradictions.

## Why it scales — the composition

The capability is built by composing four primitives, each bounding a different dimension:

- **Hierarchical synthesis bounds CONTEXT.** In a two-level configuration, the master's brief grows with sub count — on the prior 450-target run it saturated at 15 subs. The third tier is the primitive that removes that growth: it caps every tier's fan-in — the master reads 12 mids, each mid reads ~6 subs, each sub investigates ~30 packages. No reasoning context grows with total scale; that flatness *is* the "context-unbounded" property. Scaling curve: **450 targets / 15-sub master fan-in → 2,001 targets / 12-mid master fan-in** — fan-in stayed bounded while targets grew 4.4×.
- **Parallel fan-out bounds WALL-CLOCK.** Independent subs and independent mid-syntheses run concurrently inside a measured hardware-safe band, so total time tracks depth, not breadth.
- **Cadenced firing bounds HARDWARE STRESS.** Work decomposes into bounded fires; no single fire exceeds the safety envelope.
- **Self-healing bounds RELIABILITY.** Transient timeouts and budget caps pause-and-retry without losing work; the run finished unattended across a provider quota-reset boundary with zero chunks lost.

Together: *investigate an arbitrarily large codebase, at bounded per-tier context, in bounded wall-clock, on bounded hardware, unattended.*

## Fault absorption, measured

Reliability was exercised, not assumed. Over the full run, agent-level transient failures — 10 timeouts and 5 budget-cap hits — were absorbed by the self-healing layer with **0 chunks lost**. Operating parameters were retuned mid-run (per-agent timeout 1200s→600s; per-coordinator synthesis budget capped at $1) without stopping the investigation, and the run completed unattended, including traversal of a provider quota-reset window.

## Coverage frontier — the next targets

The investigation maps its own coverage frontier as it runs. It flagged five areas as the natural next targets: (1) `kube-proxy` networking data-plane internals, (2) scheduler scoring/filtering plugin algorithms, (3) etcd client interaction patterns (watch multiplexing, leases, compaction), (4) testing / e2e infrastructure, (5) feature-gate propagation from flags through to runtime behavior.

## Provenance

Every figure above is measured, not estimated: scale figures come from a direct count on the clone at the stated commit, and hierarchy, findings, convergence, reliability, and cost figures come from the run's own measurement records and per-fire usage logs. The target commit is publicly resolvable on GitHub, so the scale measurements are independently reproducible.

---

*Licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).*

### Cite this essay

> Higuera, D. (2026, July 4). *Context-Unbounded Codebase Investigation — A Capability Proof on Kubernetes (3.6M LOC)*. AES Research. https://aesresearch.ai/writing/kubernetes-capability-proof.html

```bibtex
@misc{higuera2026kubernetes,
  author = {Higuera, Daniel},
  title = {Context-Unbounded Codebase Investigation — A Capability Proof on Kubernetes (3.6M LOC)},
  year = {2026},
  month = {jul},
  publisher = {AES Research},
  url = {https://aesresearch.ai/writing/kubernetes-capability-proof.html}
}
```
