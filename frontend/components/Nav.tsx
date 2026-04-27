"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { logout } from "@/lib/api";

const navItems = [
  { href: "/decks", label: "decks", icon: "◆" },
];

export default function Nav() {
  const pathname = usePathname();
  const { isAuthenticated, onLogout } = useAuth();

  if (!isAuthenticated) return null;

  const handleLogout = () => {
    logout();
    onLogout();
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-bg-primary/95 backdrop-blur border-b border-border">
      <div className="max-w-7xl mx-auto px-4 h-12 flex items-center justify-between">
        {/* Logo / App name */}
        <Link
          href="/decks"
          className="flex items-center gap-2 text-text-primary hover:text-accent-green transition-colors"
        >
          <span className="text-accent-green font-bold">MTG</span>
          <span className="text-text-secondary text-sm hidden sm:inline">
            deck-intelligence
          </span>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-1">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-1.5 text-sm rounded transition-colors ${
                  isActive
                    ? "text-accent-green bg-accent-green/10"
                    : "text-text-secondary hover:text-text-primary hover:bg-bg-hover"
                }`}
              >
                <span className="mr-1.5">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}

          <div className="w-px h-5 bg-border mx-2" />

          <button
            onClick={handleLogout}
            className="px-3 py-1.5 text-sm text-text-muted hover:text-accent-red transition-colors"
          >
            logout
          </button>
        </div>
      </div>
    </nav>
  );
}