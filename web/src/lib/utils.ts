import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind CSS classes with clsx
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a date string for display
 */
export function formatDate(
  date: string | Date | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return "N/A";

  const dateObj = typeof date === "string" ? new Date(date) : date;

  return dateObj.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    ...options,
  });
}

/**
 * Format a relative time (e.g., "2 days ago")
 */
export function formatRelativeTime(date: string | Date): string {
  const dateObj = typeof date === "string" ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - dateObj.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
}

/**
 * Get threat level color classes
 */
export function getThreatLevelColor(
  level: "critical" | "high" | "elevated" | "moderate"
): string {
  const colors = {
    critical: "bg-red-500 text-white",
    high: "bg-orange-500 text-white",
    elevated: "bg-yellow-500 text-black",
    moderate: "bg-green-500 text-white",
  };
  return colors[level] || colors.moderate;
}

/**
 * Get threat level background for charts
 */
export function getThreatLevelChartColor(
  level: "critical" | "high" | "elevated" | "moderate"
): string {
  const colors = {
    critical: "#ef4444",
    high: "#f97316",
    elevated: "#eab308",
    moderate: "#22c55e",
  };
  return colors[level] || colors.moderate;
}

/**
 * Get status badge classes
 */
export function getStatusBadgeClass(status: string): string {
  const statusMap: Record<string, string> = {
    enacted: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    in_progress: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    proposed: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    blocked: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    not_started: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200",
  };
  return statusMap[status] || statusMap.not_started;
}

/**
 * Get resistance tier color
 */
export function getResistanceTierColor(tier: 1 | 2 | 3): string {
  const colors = {
    1: "bg-green-500 text-white", // Courts & States (now)
    2: "bg-yellow-500 text-black", // Congress (2026+)
    3: "bg-blue-500 text-white", // Presidency (2028+)
  };
  return colors[tier];
}

/**
 * Get protection level color for states
 */
export function getProtectionLevelColor(
  level: "strong" | "moderate" | "weak" | "hostile"
): string {
  const colors = {
    strong: "fill-green-500",
    moderate: "fill-yellow-500",
    weak: "fill-orange-500",
    hostile: "fill-red-500",
  };
  return colors[level] || colors.weak;
}

/**
 * Format a number with commas
 */
export function formatNumber(num: number): string {
  return num.toLocaleString("en-US");
}

/**
 * Format a percentage
 */
export function formatPercentage(value: number, decimals = 0): string {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + "...";
}

/**
 * Generate a slug from a string
 */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .trim();
}

/**
 * Capitalize first letter
 */
export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * Convert snake_case to Title Case
 */
export function snakeToTitle(text: string): string {
  return text
    .split("_")
    .map((word) => capitalize(word))
    .join(" ");
}

/**
 * Debounce function
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

/**
 * Check if we're on the server
 */
export const isServer = typeof window === "undefined";

/**
 * Get category icon name
 */
export function getCategoryIcon(category: string): string {
  const icons: Record<string, string> = {
    immigration: "users",
    environment: "leaf",
    healthcare: "heart",
    education: "book-open",
    civil_rights: "scale",
    labor: "briefcase",
    economy: "trending-up",
    defense: "shield",
    justice: "gavel",
    government: "building",
    executive: "user",
  };
  return icons[category.toLowerCase()] || "file";
}
