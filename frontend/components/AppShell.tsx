"use client";

import { Bell, LayoutDashboard, LogOut, Moon, Search, Sun, UploadCloud } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useDarkMode } from "@/hooks/useDarkMode";
import { logout } from "@/lib/auth";
import { fetchNotifications } from "@/lib/notifications";
import { useAuthStore } from "@/store/authStore";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: UploadCloud },
  { href: "/search", label: "Search", icon: Search },
  { href: "/notifications", label: "Notifications", icon: Bell },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isDark, toggle } = useDarkMode();
  const { user, clearSession } = useAuthStore();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!user) return;
    fetchNotifications(true)
      .then((items) => setUnreadCount(items.length))
      .catch(() => setUnreadCount(0));
  }, [user, pathname]);

  async function handleLogout() {
    await logout();
    clearSession();
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen bg-paper dark:bg-ink">
      <aside className="hidden w-56 flex-col justify-between border-r border-line px-4 py-6 dark:border-white/10 sm:flex">
        <div>
          <p className="font-display px-2 text-lg font-semibold text-ink dark:text-paper">
            SkillSphere
          </p>
          <nav className="mt-8 space-y-1">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  className={`focus-ring flex items-center gap-2 rounded px-2.5 py-2 text-sm font-medium transition ${
                    active
                      ? "bg-signal_dim text-signal dark:bg-white/10 dark:text-paper"
                      : "text-graphite hover:bg-signal_dim/60 dark:text-paper/60 dark:hover:bg-white/5"
                  }`}
                >
                  <Icon size={16} />
                  {label}
                  {label === "Notifications" && unreadCount > 0 && (
                    <span className="ml-auto rounded-full bg-signal px-1.5 py-0.5 text-[10px] font-semibold text-paper">
                      {unreadCount}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="space-y-1">
          <button
            onClick={toggle}
            className="focus-ring flex w-full items-center gap-2 rounded px-2.5 py-2 text-sm font-medium text-graphite transition hover:bg-signal_dim/60 dark:text-paper/60 dark:hover:bg-white/5"
          >
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
            {isDark ? "Light mode" : "Dark mode"}
          </button>
          <button
            onClick={handleLogout}
            className="focus-ring flex w-full items-center gap-2 rounded px-2.5 py-2 text-sm font-medium text-graphite transition hover:bg-signal_dim/60 dark:text-paper/60 dark:hover:bg-white/5"
          >
            <LogOut size={16} />
            Log out
          </button>
        </div>
      </aside>

      <main className="flex-1 px-6 py-8 sm:px-10">{children}</main>
    </div>
  );
}
