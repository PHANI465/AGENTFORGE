import { useState } from "react"
import { Link } from "react-router-dom"
import { useAuth } from "../lib/auth"
import { identityApi } from "../api/client"
import { Button, Card, ErrorState, Field, Input } from "../components/ui"

export function SignUp() {
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
      const apiKey = await identityApi.signup(email.trim(), password)
      signIn(apiKey)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm rise-in">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,var(--color-signal),var(--color-pink))] shadow-[0_12px_30px_-8px_rgba(139,92,255,0.7)]">
            <span className="font-display text-3xl font-extrabold text-white">A</span>
          </div>
          <h1 className="font-display text-3xl text-deck-50">Create an account</h1>
          <p className="label mt-2 text-deck-400">start building AI agents</p>
        </div>

        <Card>
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
            <Field label="Password (min. 8 characters)">
              <Input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
            {error && <ErrorState message={error} />}
            <Button
              type="submit"
              className="w-full"
              disabled={submitting || !email.trim() || password.length < 8}
            >
              {submitting ? "Creating account…" : "Create account"}
            </Button>
          </form>
        </Card>

        <p className="label mt-4 text-center !text-[10px] text-deck-500">
          already have an account?{" "}
          <Link to="/signin" className="text-signal hover:underline">
            sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
