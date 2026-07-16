import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { streamChat } from "../api.js";

const SAMPLE_QUESTIONS = [
  "How many filters does each of the three convolution layers use in the 1D CNN architecture diagram?",
  "Summarize this document and cite the pages you used.",
  "What diagrams or charts appear in this document, and what does each one show?",
  "Extract any numerical results or accuracy metrics mentioned, with their sources.",
  "What labels or components are shown in the technical diagrams?",
];

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
      <div className="flex items-center justify-between border-b border-slate-200 px-8 py-4">
        <h1 className="text-lg font-bold text-slate-900">Chat</h1>
        <button
          onClick={newConversation}
          className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-slate-300 hover:bg-slate-50"
        >
          New conversation
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto bg-slate-50/50 px-8 py-6">
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

      <div className="border-t border-slate-200 bg-white px-8 py-4">
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
            className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:border-accent-500 focus:ring-2 focus:ring-accent-100"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="rounded-lg bg-accent-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-accent-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {streaming ? "..." : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}

function EmptyState({ onPick }) {
  return (
    <div className="mx-auto flex h-full max-w-lg flex-col items-center justify-center text-center">
      <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-full bg-accent-100 text-accent-600">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </div>
      <h2 className="font-semibold text-slate-800">Ask about your documents</h2>
      <p className="mt-1 text-sm text-slate-500">Answers cite pages and surface the diagrams they're drawn from.</p>
      <div className="mt-6 flex w-full flex-col gap-2">
        {SAMPLE_QUESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-left text-sm text-slate-600 shadow-sm transition-colors hover:border-accent-300 hover:text-slate-900"
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
                ? "border border-rose-200 bg-rose-50 text-rose-700"
                : "border border-slate-200 bg-white text-slate-800 shadow-sm"
          }`}
        >
          {msg.content ? (
            isUser ? (
              msg.content
            ) : (
              <div className="prose prose-sm prose-slate max-w-none prose-p:my-1.5 prose-ul:my-1.5 prose-headings:my-2">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            )
          ) : (
            msg.pending && <TypingDots />
          )}
        </div>

        {msg.sources?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {msg.sources.map((s, i) => (
              <span
                key={i}
                className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-500"
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
                className="group relative overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
              >
                <span className="absolute left-1.5 top-1.5 z-10 rounded bg-black/60 px-1.5 py-0.5 text-[10px] font-medium text-white">
                  #{i + 1}
                </span>
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
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
    </span>
  );
}
