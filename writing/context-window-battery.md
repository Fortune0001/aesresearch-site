# The context window is a battery: surviving compaction on long-running agents

*What happens to your calibration when the context fills up, why compaction drops the work you need most, and the operational discipline that protects you from it.*

---

## The battery

The context window is a battery. Every token the agent consumes drains it: your instructions, the conversation history, the files it reads, the output from sub-agents, every turn of the interaction. When the battery runs out, the agent compacts — it summarizes its own history to free up space. That compaction is what kills long-running work if you haven't planned for it.

Think about a circular saw running on a battery pack. It doesn't warn you two minutes before it dies. There's no low-power indicator that gradually slows the blade. It cuts. And then it cuts out. Whatever you were in the middle of is now mangled — a ragged edge on a cut that should have been clean. That's what compaction does to agents mid-task. No graceful degradation. One moment the agent has your full calibration in context, the next moment it doesn't, and the work continues on a summary that threw away the parts you needed.

This is solvable. But only if you understand what compaction actually does.

## Compaction is lossy

Compaction is lossy compression. That's the term of the trade. It's not a zip file where everything comes back perfectly when you unzip. It's a JPEG. It keeps the big shapes and throws away the fine detail.

What gets kept? The middle of the agent's understanding. The parts of the training distribution it knows well. Standard patterns, common workflows, the shape of the conversation rather than its specifics. The agent compacts based on what it *understands*, not based on what you *need it to remember*.

What gets dropped? The tails. Novel territory. The calibration you built for tail-end work. The skeptic rubrics you configured. The specific boundary conditions you worked out over twenty turns. All the fine detail you accumulated in the session — the stuff that turned a generic agent into your calibrated collaborator — that's the JPEG artifact. That's what the compaction algorithm treats as fluff, because the algorithm doesn't know the difference between fluff and hard-won precision at the tails.

The failure mode is predictable. You spend an hour calibrating the agent to your domain — correcting its confident wrong answers, establishing conventions, teaching it the distinctions your domain depends on. That calibration lives in conversation history. Compaction fires. The calibration gets compressed down to "the user prefers X" and the specifics evaporate. The next response is back to generic-agent defaults, and you don't notice at first, because the agent is confident and the format looks right.

## Atomic writes

The fix is to write your calibration out of the volatile context window and into persistent files before compaction hits. Every calibrated procedure, every skeptic rubric, every boundary-layer configuration, every convention that works — all of it goes to disk while it's still fresh in context.

Use the word *atomic* deliberately. Atomic writes mean you write to a temporary file first, then move that temp file to the permanent location. Term of the trade in file systems and databases. The reason it matters: if compaction fires while the agent is mid-write on a memory file, you can end up with a half-written file that's worse than no file at all. Temp file first, commit second. Always.

I've tested this. I've had agents corrupt their own memory files because they were doing a direct write when compaction fired. The agent comes back after compaction, tries to read its memory, and the file is garbage. Now you've lost both the context window content *and* the persistent memory. You're starting from scratch. Atomic writes exist specifically to make this failure mode impossible — the permanent file is never in a partial state.

## Two memory types, different cadences

Not all calibration saves at the same tempo.

**Procedural memory** is task-specific. How to interact with a given system, how to structure a kind of deliverable, what works for a specific workflow. These save when you finish calibrating a procedure and confirm it holds. You don't save procedural memory every five minutes. You save it when the procedure is locked.

**Introspective memory** is session-level. What the agent has learned about you, about your conventions, about how it operates with you. How much detail you want in responses. Your vocabulary. Your domain focus. How you dispatch sub-agents. These accumulate across the conversation and save at a faster cadence — every time the agent learns something new about how to work with you, that's introspective memory, and it should be flushing to disk regularly throughout the session.

If you only save one type, you lose the other when compaction hits. Procedural saves alone give you the "how" but not the "for whom." Introspective saves alone give you the register but not the procedures. Both need their own files, their own cadence, and their own atomic-write discipline.

## The pre-post compaction test

Compaction damage is measurable. You don't have to guess where the calibration got lost.

Before compaction fires, ask the agent to summarize a nuanced topic from your session. Something at the tails — something that required calibration to get right, something that's not in the middle of the distribution. Have it give you the detailed version. Save the summary somewhere outside the context window.

After compaction fires, ask the exact same question. Compare the two responses. Where did the agent drift? What did it forget? What did it simplify? What did it state confidently that's actually wrong now?

Those drift points are where your calibration was lost. That's where the compaction damage landed. And the test is repeatable — you can run it every time compaction happens, and it tells you exactly what to re-inject from your memory files to get the agent back on track.

The reason this works: compaction compresses based on the agent's understanding, and at the tails it doesn't understand what's important and what's fluff. It makes bad decisions about what to keep and what to throw away. The pre-post test exposes exactly where those bad decisions landed.

## Sub-agent response discipline

The fastest way to drain the battery is to let your sub-agents return book reports.

Every token a sub-agent wastes is a token you don't have for actual work. Every two-page summary that comes back from a sub-agent gets consumed by your main agent. It drains the battery. Multiply that by twenty sub-agent dispatches in a session and you've burned a huge fraction of your context window on fluff — which pulls you closer to compaction, and when compaction fires, the book reports survive (they're in the middle of the distribution; the compaction algorithm recognizes their shape) while your tail-end calibration dies.

The discipline is simple: train your sub-agents to be concise. A sub-agent that does work and returns ten tokens is worth twenty that return book reports.

Concrete tactic: specify the response format in the dispatch instructions. Don't just tell the sub-agent what to do. Tell it how to respond. "Respond with the file path and the word done." "Respond with pass or fail and nothing else." "Respond with the count only." If you leave the output format open, you'll get book reports by default, because the model's training pushes it toward helpful-sounding verbose responses. You have to calibrate that out explicitly.

This isn't about being curt with the sub-agent. It's about context window survival. Every token matters when you're managing a battery.

## Recovery: RAG back into your own memory

Once you've taken the pre-post compaction test and identified the damage, recovery is mechanical. You have your memory files. The agent reads its own saved calibration, its own saved procedures, and it reconstructs the understanding that got compacted out. RAG, but pointed at your own persistent memory rather than an external corpus.

This is why atomic writes are the safety net that has to hold. If the memory files are corrupt or incomplete, there's nothing to RAG back into. The whole recovery chain depends on having clean, complete memory files on disk. That's the safety net — and it only works if the discipline was in place *before* you needed it.

The ordering matters. You don't build the safety net during the fall.

## Bringing it together

The context window is a battery. Compaction is lossy compression that drops the tails first. Atomic writes protect your calibration from being lost mid-flight. Procedural and introspective memory need saving on different cadences. The pre-post compaction test measures the damage. Sub-agent response discipline extends battery life. And the recovery path — RAG back into your own memory — only exists if the atomic-write discipline held from the start.

None of this is optional on a long-running agent. The failure mode isn't "the agent is confused;" it's "the agent confidently operates on a summary that threw away your calibration, and the output looks fine until it doesn't."

This pattern pairs with the two-tier memory architecture: memory files are *what* you save, and atomic writes + cadenced saves are *when* and *how*. It pairs with attention management: knowing which sub-agent calls are cheap enough to justify the battery cost is an attention-routing decision. The patterns compose into a working system. In isolation, none of them survives real use.

---

*Daniel Higuera — AES Research — 2026*

*Part of a series on agent architecture patterns. See also: [Two-tier memory for production agents](two-tier-memory.html) and [Attention management](attention-management.html). The video version of this material is session 05 of the AI 101 curriculum — contact for access.*
