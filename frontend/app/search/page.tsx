"use client";

import { MessageCircle, SearchIcon, Tag as TagIcon, User as UserIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ProjectSearchResult, searchProjects, searchUsers, UserSearchResult } from "@/lib/search";
import { useAuthStore } from "@/store/authStore";

const DEBOUNCE_MS = 300;

export default function SearchPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [query, setQuery] = useState("");
  const [projects, setProjects] = useState<ProjectSearchResult[]>([]);
  const [users, setUsers] = useState<UserSearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    if (!query.trim()) {
      setProjects([]);
      setUsers([]);
      return;
    }

    setIsSearching(true);
    setError(null);

    const timeoutId = setTimeout(() => {
      Promise.all([searchProjects(query), searchUsers(query)])
        .then(([projectResults, userResults]) => {
          setProjects(projectResults);
          setUsers(userResults);
        })
        .catch(() => setError("Search is temporarily unavailable - try again shortly."))
        .finally(() => setIsSearching(false));
    }, DEBOUNCE_MS);

    return () => clearTimeout(timeoutId);
  }, [query]);

  return (
    <AppShell>
      <h1 className="font-display text-2xl font-semibold text-ink dark:text-paper">Search</h1>
      <p className="mt-1 text-sm text-graphite dark:text-paper/60">
        Find projects and people across SkillSphere.
      </p>

      <div className="relative mt-6 max-w-md">
        <SearchIcon
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-graphite dark:text-paper/40"
          size={16}
        />
        <input
          type="text"
          autoFocus
          placeholder="Try 'django', 'recipe app', or a username…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="focus-ring w-full rounded border border-line py-2 pl-9 pr-3 text-sm dark:border-white/10 dark:bg-white/5 dark:text-paper"
        />
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {isSearching && <p className="mt-4 text-sm text-graphite dark:text-paper/50">Searching…</p>}

      {!isSearching && query.trim() && projects.length === 0 && users.length === 0 && !error && (
        <p className="mt-6 text-sm text-graphite dark:text-paper/50">
          Nothing matched &quot;{query}&quot;.
        </p>
      )}

      {projects.length > 0 && (
        <div className="mt-8">
          <p className="text-xs font-medium uppercase tracking-wide text-graphite dark:text-paper/50">
            Projects
          </p>
          <div className="mt-3 space-y-2">
            {projects.map((p) => (
              <div
                key={p.id}
                className="rounded border border-line bg-white p-4 dark:border-white/10 dark:bg-white/5"
              >
                <p className="text-sm font-medium text-ink dark:text-paper">{p.title}</p>
                <p className="mt-0.5 text-sm text-graphite dark:text-paper/60">{p.description}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-graphite dark:text-paper/50">
                  <span className="flex items-center gap-1">
                    <UserIcon size={12} /> {p.owner_username}
                  </span>
                  {p.tags.map((tag) => (
                    <span
                      key={tag}
                      className="flex items-center gap-1 rounded-full bg-signal_dim px-2 py-0.5 text-signal dark:bg-white/10 dark:text-paper/70"
                    >
                      <TagIcon size={10} /> {tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {users.length > 0 && (
        <div className="mt-8">
          <p className="text-xs font-medium uppercase tracking-wide text-graphite dark:text-paper/50">
            People
          </p>
          <div className="mt-3 space-y-2">
            {users.map((u) => (
              <div
                key={u.id}
                className="flex items-center justify-between rounded border border-line bg-white p-4 dark:border-white/10 dark:bg-white/5"
              >
                <div>
                  <p className="text-sm font-medium text-ink dark:text-paper">@{u.username}</p>
                  {u.bio && (
                    <p className="mt-0.5 text-sm text-graphite dark:text-paper/60">{u.bio}</p>
                  )}
                </div>
                {user && user.username !== u.username && (
                  <button
                    onClick={() => router.push(`/chat?with=${u.id}`)}
                    className="focus-ring flex items-center gap-1.5 rounded border border-line px-3 py-1.5 text-xs font-medium text-ink transition hover:border-signal hover:text-signal dark:border-white/15 dark:text-paper/70"
                  >
                    <MessageCircle size={14} />
                    Message
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </AppShell>
  );
}
