import type { ReactNode } from "react"
import { Link } from "react-router-dom"
import { PageHeader } from "../components/ui"

function Piece({ glyph, name, children }: { glyph: string; name: string; children: ReactNode }) {
  return (
    <div className="hud-card p-5">
      <div className="mb-2 flex items-center gap-2.5">
        <span className="text-xl text-signal">{glyph}</span>
        <span className="font-display text-lg font-bold text-deck-50">{name}</span>
      </div>
      <p className="text-sm leading-relaxed text-deck-300">{children}</p>
    </div>
  )
}

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <div className="flex gap-4">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[linear-gradient(135deg,var(--color-signal),var(--color-pink))] font-display text-base font-extrabold text-white shadow-[0_8px_20px_-8px_rgba(139,92,255,0.7)]">
        {n}
      </div>
      <div className="pt-1">
        <h3 className="font-display text-lg font-bold text-deck-50">{title}</h3>
        <p className="mt-1 text-sm leading-relaxed text-deck-300">{children}</p>
      </div>
    </div>
  )
}

export function Guide() {
  return (
    <div className="rise-in">
      <PageHeader eyebrow="Get started" title="How AgentForge works" />

      <div className="hud-card mb-8 p-6">
        <p className="text-[15px] leading-relaxed text-deck-100">
          AgentForge is a platform for building{" "}
          <span className="gradient-text font-semibold">AI agents</span> — AI that
          doesn't just chat back, but <em>does things</em>: it thinks, picks a tool,
          uses it, checks the result, and repeats until the task is done. Think of an
          agent as an <span className="text-deck-50">employee</span> you hire, brief,
          supervise, and pay — not a calculator you poke once. This platform is how you
          build those employees, prove they're safe and correct, and watch what they
          cost.
        </p>
      </div>

      <div className="label mb-3 text-signal">The pieces</div>
      <div className="mb-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Piece glyph="◈" name="Agents">
          An AI worker: its instructions (system prompt), model, tools, and safety
          rules. This is the "job description."
        </Piece>
        <Piece glyph="⚒" name="Tools">
          Abilities that reach beyond the model's frozen memory — do exact math, get
          the time, call an API. Without tools an agent can only answer from stale
          training knowledge.
        </Piece>
        <Piece glyph="⛨" name="Safety">
          Per-agent rules (e.g. "never share customer PII") enforced on every step —
          block, warn, or log. The compliance officer.
        </Piece>
        <Piece glyph="◎" name="Runs & Traces">
          Every task an agent runs is recorded step-by-step — reasoning, tool calls,
          results, timing, tokens. A full replay you can inspect.
        </Piece>
        <Piece glyph="✓" name="Evals">
          Grade an agent against test questions before it meets a real user, and
          compare versions to see if it got better.
        </Piece>
        <Piece glyph="▤" name="Cost">
          Every token and dollar is tracked per agent and per day, with per-agent
          budget caps so nothing runs away.
        </Piece>
      </div>

      <div className="label mb-4 text-signal">Try it in three steps</div>
      <div className="hud-card mb-10 space-y-6 p-6">
        <Step n={1} title="Create an agent">
          Go to <Link to="/agents" className="text-signal hover:underline">Agents</Link> →{" "}
          <span className="text-deck-100">+ New Agent</span>. Give it a name, a model
          (e.g. <code className="font-mono text-signal">gpt-4o-mini</code>), a system
          prompt like <em>"You are a helpful math tutor. Show your work."</em>, and tick
          a tool or two (calculate, get_current_time).
        </Step>
        <Step n={2} title="Test it">
          Open your agent and use the <span className="text-deck-100">Test Run</span>{" "}
          box. Try <code className="font-mono text-signal">What is 47 × 89 + 200?</code>{" "}
          (watch it use the calculate tool) or{" "}
          <code className="font-mono text-signal">What time is it?</code>. It thinks,
          picks the right tool, and answers in a few seconds.
        </Step>
        <Step n={3} title="Inspect the trace">
          Your run appears under <span className="text-deck-100">Recent Runs</span> —
          click it to see the full replay: each reasoning step, which tool it called,
          the result, plus timing, tokens, and cost. That's how you <em>see</em> it
          picked the right tool. (A run with <span className="text-deck-100">0 tool
          calls</span> answered from memory — which is why raw model knowledge can be
          outdated.)
        </Step>
      </div>

      <div className="label mb-4 text-signal">Bring your own key</div>
      <div className="hud-card mb-10 p-6">
        <p className="text-sm leading-relaxed text-deck-300">
          By default agents run on the platform's shared demo key. In{" "}
          <Link to="/settings" className="text-signal hover:underline">Settings → Use
          Your Own LLM Key</Link>, pick a provider (OpenAI, Anthropic, Google, Groq…),
          paste your key, and this session switches to your own account. Routing is by
          the <span className="text-deck-100">model name</span> — so for a Claude key,
          set your agent's model to{" "}
          <code className="font-mono text-signal">claude-3-5-sonnet-20241022</code>;
          for Gemini,{" "}
          <code className="font-mono text-signal">gemini/gemini-1.5-flash</code>. Any of
          100+ providers works this way.
        </p>
      </div>

      <div className="label mb-4 text-signal">Good to know</div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="hud-card p-5">
          <div className="mb-1 font-display font-bold text-deck-50">It's a sandbox</div>
          <p className="text-sm leading-relaxed text-deck-300">
            This public demo resets every few hours, so anything you create is
            temporary — great for trying it out, not for saving work.
          </p>
        </div>
        <div className="hud-card p-5">
          <div className="mb-1 font-display font-bold text-deck-50">Tools are a fixed set</div>
          <p className="text-sm leading-relaxed text-deck-300">
            You pick from the built-in tools per agent. User-defined custom tools are a
            planned feature, not live yet.
          </p>
        </div>
        <div className="hud-card p-5">
          <div className="mb-1 font-display font-bold text-deck-50">Safety is per agent</div>
          <p className="text-sm leading-relaxed text-deck-300">
            Each agent has its own safety rules and enforcement mode — set them on the
            agent's detail page, not globally.
          </p>
        </div>
      </div>
    </div>
  )
}
