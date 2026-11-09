import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/tutor", label: "Tutor", icon: "M4 5h16v11H9l-5 4V5z" },
  { to: "/roadmap", label: "Roadmap", icon: "M5 4v16M5 6h11l-2 3 2 3H5" },
];

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <svg viewBox="0 0 32 32" className="size-9 shrink-0" aria-hidden="true">
        <rect width="32" height="32" rx="8" fill="#0f5c63" />
        <path d="M8 22 16 8l8 14-8-4z" fill="#f4f7f6" />
      </svg>
      <div className="leading-tight">
        <p className="font-serif text-lg font-semibold">SkillPilot</p>
        <p className="text-xs text-muted">Learn with an AI tutor and a plan</p>
      </div>
    </div>
  );
}

function NavItems({ orientation }: { orientation: "side" | "top" }) {
  return (
    <>
      {links.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          className={({ isActive }) =>
            `flex min-h-11 items-center gap-2.5 rounded-lg px-3 text-sm font-semibold transition-colors ${
              orientation === "top" ? "flex-1 justify-center" : ""
            } ${isActive ? "bg-brand text-white" : "text-ink hover:bg-brand-soft"}`
          }
        >
          <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d={l.icon} />
          </svg>
          {l.label}
        </NavLink>
      ))}
    </>
  );
}

export default function AppShell() {
  return (
    <div className="flex h-dvh flex-col md:flex-row">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2 focus:shadow">
        Skip to content
      </a>

      {/* Tablet/desktop sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col gap-8 border-r border-line bg-surface px-4 py-6 md:flex ">
        <Logo />
        <nav aria-label="Main" className="flex flex-col gap-1">
          <NavItems orientation="side" />
        </nav>
      </aside>

      {/* Mobile header */}
      <header className="border-b border-line bg-surface px-4 pb-3 pt-4 md:hidden">
        <Logo />
        <nav aria-label="Main" className="mt-3 flex gap-2">
          <NavItems orientation="top" />
        </nav>
      </header>

      <main id="main" className="min-h-0 min-w-0 flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
