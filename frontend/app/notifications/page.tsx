"use client";

import { CheckCircle2, Info, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { fetchNotifications, markNotificationRead, Notification } from "@/lib/notifications";
import { useAuthStore } from "@/store/authStore";

const LEVEL_ICON = {
  info: Info,
  success: CheckCircle2,
  error: XCircle,
} as const;

const LEVEL_COLOR = {
  info: "text-graphite dark:text-paper/50",
  success: "text-signal",
  error: "text-red-600",
} as const;

export default function NotificationsPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);

  const load = useCallback((unreadOnly: boolean) => {
    fetchNotifications(unreadOnly).then(setNotifications).catch(() => setNotifications([]));
  }, []);

  useEffect(() => {
    if (!user) {
      router.replace("/login");
      return;
    }
    load(showUnreadOnly);
  }, [user, router, showUnreadOnly, load]);

  async function handleMarkRead(id: number) {
    await markNotificationRead(id);
    load(showUnreadOnly);
  }

  if (!user) return null;

  return (
    <AppShell>
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-semibold text-ink dark:text-paper">
          Notifications
        </h1>
        <label className="flex items-center gap-2 text-sm text-graphite dark:text-paper/60">
          <input
            type="checkbox"
            checked={showUnreadOnly}
            onChange={(e) => setShowUnreadOnly(e.target.checked)}
          />
          Unread only
        </label>
      </div>

      <div className="mt-6 space-y-2">
        {notifications.map((n) => {
          const Icon = LEVEL_ICON[n.level];
          return (
            <div
              key={n.id}
              className={`flex items-start gap-3 rounded border border-line bg-white p-4 dark:border-white/10 dark:bg-white/5 ${
                n.is_read ? "opacity-60" : ""
              }`}
            >
              <Icon className={`mt-0.5 shrink-0 ${LEVEL_COLOR[n.level]}`} size={18} />
              <div className="flex-1">
                <p className="text-sm text-ink dark:text-paper">{n.message}</p>
                <p className="mt-0.5 text-xs text-graphite dark:text-paper/50">
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
              {!n.is_read && (
                <button
                  onClick={() => handleMarkRead(n.id)}
                  className="focus-ring shrink-0 rounded border border-line px-2.5 py-1 text-xs font-medium text-ink transition hover:border-signal hover:text-signal dark:border-white/15 dark:text-paper/70"
                >
                  Mark read
                </button>
              )}
            </div>
          );
        })}

        {notifications.length === 0 && (
          <p className="text-sm text-graphite dark:text-paper/50">
            {showUnreadOnly ? "No unread notifications." : "Nothing here yet."}
          </p>
        )}
      </div>
    </AppShell>
  );
}
