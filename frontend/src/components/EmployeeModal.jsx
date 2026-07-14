import { useState } from 'react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'

const FIELDS = [
  ['name_en', 'Name (EN)', 'text'],
  ['name_ar', 'Name (AR)', 'text'],
  ['iqama_number', 'Iqama number', 'text'],
  ['iqama_expiry', 'Iqama expiry', 'date'],
  ['passport_expiry', 'Passport expiry', 'date'],
  ['visa_expiry', 'Visa expiry', 'date'],
  ['nationality', 'Nationality', 'text'],
  ['profession', 'Profession', 'text'],
]

export default function EmployeeModal({ mode, row, onClose, onSaved }) {
  const [form, setForm] = useState(() =>
    Object.fromEntries(FIELDS.map(([k]) => [k, row?.[k] || '']))
  )
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    setError(''); setSaving(true)
    try {
      // strip empties so backend keeps None for missing fields
      const payload = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ''))
      if (mode === 'create') await api.post('/employees', payload)
      else await api.put(`/employees/${row.id}`, payload)
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Save failed')
    } finally { setSaving(false) }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{mode === 'create' ? 'Add employee' : 'Edit employee'}</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4 py-2">
          {FIELDS.map(([key, label, type]) => (
            <div key={key} className="space-y-1">
              <Label htmlFor={key} className="text-xs">{label}</Label>
              <Input id={key} type={type} value={form[key]}
                onChange={e => setForm({ ...form, [key]: e.target.value })} />
            </div>
          ))}
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={saving}>{saving ? 'Saving…' : 'Save'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}