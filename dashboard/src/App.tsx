import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { AuthProvider, useAuth } from "./lib/auth"
import { Layout } from "./components/Layout"
import { SignIn } from "./pages/SignIn"
import { SignUp } from "./pages/SignUp"
import { AuthCallback } from "./pages/AuthCallback"
import { AgentCatalog } from "./pages/AgentCatalog"
import { AgentDetail } from "./pages/AgentDetail"
import { TraceViewer } from "./pages/TraceViewer"
import { EvalResults } from "./pages/EvalResults"
import { EvalSuiteDetail } from "./pages/EvalSuiteDetail"
import { Analytics } from "./pages/Analytics"
import { Settings } from "./pages/Settings"
import { Guide } from "./pages/Guide"

function Gate() {
  const { apiKey } = useAuth()

  return (
    <Routes>
      {/* Reachable regardless of auth state — /auth/callback in particular
          is where a signed-*out* browser lands right after OAuth proves
          who the visitor is, so it can never live behind the apiKey check
          below the way every other route does. */}
      <Route path="/signin" element={apiKey ? <Navigate to="/agents" replace /> : <SignIn />} />
      <Route path="/signup" element={apiKey ? <Navigate to="/agents" replace /> : <SignUp />} />
      <Route path="/auth/callback" element={<AuthCallback />} />

      {apiKey ? (
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/agents" replace />} />
          <Route path="/guide" element={<Guide />} />
          <Route path="/agents" element={<AgentCatalog />} />
          <Route path="/agents/:agentId" element={<AgentDetail />} />
          <Route path="/runs/:runId/trace" element={<TraceViewer />} />
          <Route path="/evals" element={<EvalResults />} />
          <Route path="/evals/:suiteId" element={<EvalSuiteDetail />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/agents" replace />} />
        </Route>
      ) : (
        <Route path="*" element={<Navigate to="/signin" replace />} />
      )}
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Gate />
      </AuthProvider>
    </BrowserRouter>
  )
}
