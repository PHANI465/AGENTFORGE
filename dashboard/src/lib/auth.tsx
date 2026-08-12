import { createContext, useContext, useState, type ReactNode } from "react"
import { getApiKey, setApiKey, clearApiKey } from "../api/client"

interface AuthContextValue {
  apiKey: string | null
  signIn: (key: string) => void
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [apiKey, setKey] = useState<string | null>(getApiKey())

  const signIn = (key: string) => {
    setApiKey(key)
    setKey(key)
  }

  const signOut = () => {
    clearApiKey()
    setKey(null)
  }

  return (
    <AuthContext.Provider value={{ apiKey, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
