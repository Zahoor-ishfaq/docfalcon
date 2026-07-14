import axios from 'axios'

// access token held in module scope (memory only — never localStorage, XSS-safe)
let accessToken = null
export const setAccessToken = (t) => { accessToken = t }
export const clearAccessToken = () => { accessToken = null }
export const getAccessToken = () => accessToken

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

// Refresh tokens are single-use — concurrent callers must share one in-flight request
// or the loser replays a consumed token and gets 401.
let refreshing = null
export function refreshSession() {
  if (!refreshing) {
    refreshing = api
      .post('/auth/refresh')
      .then(({ data }) => {
        setAccessToken(data.access_token)
        return data.access_token
      })
      .finally(() => { refreshing = null })
  }
  return refreshing
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry && !original.url.includes('/auth/')) {
      original._retry = true
      try {
        const token = await refreshSession()
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      } catch (e) {
        clearAccessToken()
        window.location.href = '/login'
        return Promise.reject(e)
      }
    }
    return Promise.reject(error)
  }
)