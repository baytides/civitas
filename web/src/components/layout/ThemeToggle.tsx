"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";

const THEME_STORAGE_KEY = "civitas-theme";

function applyTheme(isDark: boolean) {
  document.documentElement.classList.toggle("dark", isDark);
}

export function ThemeToggle() {
  const [mounted, setMounted] = React.useState(false);
  const [isDark, setIsDark] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initial = stored ? stored === "dark" : prefersDark;
    setIsDark(initial);
    applyTheme(initial);
  }, []);

  React.useEffect(() => {
    if (!mounted) return;
    applyTheme(isDark);
    window.localStorage.setItem(THEME_STORAGE_KEY, isDark ? "dark" : "light");
  }, [isDark, mounted]);

  if (!mounted) {
    return (
      <Button
        variant="ghost"
        size="icon"
        aria-label="Toggle dark mode"
        type="button"
        disabled
      >
        <MoonIcon className="h-4 w-4" aria-hidden="true" />
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      type="button"
      onClick={() => setIsDark((prev) => !prev)}
    >
      {isDark ? (
        <SunIcon className="h-4 w-4" aria-hidden="true" />
      ) : (
        <MoonIcon className="h-4 w-4" aria-hidden="true" />
      )}
    </Button>
  );
}

type IconProps = React.SVGProps<SVGSVGElement> & { className?: string };

function SunIcon({ className, ...props }: IconProps) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      focusable="false"
      {...props}
    >
      <circle cx="12" cy="12" r="4" strokeWidth={2} />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 2v2m0 16v2m10-10h-2M4 12H2m15.07-7.07-1.41 1.41M8.34 15.66l-1.41 1.41m0-10.13 1.41 1.41m8.32 8.32 1.41 1.41"
      />
    </svg>
  );
}

function MoonIcon({ className, ...props }: IconProps) {
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
        d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"
      />
    </svg>
  );
}
