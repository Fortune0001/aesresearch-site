# The Membrane, Traffic Cop, and Director stack: how to stop prompt injection without killing your agent pipeline

*Defense in depth for agentic workflows — five named roles that compose into a self-tuning human-in-the-loop system.*

---

## The attack class that breaks naive agents

In early 2026, an agent consuming a batch of emails ran into a prompt injection — a few sentences buried in the body of an email. The agent read the email, summarized it, passed the summary to a subagent for evaluation, and the subagent followed the instructions inside the summary: go pull sensitive content from the rest of the inbox and surface it back. The injection had become a prompt by being read.

This is the same class of attack as SQL injection, just one layer up. Instead of strings becoming database queries, content is becoming prompts. It shows up everywhere agents touch external material — the GitHub README attack where injection in a README initiated a bash process and granted file access to a Cline-class IDE agent; the issue-triage variant where a customer-facing form silently feeds a downstream bot; the chatbot-binding-contract case where someone prompt-engineered a car dealership's bot into committing to sell a car for nothing and took the dealership to court over whether the bot could form a contract. The categories differ; the shape doesn't. **An agent with tools and external content has no defense against the content carrying instructions unless that defense is architectural.**

A naive single-agent loop has nothing in its way. The model has been trained to be helpful, and it cannot tell the difference between a prompt I authored and a prompt that arrived inside the data I asked it to read. Prompts and content live in the same address space the moment the model sees them. The only defense is a separation that happens *before* the model sees the content as a prompt — and that separation is a structure of named roles, not a single chokepoint.

This piece walks the five roles I use, in the order they engage. **Membrane, Traffic Cop, Director, Nudge, Phase Gate.** Each does a distinct job. None is sufficient alone. The composition is the defense.

---

## Role one: the Membrane

The Membrane has one question. *Does this pass as a prompt?*

That's it. Not a content filter. Not a quality gate. It is asking whether the thing in front of it should be allowed to enter the prompt layer of the next agent. Prompt injection — by definition — should not.

The architectural rule that makes the Membrane work is upstream of the Membrane itself. **Email content does not become a prompt. README content does not become a prompt. Issue-form content does not become a prompt. None of it does, ever, by default.** External content gets stored as data first — into a database, a structured file, a typed record. Analysis runs against that store. Anything coming out of analysis destined for another agent's prompt has to pass the Membrane on the way out, and the Membrane treats anything that looks like a prompt but came from outside the trust boundary as suspect by construction.

Most naive pipelines check for "looks malicious" — banned words, jailbreak heuristics, classifier scores. Those fail because the attacker writes the content and can phrase the injection to slip past any heuristic. The Membrane sidesteps the arms race by asking a structural question instead of a semantic one. Where did this come from? If the answer is "from a place we don't control," the answer to *does this pass as a prompt* is no. It can still pass as data. It just doesn't get to author the next step.

If your pipeline ever passes raw external content directly into a downstream agent's prompt — even once — the Membrane has nothing to enforce. Drawing the boundary at the architecture level is the work. The Membrane is the guard at a gate that has to actually exist.

---

## Role two: the Traffic Cop

A Membrane catches injection attempts. It does not decide where the legitimate work goes next. The Traffic Cop does.

The Traffic Cop is the agent that knows what every other agent in the pipeline does and doesn't do. It looks at a piece of work that has cleared the Membrane and asks two questions. *Does this make sense? Where does it go from here?*

The first is a sanity pass on the Membrane's output. The Membrane is binary; the Traffic Cop is contextual. If the Membrane stripped attack vectors and returned a cleaned object, the Traffic Cop confirms the cleaning is consistent with what this stage expects to consume. If something that has the surface features of a prompt object came from a source unusual for this workflow, the Traffic Cop flags it back.

The second is routing. The Traffic Cop knows the research agent does research, the verify agent verifies, the skeptic looks for hallucinated language, the writer drafts. It does not dispatch into territory the destination agent isn't equipped for. If a piece of work has a shape the Traffic Cop hasn't seen before, it escalates instead of guessing.

That last property is what makes a Traffic Cop a Traffic Cop and not a static router. A LangGraph DAG says: when work of type X arrives at node A, send it to node B. The Traffic Cop does the same job, but it reasons about whether the routing makes sense given what just happened, and it has the ability to refuse a route the static graph would have taken. This costs more than a static graph. It is also why agents in production survive contact with the messy real world while pure DAGs trip on the first input that doesn't match the schema.

The Traffic Cop is not deeply intelligent and does not need to be. It needs to know the pipeline well enough to refuse the wrong dispatches, and to flag when the Membrane's decision is suspicious. Cheap model. High frequency. Tight prompt.

---

## Role three: the Director

The Director is what the Traffic Cop escalates to.

A Traffic Cop is good at routing work that fits the pipeline and bad at deciding what to do with work that doesn't fit. That is a different kind of decision — not "where does this go next" but "should this happen at all, and under what conditions."

I learned the hard way that a Director is needed. The Traffic Cop was the first orchestration agent I wrote, and for a long time I thought it was enough. It wasn't. The Traffic Cop kept making the right call inside the pipeline and the wrong call at the edges — dispatching novel work into agents that weren't equipped for it (because dispatching is what Traffic Cops do) and refusing to escalate (because escalation wasn't in its role definition). The thing missing wasn't more intelligence. It was a *higher level* in the orchestration hierarchy that owned the question of when the pipeline itself was the wrong shape for the work.

The Director sets phase gates. Decides when to bring a human into the loop. Owns the orchestration-level questions: is this task novel enough that we shouldn't be running it on autopilot? Is the model that just got upgraded calibrated for this kind of work? Has the environment changed in a way that means the Traffic Cop's routing assumptions no longer hold? **A Traffic Cop directs traffic. A Director decides whether the road still goes where it used to.**

Most of the time the Director is silent and the Traffic Cop runs unattended. But the Director is sitting above it, watching for the conditions where routine routing breaks down. When those conditions appear, the Director steps in. Until you have something like the Director in place, it's usually better to keep the human in the loop, because the human is doing the Director's job whether you've named it or not.

---

## Role four: the Nudge

The first three roles are kill-switches and routers. They block, dispatch, escalate. The fourth role does none of those things.

The Nudge is qualitative oversight. An agent whose only job is to ask, periodically, *does this still make sense?*

The Nudge is what would have stopped the $47K agent loop — eleven days, $47,000 in API charges, nothing produced. Two agents calling each other, semantic loop, no observer asking whether the loop should still be running. None of the previous three roles are designed for the question "is this whole thing still a good idea." The Membrane is binary. The Traffic Cop is stage-local. The Director is episodic. None of them watch the long arc of the work.

The Nudge does. It runs alongside the pipeline, samples the state, and asks the soft question. It has no authority to kill. It surfaces a signal. If the signal is loud enough, the Director catches it on the next pass and decides whether to act. If the signal is faint, it accumulates — three Nudges in a row asking whether the loop should still be running is a louder Nudge.

This soft-signal property is the point. **A hard kill-switch is too sharp for this kind of qualitative drift.** A loop that's been running too long is not always wrong — sometimes the work is genuinely large. A research swarm pulling sources for an hour might be the right behavior. A hard rule like "kill any process running over $X" fires on legitimate work and gets disabled by frustrated operators inside a week. The Nudge avoids that failure mode by being a signal, not a switch. It tells the Director something is worth looking at. The Director decides what to do.

The Nudge is a check engine light, not a kill cord. Use the wrong one and you either get fires that nobody noticed, or a system that nobody can keep running.

---

## Role five: the Phase Gate

The Phase Gate is the only one of the five roles that is temporal rather than spatial.

The other four roles all live at boundaries in the pipeline — Membrane between external and internal, Traffic Cop between stages, Director above the Traffic Cop, Nudge across the long arc. The Phase Gate sits in time. It fires when *the kind of work* changes — research into modeling, back-end into front-end, one model family into another. Phase changes warrant recalibration. Phase Gates are the structural recognition that recalibration is owed.

The obvious Phase Gates are easy. Back-end to front-end. Research to modeling. Modeling to deployment. The agents calibrated for the previous phase are now operating on the next, and their calibration may not transfer. A Phase Gate at each boundary is a checkpoint: pause, surface the deliverable, ask whether the result is what we expected, recalibrate for the next phase.

The non-obvious Phase Gates are the ones that get missed. **A model upgrade is a Phase Gate.** Going from Opus 4.6 to Opus 4.7 is a Phase Gate, even though the work hasn't changed. The geometry has. The boundary layers the old model knew how to navigate have shifted under the new model in ways that aren't visible from the outside. An interrupt that fires when calibration is owed will fire more often after a model upgrade — exactly what you want. The system is telling you, by interrupting, that the math underneath has moved. The wrong response is to suppress the interrupts. The right response is to take them seriously, recalibrate, and watch the frequency drop back down as the new boundaries settle. Environment changes are Phase Gates too. Dev to prod. Sandbox account to real account. Small dataset to large. The work is "the same." The geometry isn't.

Phase Gates compose with the Director, which sets them and decides which require a human in the loop. Early in a project, every Phase Gate is human-gated by default. Later, after the agent has been through enough phase changes that it has internalized the calibration, the gates that were once human stops become automated checkpoints. I have run sequences where the first sixteen iterations needed input and the next twenty ran on full autopilot — the gates still firing, but the agent answering them itself, because it had learned the boundary. **The point of a Phase Gate is not that a human always has to be there. It's that the boundary is named, the recalibration is explicit, and someone — the human or the calibrated agent — is making the decision that the work has crossed into new territory.**

---

## Why composition, not chokepoint

Any one of these roles is bypassable.

A Membrane alone is a single chokepoint — a determined attacker can find the case it wasn't written for. A Traffic Cop alone has no defense against external content carrying instructions; if the input never went through a Membrane, the Traffic Cop is reasoning over poisoned material. A Director alone is too high-level to catch every routing mistake. A Nudge alone has no authority — without a Director to act on its signals, it's a logging system. Phase Gates alone are temporal checkpoints with no surrounding orchestration.

**The argument for the stack is that bypassing one role is realistic and bypassing all five simultaneously is structurally hard.** An attacker who slips a prompt past the Membrane still has to slip it past a Traffic Cop that knows the shape of legitimate work in this pipeline, past a Director watching for novelty, past a Nudge asking whether the long arc still makes sense, and past Phase Gates that re-check the geometry whenever the kind of work changes. Each role has a different question and a different blind spot, and the blind spots don't overlap in a way that makes one attack work against all five.

This is defense in depth in the agent-orchestration domain. A firewall plus an IDS plus auth plus audit logs plus least-privilege isn't redundancy — each layer catches a different attack class. The five-role stack is the same idea applied to a different boundary. **Each role is doing a job the others structurally can't.**

---

## Why this is what makes calibration load-bearing

Without this stack, the calibration discipline I've written about elsewhere is theater.

The flagship piece on calibration, boundary layers, and the distance between yes and no makes the geometric argument: the model is never picking yes or no, it's picking a position on the line between them, and reliability is about how far apart those endpoints are at the moment of the decision. Boundary layers are the artifact of that calibration. But calibrated boundary layers require *something to do the recalibration when the geometry shifts*. **The five-role stack is what does it.** The Director notices the boundary has moved. The Phase Gate fires when calibration is owed. The Nudge surfaces the long-arc signal that things have been getting weirder for a while. Without these roles, the boundaries get drawn once at deployment time and rot silently as the model upgrades, the environment shifts, the work moves into novel territory.

The inversion: **human-in-the-loop is structural in a calibrated system, not a paranoia tax.**

A human-in-everything policy is paranoia. A pull-the-humans-out policy is recklessness. Both come from treating human-in-the-loop as a fixed-cadence policy decision instead of as a self-tuning property of the orchestration. The five-role stack defines a self-tuning HITL system: the interrupts come back exactly when the geometry shifts. Model upgrade, environment change, novel territory — interrupts come back. Routine work in a stable environment — interrupts taper toward zero, the human moves further out of the loop, and the system runs at full autopilot in the regime where full autopilot is correct. The human is in the loop because the geometry says so, and the geometry tells the system when to invite the human back in.

The cost of running without the stack is paid in the absence, not the presence. Two to ten times the cost of the actual work — not in per-token pricing, but in wild goose chases, semantic loops the Nudge would have flagged, novel-territory work the Director should have escalated and didn't. The $47K loop is the load-bearing example because it made the news; the median failure is smaller and quieter, and pays out continuously. The Membrane stops a class of attack that would otherwise be free for an attacker to attempt. The Traffic Cop stops dispatch into the wrong agent. The Director stops the pipeline from running on autopilot through territory it isn't calibrated for. The Nudge stops the eleven-day loop. The Phase Gate stops the silent recalibration debt that accumulates every time the model upgrades. These are not features. They are the cost of running agentic work safely at all.

Build organically. Calibrate as you go. Trust the interrupts when they come back — they are the only honest signal the system has about its own boundaries. The apparent shortcuts — single chokepoints, fixed-cadence approval gates, content-classifier filters — are how the well-publicized failures keep happening.

---

*Daniel Higuera builds production agentic systems through AES Research. This essay sits beside the calibration spine the rest of the series is built on. Companion pieces: [Calibration, boundary layers, and the distance between yes and no](distance-yes-and-no.html), [Two-tier memory for production agents](two-tier-memory.html), [The context window is a battery](context-window-battery.html), [Attention management](attention-management.html), and [The 6-tier agentic maturity model](6-tier-maturity.html).*
