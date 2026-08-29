import { useEffect, useRef, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../lib/auth"
import { identityApi } from "../api/client"
import { Card, ErrorState, LoadingState } from "../components/ui"

/** Where auth-service sends the browser after a successful OAuth login —
 * tokens arrive in the URL fragment (#access_token=...&refresh_token=...),
 * never the query string or a server log, since browsers don't send the
 * fragment as part of the HTTP request at all. This page's only job is to
 * pick them up, exchange the access token for a real API key, and get out
 * of the URL bar before anyone screenshots it. */
export function AuthCallback() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)
  const ranOnce = useRef(false)

  useEffect(() => {
    if (ranOnce.current) return
    ranOnce.current = true

    const params = new URLSearchParams(location.hash.replace(/^#/, ""))
    const accessToken = params.get("access_token")
    if (!accessToken) {
      setError("No access token was returned by the login provider.")
      return
    }

    identityApi
      .bootstrapFromAccessToken(accessToken)
      .then((apiKey) => {
        signIn(apiKey)
        navigate("/agents", { replace: true })
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [location.hash, signIn, navigate])

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm rise-in">
        {error ? (
          <Card>
            <ErrorState message={error} />
            <Link to="/signin" className="label mt-4 block text-center text-signal hover:underline">
              back to sign in
            </Link>
          </Card>
        ) : (
          <LoadingState />
        )}
      </div>
    </div>
  )
}
