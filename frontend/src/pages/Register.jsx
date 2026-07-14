import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function Register() {
  const nav = useNavigate()
  const [form, setForm] = useState({ email: '', password: '', company_name: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setError(''); setLoading(true)
    try {
      await api.post('/auth/register', form)
      nav('/login')
    } catch (e) {
      setError(e.response?.data?.detail || 'Registration failed')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">Create account</CardTitle>
          <CardDescription>Start tracking your team's documents</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="company">Company name</Label>
            <Input id="company" value={form.company_name}
              onChange={e => setForm({ ...form, company_name: e.target.value })} />
          </div>
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
            {loading ? 'Creating…' : 'Create account'}
          </Button>
          <p className="text-sm text-center text-slate-600">
            Have an account? <Link to="/login" className="text-blue-600 hover:underline">Sign in</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
