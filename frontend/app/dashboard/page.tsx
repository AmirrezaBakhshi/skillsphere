"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AppShell } from "@/components/AppShell";
import { fetchMyDashboard, UserDashboard } from "@/lib/dashboard";
import { useAuthStore } from "@/store/authStore";

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded border border-line bg-white p-5 dark:border-white/10 dark:bg-white/5">
      <p className="text-xs font-medium uppercase tracking-wide text-graphite dark:text-paper/50">
        {label}
      </p>
      <p className="font-display mt-1 text-2xl font-semibold text-ink dark:text-paper">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [stats, setStats] = useState<UserDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      router.replace("/login");
      return;
    }
    fetchMyDashboard()
      .then(setStats)
      .catch(() => setError("Couldn't load your dashboard right now."));
  }, [user, router]);

  if (!user) return null;

  return (
    <AppShell>
      <h1 className="font-display text-2xl font-semibold text-ink dark:text-paper">
        Welcome back, {user.username}
      </h1>
      <p className="mt-1 text-sm text-graphite dark:text-paper/60">
        Here&apos;s what&apos;s happening with your projects.
      </p>

      {error && <p className="mt-6 text-sm text-red-600">{error}</p>}

      {stats && (
        <>
          <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Total projects" value={stats.total_projects} />
            <StatCard label="Ready" value={stats.projects_ready} />
            <StatCard label="Processing" value={stats.projects_processing} />
            <StatCard label="Downloads" value={stats.total_downloads} />
          </div>

          <div className="mt-8 rounded border border-line bg-white p-5 dark:border-white/10 dark:bg-white/5">
            <p className="text-sm font-medium text-ink dark:text-paper">
              Your activity, last 14 days
            </p>
            <div className="mt-4 h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={stats.activity_last_14_days}>
                  <XAxis
                    dataKey="date"
                    tickFormatter={(d: string) => d.slice(5)}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={28} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#2F6F5E" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {stats.unread_notifications > 0 && (
            <p className="mt-6 text-sm text-graphite dark:text-paper/60">
              You have {stats.unread_notifications} unread notification
              {stats.unread_notifications === 1 ? "" : "s"}.
            </p>
          )}
        </>
      )}
    </AppShell>
  );
}
