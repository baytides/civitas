"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

const navigation = [
  { name: "Dashboard", href: "/" },
  { name: "Tracker", href: "/tracker" },
  { name: "States", href: "/states" },
  { name: "Resistance", href: "/resistance" },
  { name: "Timeline", href: "/timeline" },
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

function useThreatLevel() {
  const [threat, setThreat] = React.useState({ label: "...", color: "bg-muted text-muted-foreground" });

  React.useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch(`${API_BASE}/objectives/stats`);
        if (!res.ok) return;
        const data = await res.json();
        const total = data.total || 0;
        const enacted = data.by_status?.enacted || 0;
        const inProgress = data.by_status?.in_progress || 0;
        const active = enacted + inProgress;
        const pct = total > 0 ? (active / total) * 100 : 0;

        if (pct >= 30) setThreat({ label: "CRITICAL", color: "bg-red-600 text-white" });
        else if (pct >= 15) setThreat({ label: "HIGH", color: "bg-orange-500 text-white" });
        else if (pct >= 5) setThreat({ label: "ELEVATED", color: "bg-yellow-500 text-black" });
        else setThreat({ label: "LOW", color: "bg-green-500 text-white" });
      } catch {
        // keep loading state on failure
      }
    }
    fetchStats();
  }, []);

  return threat;
}

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const threat = useThreatLevel();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [searchOpen, setSearchOpen] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState("");
  const searchInputRef = React.useRef<HTMLInputElement>(null);

  // Handle keyboard shortcut (Cmd+K or Ctrl+K)
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
      if (e.key === "Escape") {
        setSearchOpen(false);
        setSearchQuery("");
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Focus search input when modal opens
  React.useEffect(() => {
    if (searchOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [searchOpen]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/tracker?search=${encodeURIComponent(searchQuery.trim())}`);
      setSearchOpen(false);
      setSearchQuery("");
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center">
        {/* Logo */}
        <Link href="/" className="flex items-center space-x-2">
          <span className="text-2xl font-bold text-primary">Civitas</span>
        </Link>

        {/* Desktop Navigation */}
        <nav
          className="ml-8 hidden md:flex items-center space-x-6"
          aria-label="Primary"
        >
          {navigation.map((item) => (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "text-sm font-medium transition-colors hover:text-primary",
                pathname === item.href
                  ? "text-primary"
                  : "text-muted-foreground"
              )}
              aria-current={pathname === item.href ? "page" : undefined}
            >
              {item.name}
            </Link>
          ))}
        </nav>

        {/* Right side */}
        <div className="ml-auto flex items-center space-x-4">
          {/* Search Button */}
          <Button
            variant="outline"
            size="sm"
            className="hidden md:flex"
            type="button"
            onClick={() => setSearchOpen(true)}
          >
            <SearchIcon className="mr-2 h-4 w-4" aria-hidden="true" />
            Search...
            <kbd className="pointer-events-none ml-2 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
              <span className="text-xs">⌘</span>K
            </kbd>
          </Button>

          <ThemeToggle />

          {/* Threat Level Indicator */}
          <div className="hidden sm:flex items-center space-x-2">
            <span className="text-xs text-muted-foreground">Threat:</span>
            <span className={cn("inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold", threat.color)}>
              {threat.label}
            </span>
          </div>

          {/* Mobile menu button */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-navigation"
          >
            {mobileMenuOpen ? (
              <XIcon className="h-6 w-6" aria-hidden="true" />
            ) : (
              <MenuIcon className="h-6 w-6" aria-hidden="true" />
            )}
          </Button>
        </div>
      </div>

      {/* Mobile Navigation */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t">
          <nav
            id="mobile-navigation"
            className="container py-4 space-y-2"
            aria-label="Primary"
          >
            {navigation.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "block px-4 py-2 text-sm font-medium rounded-md transition-colors",
                  pathname === item.href
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted"
                )}
                onClick={() => setMobileMenuOpen(false)}
                aria-current={pathname === item.href ? "page" : undefined}
              >
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
      )}

      {/* Search Modal */}
      {searchOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/50"
          onClick={() => setSearchOpen(false)}
        >
          <div
            className="fixed left-1/2 top-1/4 -translate-x-1/2 w-full max-w-lg bg-background rounded-lg shadow-lg border p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <form onSubmit={handleSearch}>
              <div className="flex items-center gap-3">
                <SearchIcon className="h-5 w-5 text-muted-foreground" />
                <input
                  ref={searchInputRef}
                  type="text"
                  placeholder="Search objectives, legislation, cases..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex-1 bg-transparent outline-none text-lg"
                />
                <kbd className="hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                  ESC
                </kbd>
              </div>
            </form>
            <div className="mt-4 pt-4 border-t">
              <p className="text-xs text-muted-foreground">
                Press Enter to search the tracker, or use the filters on the tracker page for advanced search.
              </p>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

// Simple icons
type IconProps = React.SVGProps<SVGSVGElement> & { className?: string };

function SearchIcon({ className, ...props }: IconProps) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      focusable="false"
      {...props}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
      />
    </svg>
  );
}

function MenuIcon({ className, ...props }: IconProps) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      focusable="false"
      {...props}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 6h16M4 12h16M4 18h16"
      />
    </svg>
  );
}

function XIcon({ className, ...props }: IconProps) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      focusable="false"
      {...props}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
  );
}
