import { useState, useRef } from "react";
import { Send, Loader2, ShieldCheck, Database, User, AlertTriangle, CheckCircle } from "lucide-react";
import { getAccessToken } from "../lib/api";

const TOOL_META = {
  get_expiring_documents:  { label: "Checking expiring documents", color: "text-amber-600 bg-amber-50 border-amber-200" },
  get_employee_summary:    { label: "Fetching employee summary",   color: "text-blue-600 bg-blue-50 border-blue-200" },
  check_name_mismatch:     { label: "Checking name mismatches",    color: "text-purple-600 bg-purple-50 border-purple-200" },
};

const SUGGESTIONS = [
  "Which employees have documents expiring in the next 30 days?",
  "Show me a summary for Ahmad Al-Rashidi",
  "Are there any name mismatches between iqama and contract?",
  "Who has documents expiring this week?",
];

export default function Compliance() {
  const [query, setQuery]     = useState("");
  const [loading, setLoading] = useState(false);
  const [toolCalls, setToolCalls] = useState([]);
  const [answer, setAnswer]   = useState(null);
  const [error, setError]     = useState(null);
  const inputRef = useRef(null);

  async function submit(q) {
    const text = (q || query).trim();
    if (!text || loading) return;

    setLoading(true);
    setQuery("");  
    setToolCalls([]);
    setAnswer(null);
    setError(null);

    try {
      const token = getAccessToken();
      const res = await fetch(`${import.meta.env.VITE_API_URL}/compliance/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        credentials: "include",
        body: JSON.stringify({ query: text }),
      });

      if (!res.ok) throw new Error(`Server error ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const lines = decoder.decode(value).split("\n").filter(l => l.startsWith("data:"));
        for (const line of lines) {
          const raw = line.slice(5).trim();
          if (raw === "[DONE]") break;
          const event = JSON.parse(raw);
          if (event.type === "tool")   setToolCalls(prev => [...prev, event]);
          if (event.type === "answer") setAnswer(event.text);
          if (event.type === "error")  setError(event.text);
        }
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <ShieldCheck className="w-5 h-5 text-blue-600" />
          <div>
            <h1 className="text-sm font-semibold text-slate-900">Compliance Assistant</h1>
            <p className="text-xs text-slate-500">Ask questions about your employees' document status</p>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">

        {/* Suggestions — only when idle */}
        {!answer && !loading && toolCalls.length === 0 && (
          <div className="space-y-3">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Try asking</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => { setQuery(s); submit(s); }}
                  className="text-left text-sm text-slate-600 bg-white border border-slate-200 rounded-lg px-4 py-3 hover:border-blue-300 hover:text-blue-700 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Tool trace */}
        {toolCalls.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Agent trace</p>
            {toolCalls.map((tc, i) => {
              const meta = TOOL_META[tc.name] || { label: tc.name, color: "text-slate-600 bg-slate-50 border-slate-200" };
              return (
                <div key={i} className={`flex items-center gap-2 text-xs font-medium border rounded-lg px-3 py-2 ${meta.color}`}>
                  <Database className="w-3.5 h-3.5 shrink-0" />
                  <span>{meta.label}</span>
                  {tc.input && Object.keys(tc.input).length > 0 && (
                    <span className="ml-auto font-mono opacity-60">{JSON.stringify(tc.input)}</span>
                  )}
                </div>
              );
            })}
            {loading && (
              <div className="flex items-center gap-2 text-xs text-slate-400 px-3 py-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Synthesizing answer…</span>
              </div>
            )}
          </div>
        )}

        {/* Answer */}
        {answer && (
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-2">
            <div className="flex items-center gap-2 text-xs font-medium text-emerald-600">
              <CheckCircle className="w-4 h-4" />
              Answer
            </div>
            <p className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed">{answer}</p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {/* Input */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm flex items-end gap-3 px-4 py-3">
          <textarea
            ref={inputRef}
            rows={1}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask a compliance question…"
            className="flex-1 resize-none text-sm text-slate-800 placeholder:text-slate-400 outline-none bg-transparent max-h-32"
          />
          <button
            onClick={() => submit()}
            disabled={!query.trim() || loading}
            className="shrink-0 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-lg p-2 transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}