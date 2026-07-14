import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Send, FileText, Loader2, Sparkles, IdCard, StickyNote, FileSignature, Filter, ShieldCheck, Database, AlertTriangle, CheckCircle, MessageSquare } from "lucide-react";
import { api, getAccessToken } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

const DOC_TYPE_META = {
  iqama:    { label: "Iqama",    icon: IdCard,        color: "bg-blue-50 text-blue-700 border-blue-200" },
  visa:     { label: "Visa",     icon: StickyNote,    color: "bg-purple-50 text-purple-700 border-purple-200" },
  contract: { label: "Contract", icon: FileSignature, color: "bg-amber-50 text-amber-700 border-amber-200" },
};

const FILTERS = [
  { key: null,       label: "All documents" },
  { key: "iqama",    label: "Iqamas" },
  { key: "visa",     label: "Visas" },
  { key: "contract", label: "Contracts" },
];

const COMPLIANCE_TOOL_META = {
  get_expiring_documents: { label: "Checking expiring documents", color: "text-amber-600 bg-amber-50 border-amber-200" },
  get_employee_summary:   { label: "Fetching employee summary",   color: "text-blue-600 bg-blue-50 border-blue-200" },
  check_name_mismatch:    { label: "Checking name mismatches",    color: "text-purple-600 bg-purple-50 border-purple-200" },
};

const RAG_SUGGESTIONS = [
  "When does Ahmed's iqama expire?",
  "Show me all contracts with a 6-month probation",
  "What's the notice period in Mohammed's contract?",
  "Find employees whose visa expires this year",
];

const COMPLIANCE_SUGGESTIONS = [
  "Which employees have documents expiring in the next 30 days?",
  "Show me a summary for Ahmad",
  "Are there any name mismatches between iqama and contract?",
  "Who has documents expiring this week?",
];

// ─── RAG sub-components ───────────────────────────────────────────────────────

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
            <Icon className="h-3 w-3" />{meta.label}
          </span>
          {c.employee_label && <span className="text-xs font-medium text-slate-900 truncate">{c.employee_label}</span>}
        </div>
        <span className="text-[10px] font-mono text-slate-400 shrink-0">{c.src_id}</span>
      </div>
      <div className="flex flex-wrap gap-2 mb-2 text-[11px]">
        {c.iqama_number && <span className="text-slate-600"><span className="text-slate-400">ID:</span> <span className="font-mono">{c.iqama_number}</span></span>}
        {c.expiry_date  && <span className="text-slate-600"><span className="text-slate-400">Expires:</span> <span className="font-mono">{c.expiry_date}</span></span>}
        {c.score != null && <span className="text-slate-400 ml-auto font-mono">{c.score.toFixed(3)}</span>}
      </div>
      <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed">{c.snippet}</p>
    </div>
  );
}

function RagMessage({ m, onHover, hovered }) {
  if (m.role === "user") {
    return (
      <div className="flex gap-3 justify-end">
        <div className="max-w-[75%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed">{m.text}</div>
        <div className="h-8 w-8 rounded-full bg-slate-900 text-white text-xs font-semibold flex items-center justify-center shrink-0">You</div>
      </div>
    );
  }
  if (m.role === "error") {
    return (
      <div className="flex gap-3">
        <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0"><Sparkles className="h-4 w-4 text-white" /></div>
        <div className="max-w-[85%] bg-red-50 border border-red-200 text-red-700 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm">{m.text}</div>
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
              {m.citations.map((c) => <CitationCard key={c.src_id} c={c} highlighted={hovered === c.src_id} />)}
            </div>
          </div>
        )}
        {(m.tokens != null || m.cost != null) && (
          <div className="flex gap-3 mt-2 px-1">
            {m.tokens != null && <span className="text-[10px] text-slate-400 font-mono">{m.tokens} tokens</span>}
            {m.cost   != null && <span className="text-[10px] text-slate-400 font-mono">${m.cost.toFixed(6)}</span>}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Compliance sub-components ────────────────────────────────────────────────

function ComplianceMessage({ m }) {
  if (m.role === "user") {
    return (
      <div className="flex gap-3 justify-end">
        <div className="max-w-[75%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed">{m.text}</div>
        <div className="h-8 w-8 rounded-full bg-slate-900 text-white text-xs font-semibold flex items-center justify-center shrink-0">You</div>
      </div>
    );
  }
  if (m.role === "error") {
    return (
      <div className="flex gap-3">
        <div className="h-8 w-8 rounded-full bg-emerald-600 flex items-center justify-center shrink-0"><ShieldCheck className="h-4 w-4 text-white" /></div>
        <div className="max-w-[85%] bg-red-50 border border-red-200 text-red-700 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />{m.text}
        </div>
      </div>
    );
  }
  return (
    <div className="flex gap-3">
      <div className="h-8 w-8 rounded-full bg-emerald-600 flex items-center justify-center shrink-0"><ShieldCheck className="h-4 w-4 text-white" /></div>
      <div className="max-w-[85%] flex-1 space-y-2">
        {/* tool trace pills */}
        {m.tools?.map((tc, i) => {
          const meta = COMPLIANCE_TOOL_META[tc.name] || { label: tc.name, color: "text-slate-600 bg-slate-50 border-slate-200" };
          return (
            <div key={i} className={`flex items-center gap-2 text-xs font-medium border rounded-lg px-3 py-1.5 ${meta.color}`}>
              <Database className="w-3.5 h-3.5 shrink-0" />
              <span>{meta.label}</span>
              {tc.input && Object.keys(tc.input).length > 0 && (
                <span className="ml-auto font-mono opacity-60">{JSON.stringify(tc.input)}</span>
              )}
            </div>
          );
        })}
        <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-900 shadow-sm whitespace-pre-wrap leading-relaxed">
          {m.text}
        </div>
      </div>
    </div>
  );
}

// ─── Empty states ─────────────────────────────────────────────────────────────

function EmptyState({ mode, onPick }) {
  const suggestions = mode === "rag" ? RAG_SUGGESTIONS : COMPLIANCE_SUGGESTIONS;
  const icon  = mode === "rag" ? <Sparkles className="h-6 w-6 text-blue-600" /> : <ShieldCheck className="h-6 w-6 text-emerald-600" />;
  const title = mode === "rag" ? "Ask anything about your documents" : "Ask a compliance question";
  const desc  = mode === "rag"
    ? "Search across every iqama, visa, and contract. Answers come with citations."
    : "Query your employee database directly — expiry checks, name mismatches, summaries.";

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="h-14 w-14 rounded-2xl bg-white border border-slate-200 shadow-sm flex items-center justify-center mb-4">{icon}</div>
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      <p className="text-sm text-slate-500 mt-1.5 max-w-lg">{desc}</p>
      <div className="flex flex-wrap gap-2 justify-center mt-6 max-w-2xl">
        {suggestions.map((s) => (
          <button key={s} onClick={() => onPick(s)}
            className="text-xs text-slate-700 bg-white border border-slate-200 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 rounded-full px-3 py-1.5 transition shadow-sm">
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Chat() {
  const { user, logout } = useAuth();

  // mode: "rag" | "compliance"
  const [mode, setMode] = useState("rag");

  // separate message histories per mode
  const [ragMessages,        setRagMessages]        = useState([]);
  const [complianceMessages, setComplianceMessages] = useState([]);

  const [input,   setInput]   = useState("");
  const [sending, setSending] = useState(false);
  const [filter,  setFilter]  = useState(null);
  const [hovered, setHovered] = useState(null);

  // compliance SSE state — accumulated per turn
  const [streamingTools,  setStreamingTools]  = useState([]);
  const [streamingAnswer, setStreamingAnswer] = useState(null);

  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [ragMessages, complianceMessages, sending, streamingTools, streamingAnswer]);

  // switch mode — clear transient streaming state
  const switchMode = (m) => {
    setMode(m);
    setInput("");
    setStreamingTools([]);
    setStreamingAnswer(null);
  };

  // ── RAG send ──
  const sendRag = async (query) => {
    const history = ragMessages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .slice(-10)
      .map((m) => ({ role: m.role, text: m.text }));

    setRagMessages((m) => [...m, { role: "user", text: query }]);
    setSending(true);
    try {
      const r = await api.post("/chat", { query, doc_type: filter, history });
      setRagMessages((m) => [...m, {
        role: "assistant",
        text: r.data.answer,
        citations: r.data.citations || [],
        cost: r.data.cost_usd,
        tokens: r.data.tokens_used,
      }]);
    } catch (e) {
      setRagMessages((m) => [...m, { role: "error", text: e.response?.data?.detail || "Something went wrong." }]);
    } finally {
      setSending(false);
    }
  };

  // ── Compliance SSE send ──
  const sendCompliance = async (query) => {
    setComplianceMessages((m) => [...m, { role: "user", text: query }]);
    setSending(true);
    setStreamingTools([]);
    setStreamingAnswer(null);

    try {
      const token = getAccessToken();
      const res = await fetch(`${import.meta.env.VITE_API_URL}/compliance/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        credentials: "include",
        body: JSON.stringify({ query }),
      });

      if (!res.ok) throw new Error(`Server error ${res.status}`);

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      const tools   = [];
      let answer    = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const lines = decoder.decode(value).split("\n").filter((l) => l.startsWith("data:"));
        for (const line of lines) {
          const raw = line.slice(5).trim();
          if (raw === "[DONE]") break;
          const event = JSON.parse(raw);
          if (event.type === "tool") {
            tools.push(event);
            setStreamingTools([...tools]);
          }
          if (event.type === "answer") answer = event.text;
          if (event.type === "error")  answer = `Error: ${event.text}`;
        }
      }

      setComplianceMessages((m) => [...m, { role: "assistant", text: answer, tools }]);
    } catch (e) {
      setComplianceMessages((m) => [...m, { role: "error", text: e.message || "Something went wrong." }]);
    } finally {
      setSending(false);
      setStreamingTools([]);
      setStreamingAnswer(null);
    }
  };

  const send = async (overrideQuery) => {
    const query = (overrideQuery ?? input).trim();
    if (!query || sending) return;
    setInput("");
    if (mode === "rag") await sendRag(query);
    else                await sendCompliance(query);
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const messages = mode === "rag" ? ragMessages : complianceMessages;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <header className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-6">
          <h1 className="text-lg font-semibold">DocFalcon</h1>
          <nav className="flex gap-4 text-sm text-slate-600 flex-1">
            <Link to="/dashboard" className="hover:text-slate-900">Dashboard</Link>
            <Link to="/employees" className="hover:text-slate-900">Employees</Link>
            <Link to="/upload"    className="hover:text-slate-900">Upload</Link>
            <Link to="/chat"      className="text-slate-900 font-medium">Chat</Link>
            <Link to="/onboard"   className="hover:text-slate-900">Onboard</Link>
          </nav>
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <span>{user?.email}</span>
            <Button variant="outline" size="sm" onClick={logout}>Sign out</Button>
          </div>
        </div>
      </header>

      {/* Sub-header: mode toggle + doc filter */}
      <div className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between gap-6">

          {/* Mode toggle */}
          <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => switchMode("rag")}
              className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition ${mode === "rag" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
            >
              <MessageSquare className="h-3.5 w-3.5" />
              Document Chat
            </button>
            <button
              onClick={() => switchMode("compliance")}
              className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition ${mode === "compliance" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              Compliance
            </button>
          </div>

          {/* Doc-type filter — only relevant in RAG mode */}
          {mode === "rag" && (
            <div className="flex items-center gap-1.5 bg-slate-100 rounded-lg p-1">
              <Filter className="h-3.5 w-3.5 text-slate-500 ml-1.5" />
              {FILTERS.map((f) => (
                <button
                  key={f.label}
                  onClick={() => setFilter(f.key)}
                  className={`text-xs font-medium px-2.5 py-1 rounded-md transition ${filter === f.key ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          )}

          {mode === "compliance" && (
            <p className="text-xs text-slate-500">Queries your employee database directly — no document text needed.</p>
          )}
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8 space-y-5">
          {messages.length === 0 && !sending && (
            <EmptyState mode={mode} onPick={(s) => send(s)} />
          )}

          {mode === "rag"
            ? ragMessages.map((m, i) => <RagMessage key={i} m={m} onHover={setHovered} hovered={hovered} />)
            : complianceMessages.map((m, i) => <ComplianceMessage key={i} m={m} />)
          }

          {/* Streaming compliance trace */}
          {sending && mode === "compliance" && streamingTools.length > 0 && (
            <div className="flex gap-3">
              <div className="h-8 w-8 rounded-full bg-emerald-600 flex items-center justify-center shrink-0"><ShieldCheck className="h-4 w-4 text-white" /></div>
              <div className="space-y-2 flex-1 max-w-[85%]">
                {streamingTools.map((tc, i) => {
                  const meta = COMPLIANCE_TOOL_META[tc.name] || { label: tc.name, color: "text-slate-600 bg-slate-50 border-slate-200" };
                  return (
                    <div key={i} className={`flex items-center gap-2 text-xs font-medium border rounded-lg px-3 py-1.5 ${meta.color}`}>
                      <Database className="w-3.5 h-3.5 shrink-0" />{meta.label}
                      {tc.input && Object.keys(tc.input).length > 0 && (
                        <span className="ml-auto font-mono opacity-60">{JSON.stringify(tc.input)}</span>
                      )}
                    </div>
                  );
                })}
                <div className="flex items-center gap-2 text-xs text-slate-400 px-1">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />Synthesizing answer…
                </div>
              </div>
            </div>
          )}

          {/* RAG loading */}
          {sending && mode === "rag" && (
            <div className="flex gap-3">
              <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0"><Sparkles className="h-4 w-4 text-white" /></div>
              <div className="flex items-center gap-2 text-slate-500 text-sm bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-2.5 shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin" />Searching your documents…
              </div>
            </div>
          )}

          {/* Generic compliance loading (no tools yet) */}
          {sending && mode === "compliance" && streamingTools.length === 0 && (
            <div className="flex gap-3">
              <div className="h-8 w-8 rounded-full bg-emerald-600 flex items-center justify-center shrink-0"><ShieldCheck className="h-4 w-4 text-white" /></div>
              <div className="flex items-center gap-2 text-slate-500 text-sm bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-2.5 shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin" />Querying compliance data…
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="border-t bg-white">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-end gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100 transition">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={mode === "compliance" ? "Ask a compliance question…" : filter ? `Ask about ${filter}s...` : "Ask about any document..."}
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
            {mode === "rag"
              ? "Answers are grounded in your documents. Citations link to the exact source."
              : "Queries run directly against your employee database."}
          </p>
        </div>
      </div>
    </div>
  );
}