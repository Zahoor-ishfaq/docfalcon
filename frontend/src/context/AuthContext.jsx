import { createContext, useContext, useEffect, useState } from 'react'
import { api, setAccessToken, clearAccessToken, refreshSession } from '@/lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  // on mount: try refresh cookie → get fresh access token (survives page reload)
  // must go through refreshSession() — tokens are single-use, so a second
  // concurrent refresh would replay a consumed jti and 401.
  useEffect(() => {
    (async () => {
      try {
        await refreshSession()
        setUser({ email: 'me' })
      } catch { /* not logged in */ }
      finally { setReady(true) }
    })()
  }, [])

  const login = async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password })
    setAccessToken(data.access_token)
    setUser(data.user || { email })
  }

  const logout = async () => {
    try { await api.post('/auth/logout') } catch {}
    clearAccessToken()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, ready, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)