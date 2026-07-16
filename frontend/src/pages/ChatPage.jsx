import { useEffect, useRef, useState } from "react";
import { streamChat } from "../api.js";

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const conversationId = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async (query) => {
    if (!query.trim() || streaming) return;
    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user", content: query },
      { role: "assistant", content: "", sources: [], images: [], pending: true },
    ]);
    setStreaming(true);

    const updateAssistant = (patch) => {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        next[next.length - 1] = { ...last, ...patch };
        return next;
      });
    };

    await streamChat(
      { query, conversation_id: conversationId.current },
      {
        onMetadata: (meta) => {
          conversationId.current = meta.conversation_id;
          updateAssistant({ sources: meta.sources || [], images: meta.images || [] });
        },
        onToken: (content) => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, content: last.content + content };
            return next;
          });
        },
        onDone: () => {
          updateAssistant({ pending: false });
          setStreaming(false);
        },
        onError: (err) => {
          updateAssistant({ content: `Error: ${err.message}`, pending: false, isError: true });
          setStreaming(false);
        },
      }
    );
  };

  const newConversation = () => {
    conversationId.current = null;
    setMessages([]);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-base-800 px-8 py-4">
        <h1 className="text-lg font-bold text-white">Chat</h1>
        <button
          onClick={newConversation}
          className="rounded-lg border border-base-700 px-3 py-1.5 text-xs text-slate-400 hover:border-base-600 hover:text-slate-200"
        >
          New conversation
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 py-6">
        {messages.length === 0 ? (
          <EmptyState onPick={send} />
        ) : (
          <div className="mx-auto max-w-3xl space-y-6">
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-base-800 px-8 py-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="mx-auto flex max-w-3xl items-center gap-3"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask something about your documents..."
            className="flex-1 rounded-xl border border-base-700 bg-base-900 px-4 py-3 text-sm text-slate-200 outline-none focus:border-accent-500"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="rounded-xl bg-gradient-to-r from-accent-500 to-accent-600 px-5 py-3 text-sm font-semibold text-white shadow-glow disabled:cursor-not-allowed disabled:opacity-40"
          >
            {streaming ? "..." : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}

function EmptyState({ onPick }) {
  const samples = [
    "What is this document about?",
    "Summarize the key findings.",
    "Describe any diagrams or charts in the document.",
  ];
  return (
    <div className="mx-auto flex h-full max-w-md flex-col items-center justify-center text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-accent-500/10 text-accent-400">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </div>
      <h2 className="font-semibold text-slate-200">Ask about your documents</h2>
      <p className="mt-1 text-sm text-slate-500">Answers cite pages and surface relevant diagrams.</p>
      <div className="mt-6 flex flex-col gap-2 w-full">
        {samples.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-lg border border-base-800 bg-base-900 px-4 py-2.5 text-left text-sm text-slate-400 transition-colors hover:border-accent-500/40 hover:text-slate-200"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`animate-in flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] ${isUser ? "" : "w-full"}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-accent-600 text-white"
              : msg.isError
                ? "border border-rose-500/30 bg-rose-500/10 text-rose-300"
                : "border border-base-800 bg-base-900 text-slate-200"
          }`}
        >
          {msg.content || (msg.pending && <TypingDots />)}
          {msg.pending && msg.content && <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-accent-400 align-middle" />}
        </div>

        {msg.sources?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {msg.sources.map((s, i) => (
              <span
                key={i}
                className="rounded-full border border-base-800 bg-base-850 px-2.5 py-1 text-[11px] text-slate-400"
                title={`similarity ${s.score}`}
              >
                {s.document}
                {s.page != null ? ` · p.${s.page}` : ""}
              </span>
            ))}
          </div>
        )}

        {msg.images?.length > 0 && (
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {msg.images.map((img, i) => (
              <a
                key={i}
                href={img.url}
                target="_blank"
                rel="noreferrer"
                className="group overflow-hidden rounded-lg border border-base-800 bg-base-900"
              >
                <img src={img.url} alt={img.description || "result"} className="h-24 w-full object-cover transition-transform group-hover:scale-105" />
                <div className="truncate px-2 py-1 text-[10px] text-slate-500">
                  {img.document} · p.{img.page}
                </div>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex gap-1">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-500 [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-500 [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-500" />
    </span>
  );
}
