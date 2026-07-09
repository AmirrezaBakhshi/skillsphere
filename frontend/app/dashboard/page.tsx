"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { logout } from "@/lib/auth";
import { useAuthStore } from "@/store/authStore";

export default function DashboardPage() {
  const router = useRouter();
  const { user, clearSession } = useAuthStore();

  useEffect(() => {
    if (!user) {
      router.replace("/login");
    }
  }, [user, router]);

  if (!user) return null;

  async function handleLogout() {
    await logout();
    clearSession();
    router.push("/login");
  }

  return (
    <main className="min-h-screen bg-paper px-6 py-12">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">
              Welcome, {user.username}
            </h1>
            <p className="mt-1 text-sm text-graphite">{user.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="focus-ring rounded border border-line px-4 py-2 text-sm font-medium text-ink transition hover:border-ink"
          >
            Log out
          </button>
        </div>

        <div className="mt-10 rounded border border-line bg-white p-6 text-sm text-graphite">
          Project stats, activity charts, and uploads land here in a later stage.
        </div>
      </div>
    </main>
  );
}
