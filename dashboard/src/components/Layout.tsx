import { NavLink, Outlet } from "react-router-dom"
import { useAuth } from "../lib/auth"

const NAV_ITEMS = [
  { to: "/guide", label: "Guide", glyph: "✦" },
  { to: "/agents", label: "Agents", glyph: "◈" },
  { to: "/evals", label: "Evals", glyph: "◎" },
  { to: "/analytics", label: "Analytics", glyph: "▤" },
  { to: "/settings", label: "Settings", glyph: "⚙" },
]

export function Layout() {
  const { signOut } = useAuth()

  return (
    <div className="flex min-h-screen">
      <aside className="hud-scan sticky top-0 flex h-screen w-64 shrink-0 flex-col border-r border-deck-700/70 bg-deck-900/50 backdrop-blur-xl">
        <div className="flex items-center gap-3 px-6 py-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[linear-gradient(135deg,var(--color-signal),var(--color-pink))] shadow-[0_8px_20px_-6px_rgba(139,92,255,0.7)]">
            <span className="font-display text-xl font-extrabold text-white">A</span>
          </div>
          <div>
            <div className="font-display text-base font-extrabold tracking-tight text-deck-50">
              AgentForge
            </div>
            <div className="label !text-[9px] text-deck-500">agent platform</div>
          </div>
        </div>

        <nav className="flex-1 space-y-1.5 px-4 py-4">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-semibold transition-all duration-200 ${
                  isActive
                    ? "bg-[linear-gradient(100deg,rgba(139,92,255,0.22),rgba(255,77,146,0.14))] text-deck-50 shadow-[inset_0_0_0_1px_rgba(139,92,255,0.35)]"
                    : "text-deck-300 hover:bg-deck-800/70 hover:text-deck-50"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={`text-lg leading-none transition-colors ${
                      isActive ? "text-signal" : "text-deck-500 group-hover:text-signal"
                    }`}
                  >
                    {item.glyph}
                  </span>
                  {item.label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="px-5 py-5">
          <div className="mb-3 flex items-center gap-2 rounded-xl border border-deck-700/70 bg-deck-800/50 px-3 py-2">
            <span className="status-dot-live h-2 w-2 rounded-full bg-lime" />
            <span className="label !text-[10px] text-deck-300">Gateway online</span>
          </div>
          <button
            onClick={signOut}
            className="w-full rounded-xl border border-deck-700 px-3 py-2 text-left font-mono text-[11px] font-semibold uppercase tracking-wider text-deck-400 transition-colors hover:border-danger/50 hover:text-danger"
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="hud-scan flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-8 py-10">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
