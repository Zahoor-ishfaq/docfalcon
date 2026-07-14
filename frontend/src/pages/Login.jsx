import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function Login() {
  const nav = useNavigate()
  const { login } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setError(''); setLoading(true)
    try {
      await login(form.email, form.password)
      nav('/dashboard')
    } catch (e) {
      setError(e.response?.data?.detail || 'Login failed')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">Sign in</CardTitle>
          <CardDescription>Welcome back to DocFalcon</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })} />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button className="w-full" onClick={submit} disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </Button>
          <p className="text-sm text-center text-slate-600">
            No account? <Link to="/register" className="text-blue-600 hover:underline">Register</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}