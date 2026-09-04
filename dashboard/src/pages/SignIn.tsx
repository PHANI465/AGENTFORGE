import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { useAuth } from "../lib/auth"
import { demoApi, identityApi } from "../api/client"
import { Button, Card, ErrorState, Field, Input } from "../components/ui"

/** Shown only on a public-demo deployment (api-gateway exposes the shared
 * key at /api/v1/demo/api-key). One click signs the visitor straight in —
 * the whole point of the sandboxed demo is that this key is public. */
function DemoEntry() {
  const { signIn } = useAuth()
  const [demoKey, setDemoKey] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    demoApi.getKey().then((key) => {
      if (active) setDemoKey(key)
    })
    return () => {
      active = false
    }
  }, [])

  if (!demoKey) return null

  return (
    <>
      <Button type="button" className="w-full" onClick={() => signIn(demoKey)}>
        Try the live demo — no signup
      </Button>
      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-deck-700" />
        <span className="label text-deck-500">or sign in</span>
        <div className="h-px flex-1 bg-deck-700" />
      </div>
    </>
  )
}

function OAuthButtons() {
  return (
    <div className="space-y-2">
      <a href={identityApi.oauthLoginUrl("github")} className="block">
        <Button type="button" variant="ghost" className="w-full">
          Continue with GitHub
        </Button>
      </a>
      <a href={identityApi.oauthLoginUrl("google")} className="block">
        <Button type="button" variant="ghost" className="w-full">
          Continue with Google
        </Button>
      </a>
    </div>
  )
}

function EmailPasswordForm() {
  const { signIn } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const apiKey = await identityApi.login(email.trim(), password)
      signIn(apiKey)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field label="Email">
        <Input
          type="email"
          autoFocus
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </Field>
      <Field label="Password">
        <Input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </Field>
      {error && <ErrorState message={error} />}
      <Button type="submit" className="w-full" disabled={submitting || !email.trim() || !password}>
        {submitting ? "Signing in…" : "Sign in"}
      </Button>
    </form>
  )
}

function RawKeyForm() {
  const { signIn } = useAuth()
  const [key, setKey] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (key.trim()) signIn(key.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <Field label="X-API-Key">
        <Input
          type="password"
          placeholder="afk_…"
          value={key}
          onChange={(e) => setKey(e.target.value)}
        />
      </Field>
      <Button type="submit" variant="ghost" className="w-full" disabled={!key.trim()}>
        Enter with a raw key
      </Button>
    </form>
  )
}

export function SignIn() {
  const [showRawKey, setShowRawKey] = useState(false)

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm rise-in">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,var(--color-signal),var(--color-pink))] shadow-[0_12px_30px_-8px_rgba(139,92,255,0.7)]">
            <span className="font-display text-3xl font-extrabold text-white">A</span>
          </div>
          <h1 className="font-display text-3xl text-deck-50">AgentForge</h1>
          <p className="label mt-2 text-deck-400">build, run &amp; govern AI agents</p>
        </div>

        <Card className="space-y-5">
          <DemoEntry />
          <OAuthButtons />
          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-deck-700" />
            <span className="label text-deck-500">or</span>
            <div className="h-px flex-1 bg-deck-700" />
          </div>
          <EmailPasswordForm />
        </Card>

        <p className="label mt-4 text-center !text-[10px] text-deck-500">
          no account yet?{" "}
          <Link to="/signup" className="text-signal hover:underline">
            sign up
          </Link>
        </p>

        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={() => setShowRawKey((v) => !v)}
            className="label !text-[10px] text-deck-600 hover:text-deck-400"
          >
            {showRawKey ? "hide" : "have a raw API key instead?"}
          </button>
        </div>

        {showRawKey && (
          <Card className="mt-3">
            <RawKeyForm />
            <p className="label mt-3 !text-[10px] text-deck-500">
              run{" "}
              <code className="font-mono text-deck-300">uv run python scripts/seed.py</code> from
              the repo root to mint a dev key
            </p>
          </Card>
        )}
      </div>
    </div>
  )
}
