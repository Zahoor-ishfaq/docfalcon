import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const STAT_META = [
  { key: 'total',        label: 'Total employees',   tone: 'text-slate-900' },
  { key: 'valid',        label: 'Valid',             tone: 'text-emerald-600' },
  { key: 'expiring_30d', label: 'Expiring in 30 days', tone: 'text-amber-600' },
  { key: 'expired',      label: 'Expired',           tone: 'text-red-600' },
]

export default function Dashboard() {
  const { user, logout } = useAuth()
  const [data, setData] = useState(null)
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
  <Link to="/upload" className="hover:text-slate-900">Upload</Link>
  <Link to="/chat" className="hover:text-slate-900">Chat</Link>
  <Link to="/onboard" className="hover:text-slate-900">Onboard</Link>
  <Link to="/compliance" className="hover:text-slate-900">Compliance</Link>
  
</nav>
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <span>{user?.email}</span>
            <Button variant="outline" size="sm" onClick={logout}>Sign out</Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        <h2 className="text-2xl font-semibold">Dashboard</h2>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {STAT_META.map(({ key, label, tone }) => (
            <Card key={key}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">{label}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className={`text-3xl font-semibold ${tone}`}>
                  {data ? data.counts[key] : '—'}
                </p>
              </CardContent>
            </Card>
          ))}
        </section>

        <section>
          <h3 className="text-lg font-semibold mb-3">Recent extractions</h3>
          <Card>
            <CardContent className="p-0">
              {!data ? (
                <p className="p-6 text-sm text-slate-500">Loading…</p>
              ) : data.recent_documents.length === 0 ? (
                <p className="p-6 text-sm text-slate-500">No documents yet. Upload one to get started.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="text-left text-slate-500 border-b">
                    <tr>
                      <th className="px-6 py-3 font-medium">Type</th>
                      <th className="px-6 py-3 font-medium">Provider</th>
                      <th className="px-6 py-3 font-medium">Cost (USD)</th>
                      <th className="px-6 py-3 font-medium">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_documents.map(d => (
                      <tr key={d._id} className="border-b last:border-0">
                        <td className="px-6 py-3 capitalize">{d.doc_type}</td>
                        <td className="px-6 py-3 capitalize">{d.llm_provider}</td>
                        <td className="px-6 py-3">${(d.cost_usd || 0).toFixed(4)}</td>
                        <td className="px-6 py-3 text-slate-500">
                          {d.created_at ? new Date(d.created_at).toLocaleString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  )
}