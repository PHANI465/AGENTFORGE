import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { AuthProvider, useAuth } from "./lib/auth"
import { Layout } from "./components/Layout"
import { SignIn } from "./pages/SignIn"
import { AgentCatalog } from "./pages/AgentCatalog"
import { AgentDetail } from "./pages/AgentDetail"
import { TraceViewer } from "./pages/TraceViewer"
import { EvalResults } from "./pages/EvalResults"
import { EvalSuiteDetail } from "./pages/EvalSuiteDetail"
import { Analytics } from "./pages/Analytics"
import { Settings } from "./pages/Settings"

function Gate() {
  const { apiKey } = useAuth()
  if (!apiKey) return <SignIn />

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/agents" replace />} />
        <Route path="/agents" element={<AgentCatalog />} />
        <Route path="/agents/:agentId" element={<AgentDetail />} />
        <Route path="/runs/:runId/trace" element={<TraceViewer />} />
        <Route path="/evals" element={<EvalResults />} />
        <Route path="/evals/:suiteId" element={<EvalSuiteDetail />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/agents" replace />} />
      </Route>
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
