"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn, formatRelativeTime } from "@/lib/utils";
import Link from "next/link";

interface ActivityItem {
  id: string;
  type: "executive_order" | "legislation" | "court_case" | "objective";
  title: string;
  description?: string;
  date: string;
  status?: string;
  threatLevel?: "critical" | "high" | "elevated" | "moderate";
  url?: string;
}

interface RecentActivityProps {
  items: ActivityItem[];
}

const typeConfig = {
  executive_order: {
    icon: <PenIcon />,
    label: "Executive Order",
    color: "text-purple-600 bg-purple-100 dark:bg-purple-900/30",
  },
  legislation: {
    icon: <DocumentIcon />,
    label: "Legislation",
    color: "text-blue-600 bg-blue-100 dark:bg-blue-900/30",
  },
  court_case: {
    icon: <ScaleIcon />,
    label: "Court Case",
    color: "text-amber-600 bg-amber-100 dark:bg-amber-900/30",
  },
  objective: {
    icon: <TargetIcon />,
    label: "P2025 Objective",
    color: "text-red-600 bg-red-100 dark:bg-red-900/30",
  },
};

export function RecentActivity({ items }: RecentActivityProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Recent Activity</CardTitle>
        <Link
          href="/timeline"
          className="text-sm text-muted-foreground hover:text-primary"
        >
          View all →
        </Link>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {items.map((item) => {
            const config = typeConfig[item.type];
            const Wrapper = item.url ? Link : "div";

            return (
              <Wrapper
                key={item.id}
                href={item.url || "#"}
                className={cn(
                  "block p-4 rounded-lg border transition-colors",
                  item.url && "hover:bg-muted/50 cursor-pointer"
                )}
              >
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div
                    className={cn(
                      "p-2 rounded-lg shrink-0",
                      config.color
                    )}
                  >
                    {config.icon}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-muted-foreground">
                        {config.label}
                      </span>
                      {item.threatLevel && (
                        <Badge variant={item.threatLevel} className="text-xs">
                          {item.threatLevel.toUpperCase()}
                        </Badge>
                      )}
                      {item.status && (
                        <Badge
                          variant={item.status as "enacted" | "proposed" | "in_progress" | "blocked"}
                          className="text-xs"
                        >
                          {item.status.replace("_", " ").toUpperCase()}
                        </Badge>
                      )}
                    </div>
                    <h4 className="font-medium mt-1 line-clamp-1">
                      {item.title}
                    </h4>
                    {item.description && (
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                        {item.description}
                      </p>
                    )}
                  </div>

                  {/* Time */}
                  <span className="text-xs text-muted-foreground shrink-0">
                    {formatRelativeTime(item.date)}
                  </span>
                </div>
              </Wrapper>
            );
          })}

          {items.length === 0 && (
            <p className="text-center text-muted-foreground py-8">
              No recent activity
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// Icons
function PenIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
    </svg>
  );
}

function DocumentIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );
}

function ScaleIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
    </svg>
  );
}

function TargetIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  );
}
