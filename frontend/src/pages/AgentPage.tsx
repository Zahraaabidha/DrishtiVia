import { useState, useRef, useEffect } from "react";
import { agentQuery } from "../api/client";

interface Message {
  role: "user" | "agent";
  text: string;
  ts: Date;
  source?: string;
}

const SUGGESTIONS = [
  "How many violations are there in total?",
  "Who are the repeat offenders?",
  "What is the most common violation?",
  "Show me CRITICAL violations",
  "How many violations were recorded today?",
  "Which camera has the most violations?",
  "Tell me about helmet compliance accuracy",
  "How many violations are pending review?",
];

function AgentBubble({ msg }: { msg: Message }) {
  const isAgent = msg.role === "agent";
  return (
    <div className={`flex gap-3 ${isAgent ? "" : "flex-row-reverse"}`}>
      {isAgent ? (
        <div className="w-8 h-8 rounded-full bg-neutral-900 flex items-center justify-center shrink-0 mt-0.5">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="8" r="4"/><path d="M6 20v-2a6 6 0 0 1 12 0v2"/>
          </svg>
        </div>
      ) : (
        <div className="w-8 h-8 rounded-full bg-neutral-200 flex items-center justify-center shrink-0 mt-0.5 text-[11px] font-bold text-neutral-600">TO</div>
      )}
      <div className={`max-w-[75%] rounded-[4px] px-4 py-3 text-[13px] leading-relaxed ${
        isAgent ? "bg-white border border-neutral-100 text-neutral-800" : "bg-neutral-900 text-white"
      }`}>
        {/* Render markdown-ish bold */}
        <p className="whitespace-pre-wrap" dangerouslySetInnerHTML={{
          __html: msg.text
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/`(.*?)`/g, '<code class="font-mono bg-neutral-100 text-neutral-700 px-1 rounded text-[11px]">$1</code>')
        }}/>
        <div className={`flex items-center gap-2 mt-1.5`}>
          <p className={`text-[10px] ${isAgent ? "text-neutral-400" : "text-white/50"}`}>
            {msg.ts.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </p>
          {isAgent && msg.source === "ollama" && (
            <span className="text-[9px] font-bold bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">
              Ollama LLM
            </span>
          )}
          {isAgent && !msg.source && (
            <span className="text-[9px] font-bold bg-neutral-100 text-neutral-500 px-1.5 py-0.5 rounded-full">
              Rule-based
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AgentPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "agent",
      text: "Hi! I'm the DrishtiVia AI Agent. I can answer questions about violation data in real time — plate numbers, violation counts, repeat offenders, camera hotspots, model accuracy, and more. What would you like to know?",
      ts: new Date(),
    }
  ]);
  const [input, setInput]     = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(q?: string) {
    const question = (q ?? input).trim();
    if (!question || loading) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", text: question, ts: new Date() }]);
    setLoading(true);
    try {
      const res = await agentQuery(question);
      setMessages(prev => [...prev, { role: "agent", text: res.answer, ts: new Date(), source: res.source }]);
    } catch {
      setMessages(prev => [...prev, { role: "agent", text: "Sorry, I couldn't reach the backend. Make sure the FastAPI server is running on port 8000.", ts: new Date() }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="mb-7">
        <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-1">AI Agent</p>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-900" style={{ fontFamily: "'Outfit', sans-serif" }}>
          Violation Intelligence Agent
        </h1>
        <p className="text-[13px] text-neutral-400 mt-1">
          Ask natural language questions — answered from live database data
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4" style={{ height: "calc(100vh - 220px)", minHeight: 520 }}>
        {/* Suggestions panel */}
        <div className="col-span-1 flex flex-col gap-4">
          <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
            <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-3">Suggested Questions</p>
            <div className="flex flex-col gap-1.5">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} onClick={() => send(s)} disabled={loading}
                  className="text-left px-3 py-2 rounded-[3px] bg-neutral-50 hover:bg-neutral-100 text-[12px] text-neutral-700 transition-colors disabled:opacity-50">
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* What it knows */}
          <div className="bg-neutral-900 text-white rounded-[4px] p-5">
            <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-3">What the agent knows</p>
            <div className="flex flex-col gap-2 text-[12px] text-neutral-300">
              {[
                "All violation records in the SQLite DB",
                "Plate numbers & camera locations",
                "Priority levels (CRITICAL / HIGH / MEDIUM / LOW)",
                "Operator review status (pending / confirmed)",
                "Repeat offender patterns",
                "Model accuracy & detection specs",
                "Temporal 3-of-5 confirmation logic",
              ].map((item, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-green-400 shrink-0">✓</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Chat window */}
        <div className="col-span-2 bg-white rounded-[4px] border border-neutral-100 shadow-sm flex flex-col overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-5 py-5 flex flex-col gap-4">
            {messages.map((msg, i) => <AgentBubble key={i} msg={msg}/>)}
            {loading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-neutral-900 flex items-center justify-center shrink-0">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="8" r="4"/><path d="M6 20v-2a6 6 0 0 1 12 0v2"/>
                  </svg>
                </div>
                <div className="bg-white border border-neutral-100 rounded-[4px] px-4 py-3 flex items-center gap-1.5">
                  {[0, 1, 2].map(i => (
                    <div key={i} className="w-1.5 h-1.5 rounded-full bg-neutral-400 animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }}/>
                  ))}
                </div>
              </div>
            )}
            <div ref={bottomRef}/>
          </div>

          {/* Input */}
          <div className="border-t border-neutral-100 px-4 py-3 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
              placeholder="Ask about violations, plates, hotspots, accuracy…"
              disabled={loading}
              className="flex-1 text-[13px] bg-neutral-50 border border-neutral-200 rounded-full px-4 py-2.5 outline-none focus:border-neutral-400 transition-colors disabled:opacity-50"
            />
            <button onClick={() => send()} disabled={!input.trim() || loading}
              className="w-10 h-10 rounded-full bg-neutral-900 text-white flex items-center justify-center hover:bg-neutral-700 disabled:opacity-40 transition-all shrink-0">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


