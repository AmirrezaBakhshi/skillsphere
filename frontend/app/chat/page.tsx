"use client";

import { Send } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
import {
  buildChatSocketUrl,
  ChatMessage,
  Conversation,
  fetchMessages,
  fetchMyConversations,
  startConversation,
} from "@/lib/chat";
import { useAuthStore } from "@/store/authStore";

function otherParticipantLabel(conversation: Conversation, myId: string): string {
  // We only store ids on the conversation itself (not usernames), so once
  // there are any messages the sender_username on the last message is the
  // easiest label; a brand new, message-less conversation falls back to id.
  if (conversation.last_message) {
    return conversation.last_message.sender_id === myId
      ? "You"
      : conversation.last_message.sender_username;
  }
  const otherId = conversation.participant_ids.find((id) => id !== myId);
  return otherId ? `User ${otherId.slice(0, 8)}` : "Conversation";
}

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatPageInner />
    </Suspense>
  );
}

function ChatPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuthStore();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [connectionState, setConnectionState] = useState<"connecting" | "open" | "closed">(
    "connecting"
  );

  const socketRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(() => {
    fetchMyConversations().then(setConversations).catch(() => setConversations([]));
  }, []);

  useEffect(() => {
    if (!user) {
      router.replace("/login");
      return;
    }
    loadConversations();
  }, [user, router, loadConversations]);

  // Support arriving at /chat?with=<userId> (e.g. from the search page's
  // "Message" button) by starting/finding the conversation automatically.
  useEffect(() => {
    const withUserId = searchParams.get("with");
    if (withUserId && user) {
      startConversation(withUserId).then((conversation) => {
        setActiveId(conversation.id);
        loadConversations();
      });
    }
  }, [searchParams, user, loadConversations]);

  useEffect(() => {
    if (!activeId) return;

    fetchMessages(activeId).then(setMessages).catch(() => setMessages([]));

    setConnectionState("connecting");
    const socket = new WebSocket(buildChatSocketUrl(activeId));
    socketRef.current = socket;

    socket.onopen = () => setConnectionState("open");
    socket.onclose = () => setConnectionState("closed");
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "message") {
        setMessages((prev) => [...prev, payload.message]);
      }
    };

    return () => socket.close();
  }, [activeId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim() || !socketRef.current || connectionState !== "open") return;
    socketRef.current.send(JSON.stringify({ body: draft }));
    setDraft("");
  }

  if (!user) return null;

  return (
    <AppShell>
      <h1 className="font-display text-2xl font-semibold text-ink dark:text-paper">Messages</h1>

      <div className="mt-6 flex h-[70vh] overflow-hidden rounded border border-line dark:border-white/10">
        <div className="w-64 shrink-0 overflow-y-auto border-r border-line dark:border-white/10">
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => setActiveId(c.id)}
              className={`block w-full border-b border-line px-4 py-3 text-left text-sm dark:border-white/10 ${
                activeId === c.id
                  ? "bg-signal_dim dark:bg-white/10"
                  : "hover:bg-signal_dim/50 dark:hover:bg-white/5"
              }`}
            >
              <p className="font-medium text-ink dark:text-paper">
                {otherParticipantLabel(c, user.id)}
              </p>
              {c.last_message && (
                <p className="mt-0.5 truncate text-xs text-graphite dark:text-paper/50">
                  {c.last_message.body}
                </p>
              )}
            </button>
          ))}
          {conversations.length === 0 && (
            <p className="p-4 text-sm text-graphite dark:text-paper/50">
              No conversations yet - message someone from the Search page.
            </p>
          )}
        </div>

        <div className="flex flex-1 flex-col">
          {activeId ? (
            <>
              <div className="flex-1 space-y-3 overflow-y-auto p-4">
                {messages.map((m) => {
                  const mine = m.sender_id === user.id;
                  return (
                    <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                      <div
                        className={`max-w-xs rounded px-3 py-2 text-sm ${
                          mine
                            ? "bg-signal text-paper"
                            : "bg-signal_dim text-ink dark:bg-white/10 dark:text-paper"
                        }`}
                      >
                        {!mine && (
                          <p className="mb-0.5 text-xs font-medium opacity-70">
                            {m.sender_username}
                          </p>
                        )}
                        {m.body}
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              <form
                onSubmit={handleSend}
                className="flex items-center gap-2 border-t border-line p-3 dark:border-white/10"
              >
                <input
                  type="text"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder={
                    connectionState === "open" ? "Type a message…" : "Connecting…"
                  }
                  disabled={connectionState !== "open"}
                  className="focus-ring flex-1 rounded border border-line px-3 py-2 text-sm dark:border-white/10 dark:bg-white/5 dark:text-paper"
                />
                <button
                  type="submit"
                  disabled={connectionState !== "open"}
                  className="focus-ring rounded bg-ink p-2 text-paper transition hover:bg-ink/90 disabled:opacity-50"
                  aria-label="Send"
                >
                  <Send size={16} />
                </button>
              </form>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center text-sm text-graphite dark:text-paper/50">
              Select a conversation
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
