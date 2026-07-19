import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const STAT_META = [
  { key: 'total_employees', label: 'Total employees',      tone: 'text-slate-900' },
  { key: 'valid',           label: 'Valid',                tone: 'text-emerald-600' },
  { key: 'expiring_soon',   label: 'Expiring in 30 days', tone: 'text-amber-600' },
  { key: 'expired',         label: 'Expired',             tone: 'text-red-600' },
]

export default function Dashboard() {
  const { user, logout } = useAuth()
  const [data, setData]   = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/dashboard/stats')
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || 'Failed to load'))
  }, [])

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-6">
          <h1 className="text-lg font-semibold">DocFalcon</h1>
          <nav className="flex gap-4 text-sm text-slate-600 flex-1">
            <Link to="/dashboard" className="text-slate-900 font-medium">Dashboard</Link>
            <Link to="/employees" className="hover:text-slate-900">Employees</Link>
            <Link to="/upload"    className="hover:text-slate-900">Upload</Link>
            <Link to="/chat"      className="hover:text-slate-900">Chat</Link>
            <Link to="/onboard"   className="hover:text-slate-900">Onboard</Link>
          </nav>
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <span>{user?.email}</span>
            <Button variant="outline" size="sm" onClick={logout}>Sign out</Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Dashboard</h2>
          <p className="text-sm text-slate-500 mt-1">Compliance overview for your company</p>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {STAT_META.map(({ key, label, tone }) => (
            <Card key={key}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">{label}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className={`text-3xl font-semibold ${tone}`}>
                  {data ? (data[key] ?? 0) : '—'}
                </p>
              </CardContent>
            </Card>
          ))}
        </section>

        <section>
          <h3 className="text-lg font-semibold mb-3">Documents</h3>
          <Card>
            <CardContent className="p-5">
              <p className="text-sm text-slate-600">
                Total documents processed:{' '}
                <span className="font-semibold text-slate-900">{data?.total_documents ?? '—'}</span>
              </p>
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  )
}