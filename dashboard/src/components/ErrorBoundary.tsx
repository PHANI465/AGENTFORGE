import { Component, type ErrorInfo, type ReactNode } from "react"

interface Props {
  children: ReactNode
  /** Bumping this (e.g. with the router location) clears a caught error so
   * navigating away from a broken page recovers without a full reload. */
  resetKey?: string
}

interface State {
  error: Error | null
}

/**
 * Catches render/lifecycle errors from any descendant so a single broken page
 * shows a readable, recoverable card instead of white-screening the whole app.
 * React has no hook equivalent — an error boundary must be a class component.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidUpdate(prev: Props) {
    // Clear the error when the route changes so the user isn't stuck on the
    // error card after clicking away to a healthy page.
    if (this.state.error && prev.resetKey !== this.props.resetKey) {
      this.setState({ error: null })
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface it in the console for debugging; the UI stays friendly.
    console.error("Unhandled UI error:", error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="rounded-2xl border border-danger/30 bg-danger/8 px-6 py-10 text-center">
          <div className="label mb-2 text-danger">Something broke on this page</div>
          <p className="mx-auto mb-5 max-w-md text-sm text-deck-300">
            This section hit an unexpected error, but the rest of the app is fine.
            Try again, or head back to your agents.
          </p>
          <p className="mx-auto mb-6 max-w-lg break-words font-mono text-[11px] text-deck-500">
            {this.state.error.message}
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={() => this.setState({ error: null })}
              className="rounded-xl border border-deck-600 px-4 py-2 text-sm font-semibold text-deck-100 transition-colors hover:border-signal/60 hover:bg-deck-800"
            >
              Try again
            </button>
            <a
              href="/agents"
              className="rounded-xl bg-[linear-gradient(100deg,var(--color-signal),var(--color-pink))] px-4 py-2 text-sm font-semibold text-white"
            >
              Back to agents
            </a>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
