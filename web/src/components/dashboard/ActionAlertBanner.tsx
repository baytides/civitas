"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import Link from "next/link";

interface ActionAlert {
  id: string;
  title: string;
  description: string;
  urgency: "critical" | "high" | "medium";
  callToAction: {
    text: string;
    url: string;
  };
  expiresAt?: string;
}

interface ActionAlertBannerProps {
  alert: ActionAlert;
  onDismiss?: (id: string) => void;
}

const urgencyStyles = {
  critical: {
    bg: "bg-red-600",
    hover: "hover:bg-red-700",
    text: "text-white",
    icon: <AlertCircleIcon className="h-5 w-5" />,
  },
  high: {
    bg: "bg-orange-500",
    hover: "hover:bg-orange-600",
    text: "text-white",
    icon: <AlertTriangleIcon className="h-5 w-5" />,
  },
  medium: {
    bg: "bg-yellow-500",
    hover: "hover:bg-yellow-600",
    text: "text-black",
    icon: <InfoIcon className="h-5 w-5" />,
  },
};

export function ActionAlertBanner({ alert, onDismiss }: ActionAlertBannerProps) {
  const [dismissed, setDismissed] = useState(false);
  const styles = urgencyStyles[alert.urgency];

  if (dismissed) return null;

  return (
    <div className={cn("relative py-3 px-4", styles.bg, styles.text)}>
      <div className="container flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {styles.icon}
          <div>
            <p className="font-semibold">{alert.title}</p>
            <p className="text-sm opacity-90">{alert.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link href={alert.callToAction.url}>
            <Button
              variant="secondary"
              size="sm"
              className="font-semibold whitespace-nowrap"
            >
              {alert.callToAction.text}
            </Button>
          </Link>
          {onDismiss && (
            <button
              onClick={() => {
                setDismissed(true);
                onDismiss(alert.id);
              }}
              className="p-1 rounded hover:bg-white/20 transition-colors"
              aria-label="Dismiss"
            >
              <XIcon className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

interface ActionAlertStackProps {
  alerts: ActionAlert[];
  maxVisible?: number;
}

export function ActionAlertStack({
  alerts,
  maxVisible = 2,
}: ActionAlertStackProps) {
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  const visibleAlerts = alerts
    .filter((alert) => !dismissedIds.has(alert.id))
    .slice(0, maxVisible);

  const handleDismiss = (id: string) => {
    setDismissedIds((prev) => new Set([...prev, id]));
  };

  if (visibleAlerts.length === 0) return null;

  return (
    <div className="space-y-px">
      {visibleAlerts.map((alert) => (
        <ActionAlertBanner
          key={alert.id}
          alert={alert}
          onDismiss={handleDismiss}
        />
      ))}
    </div>
  );
}

// Icons
function AlertCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function AlertTriangleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  );
}

function InfoIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
  );
}
