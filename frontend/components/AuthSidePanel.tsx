const feed = [
  { who: "@marta", did: "shipped", what: "offline-first recipe app", when: "2m" },
  { who: "@devon", did: "commented on", what: "rate-limited job queue", when: "14m" },
  { who: "@priya", did: "reached", what: "Day 30 of #buildstreak", when: "1h" },
  { who: "@theo", did: "starred", what: "hexagonal Django starter", when: "3h" },
];

export function AuthSidePanel() {
  return (
    <aside className="hidden w-[380px] flex-col justify-between bg-ink px-10 py-12 text-paper lg:flex">
      <div>
        <p className="font-display text-2xl font-semibold">SkillSphere</p>
        <p className="mt-2 text-sm text-paper/60">
          A running log of what people are building right now.
        </p>
      </div>

      <ul className="space-y-6 border-l border-paper/15 pl-5">
        {feed.map((item, i) => (
          <li key={i} className="relative text-sm">
            <span className="absolute -left-[23px] top-1.5 h-2 w-2 rounded-full bg-signal" />
            <p className="text-paper/90">
              <span className="font-medium">{item.who}</span> {item.did}{" "}
              <span className="text-paper/70">{item.what}</span>
            </p>
            <p className="mt-0.5 text-xs text-paper/45">{item.when} ago</p>
          </li>
        ))}
      </ul>

      <p className="text-xs text-paper/40">
        Every project here started as someone&apos;s first commit.
      </p>
    </aside>
  );
}
