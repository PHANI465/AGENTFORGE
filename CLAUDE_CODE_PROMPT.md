# Claude Code — Starter Prompt

Copy everything below the line into your first Claude Code session.

---

## THE PROMPT (copy from here)

```
You are working on AgentForge — an agent-native AI platform for building, deploying, evaluating, monitoring, and governing AI agents.

Before doing ANYTHING, read these files in this exact order:
1. CLAUDE.md — project context, tech stack, conventions
2. ARCHITECTURE.md — system design, components, data model
3. MILESTONES.md — ordered build plan
4. CURSOR_TASKS.md — parallel work tracker

After reading, confirm your understanding by answering:
- What is AgentForge?
- What are the 6 core components?
- What is the current milestone?
- What tech stack are we using?

Then ask me any questions you have before starting.

## Model & Effort Guide (CRITICAL — remind me to switch)

You MUST remind me to change the model at the right time. Here is the plan:

| Milestones | Model | Effort | Why |
|---|---|---|---|
| 0, 1, 2 | Sonnet 5 | high | Scaffolding, models, CRUD — standard patterns |
| 3, 4, 5 | Opus | xhigh | Agent execution loop, safety engine, OpenTelemetry — complex architecture |
| 6, 7, 8, 9, 10 | Sonnet 5 | high | Eval pipeline, dashboard, IaC — well-scoped work |

**When finishing Milestone 2**, include this at the end of your report:

⚠️ MODEL SWITCH REQUIRED
Milestone 3 (Agent Execution) is architecture-heavy.
Before starting, run these commands:
  /model opus
  Then set effort to xhigh using → arrow key
This gives you deeper reasoning for the execution loop, tool orchestration, and LiteLLM integration.

**When finishing Milestone 5**, include this at the end of your report:

⚠️ MODEL SWITCH REQUIRED
Milestones 6-10 are well-scoped implementation work.
Switch back to save costs:
  /model sonnet
  Then set effort to high using ← arrow key

## Workflow Rules (CRITICAL — follow these every session)

1. **Work one milestone at a time.** Check MILESTONES.md for the current one.
2. **After every implementation session, always end with this report:**

   ### ✅ What was done
   - (list files created/modified and what they do)

   ### 🔜 What's next
   - (the next task or milestone to tackle)

   ### 🖱️ Cursor tasks
   - (what I should work on in Cursor IDE in the meantime)
   - (update CURSOR_TASKS.md with these)

   ### ⚠️ Model/effort reminder
   - (if the next milestone requires a model switch, remind me here)
   - (if no switch needed, say "No model change needed — stay on [current model]")

3. **Update MILESTONES.md** — check off completed items.
4. **Update CURSOR_TASKS.md** — add new Cursor tasks as they emerge.
5. **Never skip tests.** Every feature needs at least basic tests.
6. **Never hardcode secrets.** Use environment variables.
7. **Follow the coding conventions in CLAUDE.md** — type hints, Pydantic models, async, etc.

## Current Objective
Start with Milestone 0: Project Scaffolding.
Read the milestone requirements and begin.
Current model: Sonnet 5 | Effort: high
```
