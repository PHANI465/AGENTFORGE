import { NavLink, Outlet } from "react-router-dom"
import { useAuth } from "../lib/auth"

const NAV_ITEMS = [
  { to: "/agents", label: "Agents", glyph: "◈" },
  { to: "/evals", label: "Evals", glyph: "◎" },
  { to: "/analytics", label: "Analytics", glyph: "▤" },
  { to: "/settings", label: "Settings", glyph: "⚙" },
]

export function Layout() {
  const { signOut } = useAuth()

  return (
    <div className="flex min-h-screen">
      <aside className="hud-scan flex w-60 shrink-0 flex-col border-r border-deck-700 bg-deck-900/60 backdrop-blur-sm">
        <div className="flex items-center gap-2.5 border-b border-deck-700 px-5 py-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-sm border border-signal/40 bg-signal/10 text-signal">
            <span className="font-display text-lg italic">A</span>
          </div>
          <div>
            <div className="font-display text-sm font-semibold tracking-tight text-deck-50">
              AgentForge
            </div>
            <div className="label !text-[9px] text-deck-500">operations deck</div>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-sm px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "border-l-2 border-signal bg-deck-800 text-deck-50"
                    : "border-l-2 border-transparent text-deck-300 hover:bg-deck-800/60 hover:text-deck-100"
                }`
              }
            >
              <span className="text-base leading-none text-signal">{item.glyph}</span>
              <span className="label !text-[11px] !font-medium !tracking-[0.08em] !normal-case">
                {item.label}
              </span>
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-deck-700 px-4 py-4">
          <div className="mb-3 flex items-center gap-2">
            <span className="status-dot-live h-1.5 w-1.5 rounded-full bg-lime" />
            <span className="label !text-[10px] text-deck-300">Gateway online</span>
          </div>
          <button
            onClick={signOut}
            className="label w-full rounded-sm border border-deck-600 px-3 py-1.5 text-left !text-[10px] text-deck-300 transition-colors hover:border-danger/50 hover:text-danger"
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="hud-scan flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
