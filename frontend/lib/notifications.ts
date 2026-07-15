import { api } from "@/lib/api";

export type Notification = {
  id: number;
  verb: string;
  message: string;
  level: "info" | "success" | "error";
  is_read: boolean;
  created_at: string;
};

export async function fetchNotifications(unreadOnly = false): Promise<Notification[]> {
  const { data } = await api.get<Notification[]>("/notifications/", {
    params: unreadOnly ? { unread: "true" } : undefined,
  });
  return data;
}

export async function markNotificationRead(id: number): Promise<Notification> {
  const { data } = await api.post<Notification>(`/notifications/${id}/read/`);
  return data;
}
