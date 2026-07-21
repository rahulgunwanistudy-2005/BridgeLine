import { BookOpenCheck, FileCheck2, Gauge, Scale, Upload } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

const navigation = [
  { to: "/upload", label: "New IEP", icon: Upload },
  { to: "/dashboard", label: "Compliance", icon: Gauge },
  { to: "/rules", label: "Rules", icon: Scale },
  { to: "/my-briefs", label: "Brief", icon: BookOpenCheck },
];

export function AppShell(): React.JSX.Element {
  return (
    <div className="min-h-screen bg-cool-mineral text-ink-green">
      <header className="sticky top-0 z-40 border-b border-deep-moss/15 bg-cool-mineral/95 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-[96rem] items-center justify-between px-4 sm:px-6 lg:px-8">
          <NavLink className="flex items-center gap-3 font-semibold" to="/">
            <span className="grid size-9 place-items-center rounded-[2px] bg-deep-moss text-paper-cream">
              <FileCheck2 aria-hidden="true" size={18} />
            </span>
            <span>Bridgeline</span>
          </NavLink>
          <nav aria-label="Primary" className="flex items-center gap-1">
            {navigation.map(({ to, label, icon: Icon }) => (
              <NavLink
                className={({ isActive }) =>
                  `inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-medium ${isActive ? "bg-deep-moss text-paper-cream" : "text-ink-green/70 hover:bg-surface"}`
                }
                key={to}
                to={to}
              >
                <Icon aria-hidden="true" size={16} />
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="hidden text-right text-xs sm:block"><p className="font-medium">Riverside Demo District</p><p className="text-ink-green/55">IEP operations</p></div>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
