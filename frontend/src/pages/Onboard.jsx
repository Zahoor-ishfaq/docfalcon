import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { api, getAccessToken } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  FileSearch, Cpu, Users, UserPlus, UserCheck, GitCompare,
  CheckCircle2, XCircle, Loader2, Upload, Sparkles
} from 'lucide-react'

const MAX_MB = 20

const TOOL_META = {
  classify_document: { label: 'Classify',        color: 'bg-blue-50 border-blue-200 text-blue-700',      icon: FileSearch },
  extract_document:  { label: 'Extract',         color: 'bg-purple-50 border-purple-200 text-purple-700', icon: Cpu },
  search_employees:  { label: 'Search',          color: 'bg-slate-50 border-slate-200 text-slate-700',    icon: Users },
  create_employee:   { label: 'Create employee', color: 'bg-emerald-50 border-emerald-200 text-emerald-700', icon: UserPlus },
  update_employee:   { label: 'Update employee', color: 'bg-amber-50 border-amber-200 text-amber-700',    icon: UserCheck },
  compare_names:     { label: 'Compare names',   color: 'bg-yellow-50 border-yellow-200 text-yellow-700', icon: GitCompare },
  ocr:               { label: 'OCR',             color: 'bg-red-50 border-red-200 text-red-700',          icon: XCircle },
}

export default function Onboard() {
  const { user, logout } = useAuth()
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [running, setRunning] = useState(false)
  const [events, setEvents] = useState([])
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const traceRef = useRef(null)

  const pick = (f) => {
    setError(''); setEvents([]); setSummary(null)
    if (!f) return
    if (!f.name.endsWith('.zip')) return setError('Only .zip files accepted.')
    if (f.size > MAX_MB * 1024 * 1024) return setError(`Max ${MAX_MB}MB.`)
    setFile(f)
  }

  const reset = () => { setFile(null); setEvents([]); setSummary(null); setError('') }

  const run = async () => {
    if (!file) return
    setRunning(true); setEvents([]); setSummary(null); setError('')

    // Ensure we have a fresh token — trigger axios refresh interceptor if needed
    let token = getAccessToken()
    if (!token) {
      try {
        const { data } = await api.post('/auth/refresh')
        token = data.access_token
      } catch {
        setError('Session expired — please log in again.')
        setRunning(false)
        return
      }
    }

    const fd = new FormData()
    fd.append('file', file)

    let resp
    try {
      resp = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/onboard`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        credentials: 'include',
        body: fd,
      })
    } catch (e) {
      setError('Network error — is the backend running?')
      setRunning(false)
      return
    }

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      setError(typeof err.detail === 'string' ? err.detail : `Error ${resp.status}`)
      setRunning(false)
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const evt = JSON.parse(line.slice(6))
          if (evt.type === 'summary') {
            setSummary(evt.data)
          } else if (evt.type !== 'done') {
            setEvents(prev => [...prev, evt])
            setTimeout(() => traceRef.current?.scrollTo({ top: traceRef.current.scrollHeight, behavior: 'smooth' }), 50)
          }
        } catch {}
      }
    }
    setRunning(false)
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-6">
          <h1 className="text-lg font-semibold">DocFalcon</h1>
          <nav className="flex gap-4 text-sm text-slate-600 flex-1">
            <Link to="/dashboard" className="hover:text-slate-900">Dashboard</Link>
            <Link to="/employees" className="hover:text-slate-900">Employees</Link>
            <Link to="/upload" className="hover:text-slate-900">Upload</Link>
            <Link to="/chat" className="hover:text-slate-900">Chat</Link>
            <Link to="/onboard" className="text-slate-900 font-medium">Onboard</Link>
          </nav>
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <span>{user?.email}</span>
            <Button variant="outline" size="sm" onClick={logout}>Sign out</Button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h2 className="text-2xl font-semibold">Bulk onboarding</h2>
          <p className="text-sm text-slate-500 mt-1">
            Upload a ZIP of Iqama, visa, and contract files. The agent classifies, extracts, and creates employee records automatically.
          </p>
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
                <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB · ZIP</p>
                <Button variant="outline" size="sm" onClick={reset}>Choose different file</Button>
              </div>
            ) : (
              <div className="space-y-3">
                <Upload className="w-8 h-8 text-slate-400 mx-auto" />
                <p className="text-sm text-slate-600">Drag and drop a ZIP here, or</p>
                <label className="inline-block">
                  <input type="file" accept=".zip" className="hidden" onChange={(e) => pick(e.target.files[0])} />
                  <span className="inline-flex items-center px-4 py-2 text-sm font-medium border rounded-md cursor-pointer hover:bg-slate-50">
                    Browse
                  </span>
                </label>
                <p className="text-xs text-slate-500">ZIP containing JPG, PNG, or PDF · max {MAX_MB}MB · max 20 files</p>
              </div>
            )}
          </CardContent>
        </Card>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end">
          <Button onClick={run} disabled={!file || running} className="gap-2">
            {running
              ? <><Loader2 className="w-4 h-4 animate-spin" />Running…</>
              : <><Sparkles className="w-4 h-4" />Run agent</>}
          </Button>
        </div>

        {(events.length > 0 || running) && (
          <div>
            <p className="text-sm font-medium text-slate-700 mb-2">Agent trace</p>
            <div ref={traceRef} className="bg-white border rounded-lg divide-y max-h-96 overflow-y-auto">
              {events.map((evt, i) => <TraceRow key={i} evt={evt} />)}
              {running && (
                <div className="flex items-center gap-2 px-4 py-3 text-xs text-slate-400">
                  <Loader2 className="w-3 h-3 animate-spin" /> Waiting for agent…
                </div>
              )}
            </div>
          </div>
        )}

        {summary && <SummaryCard summary={summary} />}
      </main>
    </div>
  )
}

function TraceRow({ evt }) {
  const meta = TOOL_META[evt.tool] || { label: evt.tool, color: 'bg-slate-50 border-slate-200 text-slate-700', icon: Cpu }
  const Icon = meta.icon

  if (evt.type === 'tool_start') {
    return (
      <div className="flex items-start gap-3 px-4 py-3">
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border ${meta.color} shrink-0 mt-0.5`}>
          <Icon className="w-3 h-3" />{meta.label}
        </span>
        <div className="min-w-0">
          {evt.file && <p className="text-xs text-slate-500 truncate">{evt.file}</p>}
          <p className="text-xs text-slate-400 font-mono truncate">{JSON.stringify(evt.input)}</p>
        </div>
      </div>
    )
  }

  if (evt.type === 'tool_end') {
    return (
      <div className="flex items-start gap-3 px-4 py-2 bg-slate-50">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 mt-0.5 shrink-0" />
        <p className="text-xs text-slate-500 font-mono truncate">{JSON.stringify(evt.output)}</p>
      </div>
    )
  }

  if (evt.type === 'tool_error') {
    return (
      <div className="flex items-start gap-3 px-4 py-2 bg-red-50">
        <XCircle className="w-3.5 h-3.5 text-red-500 mt-0.5 shrink-0" />
        <p className="text-xs text-red-600">{evt.error}</p>
      </div>
    )
  }

  return null
}

function SummaryCard({ summary }) {
  const flagged = summary.flagged || []
  return (
    <Card>
      <CardContent className="p-6 space-y-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
          <h3 className="text-lg font-semibold">Onboarding complete</h3>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Stat label="Processed" value={summary.processed ?? '—'} />
          <Stat label="Created" value={summary.created ?? '—'} color="text-emerald-600" />
          <Stat label="Updated" value={summary.updated ?? '—'} color="text-amber-600" />
        </div>
        {flagged.length > 0 && (
          <div className="space-y-1">
            <p className="text-sm font-medium text-slate-700">Flagged for review</p>
            {flagged.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-red-600">
                <XCircle className="w-4 h-4 shrink-0" />
                <span>File {f.file_index}: {f.reason}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Stat({ label, value, color = 'text-slate-900' }) {
  return (
    <div className="text-center p-3 bg-slate-50 rounded-lg">
      <p className={`text-2xl font-semibold ${color}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  )
}