import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Send, FileText, Loader2, Sparkles, IdCard, StickyNote, FileSignature, Filter } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

const DOC_TYPE_META = {
  iqama:    { label: "Iqama",    icon: IdCard,        color: "bg-blue-50 text-blue-700 border-blue-200" },
  visa:     { label: "Visa",     icon: StickyNote,    color: "bg-purple-50 text-purple-700 border-purple-200" },
  contract: { label: "Contract", icon: FileSignature, color: "bg-amber-50 text-amber-700 border-amber-200" },
};

const FILTERS = [
  { key: null,        label: "All documents" },
  { key: "iqama",     label: "Iqamas" },
  { key: "visa",      label: "Visas" },
  { key: "contract",  label: "Contracts" },
];

const SUGGESTIONS = [
  "When does Ahmed's iqama expire?",
  "Show me all contracts with a 6-month probation",
  "What's the notice period in Mohammed's contract?",
  "Find employees whose visa expires this year",
  "Who works as a graphic designer?",
];

// Turn [src_N] tokens into interactive pills that highlight the matching citation card below.
function AnswerText({ text, citations, onHover }) {
  const parts = text.split(/(\[src_\d+\])/g);
  return (
    <span className="whitespace-pre-wrap leading-relaxed">
      {parts.map((p, i) => {
        const m = p.match(/^\[src_(\d+)\]$/);
        if (!m) return <span key={i}>{p}</span>;
        const srcId = `src_${m[1]}`;
        const citation = citations.find((c) => c.src_id === srcId);
        const meta = citation ? DOC_TYPE_META[citation.doc_type] : null;
        return (
          <button
            key={i}
            onMouseEnter={() => onHover(srcId)}
            onMouseLeave={() => onHover(null)}
            onClick={() => document.getElementById(`citation-${srcId}`)?.scrollIntoView({ behavior: "smooth", block: "center" })}
            className={`inline-flex items-center gap-1 px-1.5 py-0.5 mx-0.5 rounded text-[10px] font-mono font-semibold border transition ${meta?.color || "bg-slate-50 text-slate-700 border-slate-200"} hover:ring-2 hover:ring-offset-1 hover:ring-blue-200 cursor-pointer`}
            title={citation ? `${meta?.label || citation.doc_type} · ${citation.employee_label || "unknown"}` : srcId}
          >
            {meta ? <meta.icon className="h-3 w-3" /> : null}
            {citation?.employee_label || srcId}
          </button>
        );
      })}
    </span>
  );
}

function CitationCard({ c, highlighted }) {
  const meta = DOC_TYPE_META[c.doc_type] || { label: c.doc_type, icon: FileText, color: "bg-slate-50 text-slate-700 border-slate-200" };
  const Icon = meta.icon;
  return (
    <div
      id={`citation-${c.src_id}`}
      className={`border rounded-xl p-3.5 bg-white transition ${highlighted ? "border-blue-400 ring-2 ring-blue-100 shadow-sm" : "border-slate-200"}`}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-semibold uppercase border ${meta.color}`}>
            <Icon className="h-3 w-3" />
            {meta.label}
          </span>
          {c.employee_label && (
            <span className="text-xs font-medium text-slate-900 truncate">{c.employee_label}</span>
          )}
        </div>
        <span className="text-[10px] font-mono text-slate-400 shrink-0">{c.src_id}</span>
      </div>

      <div className="flex flex-wrap gap-2 mb-2 text-[11px]">
        {c.iqama_number && (
          <span className="text-slate-600"><span className="text-slate-400">ID:</span> <span className="font-mono">{c.iqama_number}</span></span>
        )}
        {c.expiry_date && (
          <span className="text-slate-600"><span className="text-slate-400">Expires:</span> <span className="font-mono">{c.expiry_date}</span></span>
        )}
        {c.score != null && (
          <span className="text-slate-400 ml-auto"><span className="font-mono">{c.score.toFixed(3)}</span></span>
        )}
      </div>

      <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed">{c.snippet}</p>
    </div>
  );
}

function Message({ m, onHover, hovered }) {
  if (m.role === "user") {
    return (
      <div className="flex gap-3 justify-end">
        <div className="max-w-[75%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed">
          {m.text}
        </div>
        <div className="h-8 w-8 rounded-full bg-slate-900 text-white text-xs font-semibold flex items-center justify-center shrink-0">You</div>
      </div>
    );
  }
  if (m.role === "error") {
    return (
      <div className="flex gap-3">
        <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0"><Sparkles className="h-4 w-4 text-white" /></div>
        <div className="max-w-[85%] bg-red-50 border border-red-200 text-red-700 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm">
          {m.text}
        </div>
      </div>
    );
  }
  return (
    <div className="flex gap-3">
      <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0"><Sparkles className="h-4 w-4 text-white" /></div>
      <div className="max-w-[85%] flex-1">
        <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-900 shadow-sm">
          <AnswerText text={m.text} citations={m.citations || []} onHover={onHover} />
        </div>

        {m.citations?.length > 0 && (
          <div className="mt-3">
            <div className="flex items-center gap-2 mb-2 px-1">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Sources</span>
              <span className="text-[11px] text-slate-400">({m.citations.length})</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {m.citations.map((c) => (
                <CitationCard key={c.src_id} c={c} highlighted={hovered === c.src_id} />
              ))}
            </div>
          </div>
        )}

        {(m.tokens != null || m.cost != null) && (
          <div className="flex gap-3 mt-2 px-1">
            {m.tokens != null && <span className="text-[10px] text-slate-400 font-mono">{m.tokens} tokens</span>}
            {m.cost != null && <span className="text-[10px] text-slate-400 font-mono">${m.cost.toFixed(6)}</span>}
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyState({ onPick }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="h-14 w-14 rounded-2xl bg-white border border-slate-200 shadow-sm flex items-center justify-center mb-4">
        <Sparkles className="h-6 w-6 text-blue-600" />
      </div>
      <h3 className="text-base font-semibold text-slate-900">Ask anything about your documents</h3>
      <p className="text-sm text-slate-500 mt-1.5 max-w-lg">
        Search across every iqama, visa, and contract in your company. Answers come with citations to the source document.
      </p>
      <div className="flex flex-wrap gap-2 justify-center mt-6 max-w-2xl">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="text-xs text-slate-700 bg-white border border-slate-200 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 rounded-full px-3 py-1.5 transition shadow-sm"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Chat() {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [filter, setFilter] = useState(null);      // null | 'iqama' | 'visa' | 'contract'
  const [hovered, setHovered] = useState(null);     // src_id being hovered — highlights matching card
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  const send = async (overrideQuery) => {
    const query = (overrideQuery ?? input).trim();
    if (!query || sending) return;
    if (!overrideQuery) setInput("");

    // Build history from previous non-error messages, capped to last 10
    const history = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .slice(-10)
      .map((m) => ({ role: m.role, text: m.text }));

    setMessages((m) => [...m, { role: "user", text: query }]);
    setSending(true);
    try {
      const r = await api.post("/chat", { query, doc_type: filter, history });
      setMessages((m) => [...m, {
        role: "assistant",
        text: r.data.answer,
        citations: r.data.citations || [],
        cost: r.data.cost_usd,
        tokens: r.data.tokens_used,
      }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "error", text: e.response?.data?.detail || "Something went wrong. Try again." }]);
    } finally {
      setSending(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <header className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-6">
          <h1 className="text-lg font-semibold">DocFalcon</h1>
          <nav className="flex gap-4 text-sm text-slate-600 flex-1">
            <Link to="/dashboard" className="hover:text-slate-900">Dashboard</Link>
            <Link to="/employees" className="hover:text-slate-900">Employees</Link>
            <Link to="/upload" className="hover:text-slate-900">Upload</Link>
            <Link to="/chat" className="text-slate-900 font-medium">Chat</Link>
            <Link to="/onboard" className="hover:text-slate-900">Onboard</Link>
          </nav>
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <span>{user?.email}</span>
            <Button variant="outline" size="sm" onClick={logout}>Sign out</Button>
          </div>
        </div>
      </header>

      {/* Sub-header: title + doc-type filter chips */}
      <div className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-blue-600 flex items-center justify-center shrink-0">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900 leading-tight">Ask your documents</h2>
              <p className="text-xs text-slate-500">Cross-document search across your company's HR files</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 bg-slate-100 rounded-lg p-1">
            <Filter className="h-3.5 w-3.5 text-slate-500 ml-1.5" />
            {FILTERS.map((f) => (
              <button
                key={f.label}
                onClick={() => setFilter(f.key)}
                className={`text-xs font-medium px-2.5 py-1 rounded-md transition ${
                  filter === f.key
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8 space-y-5">
          {messages.length === 0 && <EmptyState onPick={(s) => send(s)} />}
          {messages.map((m, i) => <Message key={i} m={m} onHover={setHovered} hovered={hovered} />)}
          {sending && (
            <div className="flex gap-3">
              <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0"><Sparkles className="h-4 w-4 text-white" /></div>
              <div className="flex items-center gap-2 text-slate-500 text-sm bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-2.5 shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                Searching your documents...
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t bg-white">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-end gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100 transition">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={filter ? `Ask about ${filter}s...` : "Ask about any document..."}
              disabled={sending}
              rows={1}
              className="flex-1 bg-transparent resize-none outline-none text-sm text-slate-900 placeholder:text-slate-400 py-1.5 max-h-32"
              style={{ minHeight: "1.5rem" }}
            />
            <Button size="icon" onClick={() => send()} disabled={!input.trim() || sending} className="h-8 w-8 shrink-0">
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-[11px] text-slate-400 mt-2 text-center">
            Answers are grounded in your documents. Citations link to the exact source.
          </p>
        </div>
      </div>
    </div>
  );
}