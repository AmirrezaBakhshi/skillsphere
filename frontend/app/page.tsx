import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-6">
      <div className="text-center">
        <h1 className="font-display text-4xl font-semibold text-ink">SkillSphere</h1>
        <p className="mt-3 text-graphite">Build in public, learn from what others ship.</p>
        <div className="mt-8 flex justify-center gap-3">
          <Link
            href="/login"
            className="focus-ring rounded bg-ink px-5 py-2.5 text-sm font-medium text-paper transition hover:bg-ink/90"
          >
            Log in
          </Link>
          <Link
            href="/register"
            className="focus-ring rounded border border-line px-5 py-2.5 text-sm font-medium text-ink transition hover:border-ink"
          >
            Create account
          </Link>
        </div>
      </div>
    </main>
  );
}
