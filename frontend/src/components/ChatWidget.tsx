import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { MessageCircle, Send, X } from "lucide-react";
import { API_BASE_URL } from "../api";

type ChatConfig = {
  bot_name?: string;
  welcome_message?: string;
  primary_color?: string;
  avatar_url?: string | null;
};

type ChatMessage = {
  id: string;
  role: "bot" | "user";
  text: string;
};

const FALLBACK_CONFIG: ChatConfig = {
  bot_name: "HiveRank",
  welcome_message: "Hello! How can I help you today?",
  primary_color: "#1158e5",
};

function chatApiBase() {
  const override = import.meta.env.VITE_CHATBOT_API_URL;
  if (override) return String(override).replace(/\/$/, "");
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://localhost:8003";
    }
  }
  return API_BASE_URL;
}

function nextId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [config, setConfig] = useState<ChatConfig>(FALLBACK_CONFIG);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const listRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${chatApiBase()}/chatbot/config`)
      .then(async (res) => {
        if (!res.ok) throw new Error("config");
        return res.json();
      })
      .then((data: ChatConfig) => {
        if (cancelled) return;
        setConfig({ ...FALLBACK_CONFIG, ...data });
        if (data.welcome_message) {
          setMessages([
            { id: nextId(), role: "bot", text: data.welcome_message },
          ]);
        }
      })
      .catch(() => {
        if (cancelled) return;
        setMessages([
          {
            id: nextId(),
            role: "bot",
            text: FALLBACK_CONFIG.welcome_message!,
          },
        ]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages, open, busy]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const send = async () => {
    const query = input.trim();
    if (!query || busy) return;
    setInput("");
    setError("");
    setMessages((prev) => [...prev, { id: nextId(), role: "user", text: query }]);
    setBusy(true);
    try {
      const res = await fetch(`${chatApiBase()}/chatbot/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          session_id: sessionId,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Could not reach the assistant");
      }
      if (data.session_id) setSessionId(data.session_id);
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: "bot",
          text: data.answer || "I could not find an answer for that.",
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reach the assistant");
    } finally {
      setBusy(false);
    }
  };

  const accent = config.primary_color || FALLBACK_CONFIG.primary_color;
  const name = config.bot_name || FALLBACK_CONFIG.bot_name;

  return createPortal(
    <div className="hr-chat-widget">
      {open && (
        <div
          className="hr-chat-widget__panel"
          role="dialog"
          aria-label={`${name} chat`}
        >
          <header className="hr-chat-widget__head" style={{ background: accent }}>
            <div className="hr-chat-widget__identity">
              {config.avatar_url ? (
                <img src={config.avatar_url} alt="" className="hr-chat-widget__avatar" />
              ) : (
                <span className="hr-chat-widget__avatar hr-chat-widget__avatar--mark">
                  {name.slice(0, 1)}
                </span>
              )}
              <div>
                <p className="hr-chat-widget__name">{name}</p>
                <p className="hr-chat-widget__status">Online</p>
              </div>
            </div>
            <button
              type="button"
              className="hr-chat-widget__icon-btn"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
            >
              <X size={18} />
            </button>
          </header>

          <div className="hr-chat-widget__list" ref={listRef}>
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`hr-chat-widget__bubble hr-chat-widget__bubble--${msg.role}`}
              >
                {msg.text}
              </div>
            ))}
            {busy && (
              <div className="hr-chat-widget__bubble hr-chat-widget__bubble--bot">
                <span className="hr-chat-widget__dots" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </span>
              </div>
            )}
            {error && <p className="hr-chat-widget__error">{error}</p>}
          </div>

          <form
            className="hr-chat-widget__form"
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question…"
              aria-label="Message"
              disabled={busy}
            />
            <button
              type="submit"
              className="hr-chat-widget__send"
              style={{ background: accent }}
              disabled={busy || !input.trim()}
              aria-label="Send"
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      )}

      <button
        type="button"
        className="hr-chat-widget__launch"
        style={{ background: accent }}
        onClick={() => setOpen((prev) => !prev)}
        aria-label={open ? "Close chat" : `Open ${name} chat`}
        aria-expanded={open}
      >
        {open ? <X size={22} /> : <MessageCircle size={22} />}
      </button>
    </div>,
    document.body,
  );
}
