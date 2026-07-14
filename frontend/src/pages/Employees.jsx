import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import EmployeeModal from '@/components/EmployeeModal'
import ConfirmDialog from '@/components/ConfirmDialog'

const STATUS_META = {
  valid:        { label: 'Valid',        cls: 'bg-emerald-100 text-emerald-700' },
  expiring_30d: { label: 'Expiring 30d', cls: 'bg-amber-100 text-amber-700' },
  expired:      { label: 'Expired',      cls: 'bg-red-100 text-red-700' },
}

export default function Employees() {
  const [rows, setRows] = useState([])
  const [status, setStatus] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)          // null | {mode:'create'} | {mode:'edit', row}
  const [toDelete, setToDelete] = useState(null)    // employee row pending deletion

  const load = async () => {
    setLoading(true); setError('')
    try {
      const params = status !== 'all' ? { status } : {}
      const { data } = await api.get('/employees', { params })
      setRows(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load')
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [status])

  const remove = async () => {
    await api.delete(`/employees/${toDelete.id}`)
    setToDelete(null)
    load()
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-6">
          <h1 className="text-lg font-semibold">DocFalcon</h1>
          <nav className="flex gap-4 text-sm text-slate-600">
            <Link to="/dashboard" className="hover:text-slate-900">Dashboard</Link>
            <Link to="/employees" className="text-slate-900 font-medium">Employees</Link>
            <Link to="/upload" className="hover:text-slate-900">Upload</Link>
            <Link to="/chat" className="hover:text-slate-900">Chat</Link>
            <Link to="/onboard" className="hover:text-slate-900">Onboard</Link>

          </nav>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold">Employees</h2>
          <Button onClick={() => setModal({ mode: 'create' })}>Add employee</Button>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-600">Filter:</span>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="valid">Valid</SelectItem>
              <SelectItem value="expiring_30d">Expiring 30d</SelectItem>
              <SelectItem value="expired">Expired</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <Card>
          <CardContent className="p-0">
            {loading ? (
              <p className="p-6 text-sm text-slate-500">Loading…</p>
            ) : rows.length === 0 ? (
              <p className="p-6 text-sm text-slate-500">No employees. Add one to get started.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-slate-500 border-b">
                  <tr>
                    <th className="px-6 py-3 font-medium">Name</th>
                    <th className="px-6 py-3 font-medium">Iqama</th>
                    <th className="px-6 py-3 font-medium">Iqama expiry</th>
                    <th className="px-6 py-3 font-medium">Status</th>
                    <th className="px-6 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(r => {
                    const s = STATUS_META[r.status] || { label: r.status, cls: 'bg-slate-100 text-slate-700' }
                    return (
                      <tr key={r.id} className="border-b last:border-0">
                        <td className="px-6 py-3">{r.name_en || '—'}</td>
                        <td className="px-6 py-3">{r.iqama_number || '—'}</td>
                        <td className="px-6 py-3">{r.iqama_expiry || '—'}</td>
                        <td className="px-6 py-3">
                          <Badge className={s.cls}>{s.label}</Badge>
                        </td>
                        <td className="px-6 py-3 text-right space-x-2">
                          <Button variant="outline" size="sm" onClick={() => setModal({ mode: 'edit', row: r })}>Edit</Button>
                          <Button variant="outline" size="sm" onClick={() => setToDelete(r)}>Delete</Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </main>

      {modal && (
        <EmployeeModal
          mode={modal.mode}
          row={modal.row}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load() }}
        />
      )}

      <ConfirmDialog
        open={!!toDelete}
        title="Delete employee?"
        description={`This will permanently remove ${toDelete?.name_en || 'this employee'}.`}
        confirmLabel="Delete"
        danger
        onConfirm={remove}
        onClose={() => setToDelete(null)}
      />
    </div>
  )
}