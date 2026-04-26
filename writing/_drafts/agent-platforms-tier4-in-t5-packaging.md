# Most agent platforms are Tier 4 in T5 packaging: a tour of the marketplace

*AES Research / Opinion. A tour of the agent-tool marketplace through the 6-tier lens. Read as marketplace analysis, not as experimental result.*

---

## A diagnostic, before the tour

A reader looking at any agent platform — vendor demo, OSS framework, enterprise procurement deck — should be able to reach a tier verdict in under a minute. The diagnostic is three questions, deliberately blunt.

1. Does the platform ship a **rubric system separable from any specific deployment** — a body of governance that lives outside the graph and applies across all of them?
2. Does it ship **calibrated evaluation** — judges measured against a known-good corpus — rather than a trace UI that lets you watch executions go by?
3. Does it ship **cross-session memory distinct from conversation history** — knowledge that compounds across runs of different graphs, not just resume-state for an interrupted execution?

If the answer is "no" to two of three, the platform is **Tier 4 in T5 packaging**, regardless of what the homepage says. The tooling may be excellent. The default deployment is not Tier 5. To reach Tier 5, the operator has to author the missing layers themselves — measured separately at two to four months of dedicated build.

That is the spine. The tier the marketing claims is not the tier the work runs at. The marketplace has gotten very good at packaging the substrate of Tier 5 — orchestration graphs, durable execution, observability traces — and very little has happened on the policy layer that sits on top of substrate and converts it into Tier 5 capability. The reader who internalizes the three-question diagnostic stops being available to be sold the gap.

---

## **The Lang ecosystem case study — and the mis-evaluation pattern**

Take the most-adopted open-source orchestration framework and run the diagnostic on each component. Not to pick on the Lang stack — it is the thing I would reach for first if I were buying substrate today — but because it is the most carefully built and the cleanest case for showing where the boundary actually lies.

**LangChain alone is Tier 3.** *— a chain of glue, fast generation in any one session, and inconsistency across sessions you don't notice until integration.* A chain composition library and a glue layer. No orchestration shape, no governance, no evaluation discipline. It accelerates per-call work, and that is what it is for. A team running LangChain without anything else has shipped the trough of the maturity ladder — naïve AI adoption that produces rapid, internally-fluent, cross-session-inconsistent output. Reconciliation overhead exceeds the per-call speedup. LangChain is honest about this; it does not claim otherwise. The mistake is reaching for it and assuming the rest of the stack will be added later by someone, somewhere.

**LangGraph alone is Tier 4 default, Tier 5 ceiling, with a wide gap between the two.** *— the graph runs, the engineering is good, and there is nobody home in the methodology layer until the operator writes it.* LangGraph is a state-graph engine — directed graph with annotated reducers for concurrent updates, durable checkpointing across InMemory and SQLite and Postgres, human-in-the-loop interrupts, subgraphs with explicit child-to-parent communication, streaming-by-default. The engineering is genuinely good. The annotated-reducer pattern is original and elegant. The checkpointer is production-grade. The framework runs.

What LangGraph is not is a methodology. The graph does not tell you how agents should communicate, when to refuse work versus clarify versus proceed, what constitutes a valid handoff, which decisions are bounded actions versus require human review, or how to resolve disagreement between nodes. There is no rubric system separable from any specific graph. There is no role hierarchy with authority gradients — every node is a function with no identity. There is no quality framework — zero evaluation primitives ship in the box, and a "validator node" added by an operator is not the same thing as a judge measured against a corpus of fifty known-good and fifty known-bad outputs. State is a TypedDict with reducers — shared mutable variables, not knowledge. Checkpointing is execution-resume, not learning. No model for context-window exhaustion. No client profile.

Each of these is the operator's job. A LangGraph deployment that has authored the rubric system, the role hierarchy, the corpus-grounded evaluators, the cross-graph contracts, and the client profile reaches Tier 5. The investment is real — eight to sixteen weeks of operator-authored discipline — but the ceiling is genuinely there. A LangGraph deployment that has not done that work is Tier 4. Sophisticated single-context engineering. No methodology layer.

**LangSmith and LangFuse are both Tier 4 default, Tier 5 ceiling — same gap.** *— the trace UI is excellent and looking at lots of traces is not the same thing as evaluating against a corpus.* They ship excellent traces. The trace UI matured significantly over the last eighteen months. The problem is that traces-as-evidence-of-evaluation is the most common observability mistake in the marketplace. A judge that has not been measured against a known-good corpus is performing eval theater regardless of how good the trace UI is, and looking at lots of traces does not produce calibration — it produces familiarity, which is a different thing. The corpus, the gating thresholds, the recalibration cadence when a model upgrade silently moves the boundary — that is the operator's job. Self-hosting LangFuse instead of paying for LangSmith is a procurement choice; it is not a methodology choice.

**LangServe is Tier 3, Tier 4 ceiling.** *— it deploys; it does not decide what good looks like.* A runtime boundary, a way to deploy chains as services. Not a methodology surface. Conflating "we shipped it on LangServe" with "we have a methodology" is a different version of the same mistake.

The Lang suite is Tier 4-and-a-half: the substrate is complete, the policy layer is missing, and this is where reviewers most often misread the marketplace.

When LangGraph is reviewed in isolation, reviewers correctly identify that it lacks evaluation surfaces and call it incomplete. When the full Lang suite is reviewed, the LangSmith-shaped hole is filled, the substrate looks complete, and reviewers conclude T5, and both readings miss the boundary. Substrate completeness is *necessary* for Tier 5. It is not *sufficient*. Sufficiency requires policy on top of substrate, and the suite — by design, by stated intention, by the vendor's own marketing if you read it carefully — does not ship the policy. It is the most complete OSS substrate currently available. It does not, and does not claim to be, a methodology.

The pattern that makes this hard to see is that Tier 4 substrate looks like Tier 5 from the outside when the reviewer is not asking the three diagnostic questions. The reviewer infers methodology from the presence of substrate, the way a non-trader infers a trading strategy from the presence of a Bloomberg terminal. The terminal is not the strategy. The substrate is not the policy.

Apply the same lens to OpenAI Assistants, CrewAI, AutoGen, Google's Agent Development Kit, the Anthropic Claude Agent SDK — Tier 4 default, Tier 5 ceiling reachable only through operator-authored governance — and the picture is the same. Twenty-four of fifty-eight tools in the survey default to Tier 4. One defaults to Tier 5. Zero default to Tier 6. The marketplace did not produce this distribution by accident.

---

## **The catalog: nine ways "the platform handles it" goes wrong**

If the diagnostic is a single test, the catalog is the textbook of failure modes that test catches. Each of these is operator-believed-policy turning out to be vendor-shipped-substrate. The pattern is consistent enough across categories that I have started using it as a heuristic on every vendor call.

**Threads = memory.** OpenAI Assistants ships a thread primitive — persistent conversation state retrievable by ID. Operators read "memory" into this and assume the system carries learned knowledge across runs. It does not. Threads are conversation history with persistence. The model that consumes the thread sees a longer transcript. There is no compounding asset, no across-thread inference, no decision about what was worth remembering.

**Checkpointing = memory.** The LangGraph variant of the same mistake, more dangerous because the checkpointing is genuinely good. The checkpointer resumes an interrupted execution from the last good state. Process crashes recover cleanly. Human-in-the-loop interrupts hold state across hours. None of it is a learning system. The error rate does not decrease over runs. Findings from one graph do not inform another. A team that says "we have memory because we have checkpointing" has confused durable execution with knowledge accumulation. The fix is to author a separate cross-session memory layer on top.

**Crew = governed team.** CrewAI ships role-based agent compositions — a Researcher and a Writer and an Editor, whatever decomposition the operator authors. Roles are real. What the framework does not give you is an authority gradient. A "crew" is a group of agents with role labels. A governed team has decision rights at different levels with explicit escalation protocol — *intervene at the lowest authority that can resolve the issue* is a discipline, not a parameter. CrewAI deployments at scale routinely ship as flat function graphs with role nameplates. Tier 4 with labels, not Tier 5.

**Workflow = orchestration.** n8n, Make, Activepieces. These tools execute conditional sequences of API calls and they execute them well. Operators read "workflow engine" as "agent orchestration framework," and the slippage is structural — workflows are deterministic execution graphs with branching; agentic orchestration is an LLM choosing among actions with tool-call binding. A workflow that calls an LLM at one step is not an agent stack. It is a workflow with an LLM step.

**DLP = governance.** Microsoft Copilot Studio ships Data Loss Prevention controls — what data can leave the tenancy, which connectors are allowed, which fields are redacted. DLP is real and good and solves a real compliance problem. It is not governance in the agent-architecture sense. Governance includes rubrics, role hierarchy, evaluation discipline, cross-session memory, dispatch protocol, client profile. DLP is the perimeter; governance is the methodology that runs inside the perimeter.

**Topics = role hierarchy.** Salesforce Agentforce ships "topics" — clusters of related skills that an agent can specialize in. Topics are useful. They are not authority gradients. An agent with topic specialization is still a flat actor; it does not escalate to a higher-authority agent on decisions outside its scope, and there is no runtime protocol for what "outside its scope" means.

**Vector DB = RAG.** Pinecone, Weaviate, Qdrant, Chroma, pgvector. Excellent infrastructure. Vector storage and retrieval are substrate for RAG. RAG is the methodology — what to embed, how to chunk, when to retrieve, how to interleave retrieval with generation, how to detect when retrieval missed. The methodology layer is empty in every vector DB I have surveyed. A team that says "we have RAG because we have Pinecone" is at the bottom of a long ladder they have not started climbing.

**Trace = eval.** Already covered. Traces show what happened. Evaluation tells you whether what happened was good. The first does not produce the second.

**Visual canvas = methodology.** OpenAI Agent Builder, Flowise, Dify. The canvas is a representation. It does not make the underlying agent stack methodologically sound. A pretty diagram of an ungoverned system is an ungoverned system with a pretty diagram.

In every case the platform provides substrate and the operator believes it is providing policy. The framework's diagnostic — what tier did the org expect, what tier does the tool ship at, what tier does the work require — is built for exactly this gap. When the three are misaligned, the deployment fails in ways that look like model or framework failures but are actually procurement failures.

---

## **Palantir is the only Tier-5-default tool in the survey — and it costs accordingly**

Of fifty-eight tools surveyed across nine categories, exactly one defaults to Tier 5: Palantir AIP. This is the case that proves the rule. When governance ships pre-built — when the rubric system, the role hierarchy, the evaluation discipline, the cross-session knowledge layer, the dispatch protocol all come in the box — the box costs enterprise money and the procurement is bespoke. AIP is not sold by the seat on a self-serve page. There is a sales motion, a deployment engagement, and a price tag that reflects the fact that what you are buying is methodology embedded in software, not software with a methodology stickered on top.

Adjacent platforms — Microsoft Copilot Studio, Salesforce Agentforce, ServiceNow Now Assist, Databricks Mosaic — ship governance *shape* but not governance *substance*. They give you action types and topics and skills and lineage primitives. The shape is real and useful. The work that turns shape into Tier 5 capability is the operator's authoring job. The procurement-vs-build trade in concrete form: closed enterprise platforms charge enterprise pricing for governance scaffolding; the OSS path requires operator-authored discipline measured in months. Neither is wrong. The mistake is failing to recognize that you are paying one of those two costs whether you intend to or not.

This is the most direct empirical evidence that the framework is real. If Tier 5 were a marketing label, the marketplace would be saturated with Tier-5-default tools. It is not. There is one. Tier 5 is hard to ship as a product because it requires methodology embedded in software, and most vendors cannot afford to encode opinions strong enough to be methodology-shaped. Palantir can because its organizational character — Forward Deployed Engineers embedded in customer engagements, decades of experience in regulated deployments — produced opinions of that strength. Other vendors are honest in not pretending to ship what they do not have.

If the platform you are evaluating is not Palantir AIP, it is not Tier 5 default. The work to reach Tier 5 is yours.

---

## **The vibe-code category is structurally different — and worth naming separately**

Lovable, v0, Bolt.new, Replit Agent. Calling them "low-quality Tier 3 tools" misses what they actually are. They are honest products for prototype work. The UX premise — *skip the methodology, let the AI generate the application end-to-end, ship a working demo* — is the explicit value proposition. They do exactly what they advertise. For demo, for prototype, for the moment when you need something running by Friday and the question is whether the idea is plausible at all, they earn their seat.

The structural problem is that the same UX premise that makes them good for prototyping makes them anti-patterns for sustained development. The premise is *skip the methodology*. Skipping the methodology IS the Tier 3 trough by definition — fast generation without consistency discipline produces output that compounds inconsistencies across sessions, which produces reconciliation work that exceeds the per-file speedup. Vibe-code tools are not failing to climb out of the trough; they are explicitly not trying to. The trough is the product.

The marketplace failure happens when a vibe-code tool gets mistaken for a platform. A team prototypes something on Lovable, the demo works, leadership sees the demo, the team is told to "productionize what you built," and now the team is doing sustained development on top of an artifact whose substrate was never designed for it. Within a quarter the team is rewriting from scratch on a different stack and pretending the vibe-code phase did not happen. The tool did its job; the org used it for a job it was not built for.

Treating vibe-code as a category — Tier 3 by design, valuable for the prototype slot, anti-pattern in the sustained-development slot — keeps the discipline honest. The tool is not bad. The deployment context decides whether it is being used well. The right question on every product demo is not whether the tool is good. It is whether the tool's slot matches the slot the buyer is filling.

---

## **The marketplace gaps — what the framework predicts and the survey confirms**

If the tier framework has predictive power, it should predict where the marketplace has not built — empty product slots that are load-bearing for Tier 5 capability and that operator-authored work is currently filling because no vendor has shipped the layer. The 58-tool survey produced ten such gaps.

OSS Tier-5 governance frameworks — the largest gap, by some distance. Cross-program knowledge transfer where findings from one project inform another autonomously. Judge infrastructure that ships a calibration discipline rather than templates. Client-profile models where the human is treated as an entity with preferences, vocabulary, authority, domain expertise. Re-execution-over-recovery as a framework primitive — frameworks optimize for partial-state recovery; the opposite principle is currently authored ad hoc. Predictive-friction identification that surfaces bottlenecks weeks before they manifest. Cross-domain pattern transfer at the agent level. Authority-gradient orchestration where decision rights at different levels carry explicit escalation protocol. Brief-as-artifact — canonical structured task specs persisting as versioned files, consumed by stateless executors. Pre-built judge corpora shipping for common task classes.

Each of these is an essential component of a Tier 5 deployment. None ships in any tool I surveyed. The empty slots are the evidence. If the framework were merely descriptive, the marketplace could fill the slots in any direction. Instead it consistently builds substrate up to the predicted boundary and stops, leaving the policy-on-substrate work to the operator. That is a falsifiable prediction the survey confirms in ten places.

The reader who concludes "I should buy more tools to fill these gaps" has missed the point. The gaps are not buy-able right now. They are author-able. The buy-vs-build call at the Tier 4-to-5 transition has one honest answer: *buy the substrate, author the policy*. Buying more substrate does not climb the tier ladder. Authoring the policy on top of the substrate you already have does.

---

## **The positions, restated**

Vibe-code is honest Tier 3, anti-pattern in the sustained-development slot. Use for prototype, not for platform. The Lang suite is the most complete substrate currently available in OSS and is Tier 4-and-a-half — substrate complete, policy absent — and the common review error is mistaking suite completeness for tier completeness. Palantir AIP is the only Tier-5-default tool in fifty-eight, and that finding is more important than any individual tool comparison because it tells you what the marketplace can ship as a product versus what it cannot. The catalog of nine "platform handles it" failure modes is what happens when buyers do not run the three-question diagnostic before procurement.

The marketplace is not failing. It is doing exactly what marketplaces do — building the substrate where the substrate is buildable as a product, leaving the policy work to the operator because the policy work has not yet found a productizable shape outside of bespoke enterprise engagements. A practitioner who reads the marketplace this way stops being available to be sold the gap. A practitioner who does not will discover the gap on the day the deployment fails, the failure will look like a model problem or a framework problem, and the team will spend the next quarter shopping for a better substrate when what they actually needed was the policy layer the substrate was never going to ship.

The cost of that misdiagnosis is paid by the senior engineer who walks away from the tool, the analyst who shipped the wrong number, the audit finding that got missed, and the next round of buyers who hear "AI rollout failed at our org" and wonder whether the technology is just not ready. The technology is fine. The composition is the work.

The diagnostic at the top of this piece is the cheapest tool I know for not being on the wrong side of that gap. Three questions, under a minute, no procurement budget required. Run it on the next platform you are about to buy. If two of three answers are no, you are looking at Tier 4 in T5 packaging, and the work to reach Tier 5 is the work you are about to underestimate.

---

*Daniel Higuera builds production agentic systems through AES Research. This is the inaugural piece in the AES Research opinion track — marketplace analysis, not experimental result. The research-track companion pieces — [Calibration, boundary layers, and the distance between yes and no](distance-yes-and-no.html), [Two-tier memory for production agents](two-tier-memory.html), [The context window is a battery](context-window-battery.html), and [Attention management](attention-management.html) — report on systems built and experiments run. Forthcoming research-track pieces include [The 6-tier agent maturity model](6-tier-maturity.html) and [What changes when an agentic AI initiative crosses 50 people](agentic-initiative-50-people.html), which is the Director-track companion to this op-ed. Read the research pieces as findings; read this one as opinion.*
