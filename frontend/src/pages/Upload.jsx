import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const ACCEPTED = ['image/jpeg', 'image/png', 'application/pdf']
const MAX_MB = 5

export default function Upload() {
  const { user, logout } = useAuth()
  const [docType, setDocType] = useState('iqama')
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [mismatch, setMismatch] = useState(null) // {detected, claimed}

  const pick = (f) => {
    setError(''); setResult(null); setMismatch(null)
    if (!f) return
    if (!ACCEPTED.includes(f.type)) return setError('Only JPG, PNG, or PDF allowed.')
    if (f.size > MAX_MB * 1024 * 1024) return setError(`Max ${MAX_MB}MB.`)
    setFile(f)
  }

  const submit = async (overrideType) => {
    if (!file) return
    const type = overrideType || docType
    setBusy(true); setError(''); setResult(null); setMismatch(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const { data } = await api.post(`/extract?doc_type=${type}`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(data)
      if (overrideType) setDocType(overrideType) // keep selector in sync
    } catch (e) {
      const status = e.response?.status
      const detail = e.response?.data?.detail
      if (status === 409 && typeof detail === 'object') {
        // Classifier detected a different doc type
        setMismatch({ detected: detail.detected, claimed: detail.claimed })
      } else {
        setError(typeof detail === 'string' ? detail : 'Extraction failed')
      }
    } finally { setBusy(false) }
  }

  const reset = () => { setFile(null); setResult(null); setError(''); setMismatch(null) }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-6">
          <h1 className="text-lg font-semibold">DocFalcon</h1>
          <nav className="flex gap-4 text-sm text-slate-600 flex-1">
            <Link to="/dashboard" className="hover:text-slate-900">Dashboard</Link>
            <Link to="/employees" className="hover:text-slate-900">Employees</Link>
            <Link to="/upload" className="text-slate-900 font-medium">Upload</Link>
            <Link to="/chat" className="hover:text-slate-900">Chat</Link>
            <Link to="/onboard" className="hover:text-slate-900">Onboard</Link>
          </nav>
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <span>{user?.email}</span>
            <Button variant="outline" size="sm" onClick={logout}>Sign out</Button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        <h2 className="text-2xl font-semibold">Upload document</h2>

        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-600">Document type:</span>
          <Select value={docType} onValueChange={(v) => { setDocType(v); setMismatch(null) }}>
            <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="iqama">Iqama</SelectItem>
              <SelectItem value="visa">Visa</SelectItem>
              <SelectItem value="contract">Contract</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Card>
          <CardContent
            className={`p-10 border-2 border-dashed rounded-lg text-center transition-colors ${
              dragOver ? 'border-blue-500 bg-blue-50' : 'border-slate-300'
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); pick(e.dataTransfer.files[0]) }}
          >
            {file ? (
              <div className="space-y-2">
                <p className="text-sm font-medium">{file.name}</p>
                <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                <Button variant="outline" size="sm" onClick={reset}>Choose different file</Button>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-slate-600">Drag and drop a file here, or</p>
                <label className="inline-block">
                  <input
                    type="file"
                    accept=".jpg,.jpeg,.png,.pdf"
                    className="hidden"
                    onChange={(e) => pick(e.target.files[0])}
                  />
                  <span className="inline-flex items-center px-4 py-2 text-sm font-medium border rounded-md cursor-pointer hover:bg-slate-50">
                    Browse
                  </span>
                </label>
                <p className="text-xs text-slate-500">JPG, PNG, or PDF · max {MAX_MB}MB</p>
              </div>
            )}
          </CardContent>
        </Card>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {mismatch && (
          <div className="flex items-center gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-800 flex-1">
              This looks like a <span className="font-semibold capitalize">{mismatch.detected}</span>, not a{' '}
              <span className="font-semibold capitalize">{mismatch.claimed}</span>.
            </p>
            <Button
              size="sm"
              variant="outline"
              className="border-amber-400 text-amber-800 hover:bg-amber-100 shrink-0"
              onClick={() => submit(mismatch.detected)}
              disabled={busy}
            >
              Retry as {mismatch.detected}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="text-amber-700 shrink-0"
              onClick={() => { setMismatch(null); submit(mismatch.claimed) }}
              disabled={busy}
            >
              Keep as {mismatch.claimed}
            </Button>
          </div>
        )}

        <div className="flex justify-end">
          <Button onClick={() => submit()} disabled={!file || busy}>
            {busy ? 'Extracting…' : 'Extract'}
          </Button>
        </div>

        {result && <ResultPanel result={result} />}
      </main>
    </div>
  )
}

function ResultPanel({ result }) {
  const fields = result.fields || {}
  return (
    <Card>
      <CardContent className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Extraction result</h3>
          <div className="flex items-center gap-2">
            {result.cached && <Badge className="bg-blue-100 text-blue-700">Cached</Badge>}
            <Badge className="bg-slate-100 text-slate-700 capitalize">{result.llm_provider}</Badge>
            {typeof result.cost_usd === 'number' && (
              <Badge className="bg-slate-100 text-slate-700">${result.cost_usd.toFixed(4)}</Badge>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
          {Object.entries(fields).map(([k, v]) => (
            <div key={k} className="border-b pb-2">
              <p className="text-xs uppercase tracking-wide text-slate-500">{k.replace(/_/g, ' ')}</p>
              <p className="text-sm">{v ?? <span className="text-slate-400 italic">null</span>}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}