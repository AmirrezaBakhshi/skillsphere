import { api } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

export type ChatMessage = {
  id: number;
  conversation_id: string;
  sender_id: string;
  sender_username: string;
  body: string;
  created_at: string;
};

export type Conversation = {
  id: string;
  participant_ids: string[];
  project_id: string | null;
  created_at: string;
  last_message: ChatMessage | null;
};

export async function startConversation(otherUserId: string): Promise<Conversation> {
  const { data } = await api.post<Conversation>("/chat/start/", { other_user_id: otherUserId });
  return data;
}

export async function fetchMyConversations(): Promise<Conversation[]> {
  const { data } = await api.get<Conversation[]>("/chat/mine/");
  return data;
}

export async function fetchMessages(conversationId: string): Promise<ChatMessage[]> {
  const { data } = await api.get<ChatMessage[]>(`/chat/${conversationId}/messages/`);
  return data;
}

/**
 * WebSockets can't send a normal Authorization header from the browser,
 * so the access token travels as a query param instead - see
 * apps/chat/infrastructure/channels/jwt_auth_middleware.py on the backend
 * for the matching half of this. This is the one place in the frontend
 * the access token leaves the Zustand store as anything other than a
 * request header; it's still never written to storage, only used
 * in-memory to build this one URL for this one connection attempt.
 */
export function buildChatSocketUrl(conversationId: string): string {
  const httpBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const wsBase = httpBase
    .replace(/^http/, "ws")
    .replace(/\/api\/v1$/, "");
  const token = useAuthStore.getState().accessToken ?? "";
  return `${wsBase}/ws/chat/${conversationId}/?token=${encodeURIComponent(token)}`;
}
