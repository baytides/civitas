"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatDate, snakeToTitle } from "@/lib/utils";

// Mock data
const mockTimelineEvents = [
  {
    id: "1",
    date: "2025-01-26",
    eventType: "executive_order",
    title: "Executive Order on Federal Workforce Restructuring",
    description:
      "President signs executive order directing review of all federal agencies for potential consolidation and workforce reduction.",
    relatedObjectives: ["gov-1", "ed-1"],
    threatLevel: "critical",
    sourceUrl: "#",
  },
  {
    id: "2",
    date: "2025-01-25",
    eventType: "court_case",
    title: "Ninth Circuit Grants Emergency Stay",
    description:
      "Appeals court blocks implementation of immigration enforcement expansion pending full review.",
    relatedObjectives: ["imm-1"],
    threatLevel: "moderate",
    sourceUrl: "#",
  },
  {
    id: "3",
    date: "2025-01-24",
    eventType: "legislation",
    title: "H.R. 1234 Passes Committee",
    description:
      "Federal Agency Accountability Act advances to full House floor vote, would eliminate key oversight requirements.",
    relatedObjectives: ["gov-1"],
    threatLevel: "high",
    sourceUrl: "#",
  },
  {
    id: "4",
    date: "2025-01-23",
    eventType: "executive_order",
    title: "DEI Programs Elimination Order",
    description:
      "Executive order requires termination of all federal diversity, equity, and inclusion programs within 60 days.",
    relatedObjectives: ["cr-1"],
    threatLevel: "critical",
    sourceUrl: "#",
  },
  {
    id: "5",
    date: "2025-01-22",
    eventType: "state_action",
    title: "California Passes Sanctuary Protection Act",
    description:
      "State legislature passes comprehensive protection bill limiting state cooperation with federal immigration enforcement.",
    relatedObjectives: ["imm-1"],
    threatLevel: "moderate",
    sourceUrl: "#",
  },
  {
    id: "6",
    date: "2025-01-21",
    eventType: "appointment",
    title: "New EPA Administrator Confirmed",
    description:
      "Senate confirms new EPA administrator who has pledged to 'streamline' environmental regulations.",
    relatedObjectives: ["env-1"],
    threatLevel: "high",
    sourceUrl: "#",
  },
  {
    id: "7",
    date: "2025-01-20",
    eventType: "executive_order",
    title: "Day One Executive Orders",
    description:
      "Multiple executive orders signed on inauguration day affecting immigration, environment, and federal workforce.",
    relatedObjectives: ["imm-1", "env-1", "gov-1"],
    threatLevel: "critical",
    sourceUrl: "#",
  },
];

const eventTypeConfig = {
  executive_order: {
    icon: <PenIcon className="h-4 w-4" />,
    label: "Executive Order",
    color: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-200",
  },
  legislation: {
    icon: <DocumentIcon className="h-4 w-4" />,
    label: "Legislation",
    color: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200",
  },
  court_case: {
    icon: <ScaleIcon className="h-4 w-4" />,
    label: "Court Case",
    color: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200",
  },
  state_action: {
    icon: <MapIcon className="h-4 w-4" />,
    label: "State Action",
    color: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200",
  },
  appointment: {
    icon: <UserIcon className="h-4 w-4" />,
    label: "Appointment",
    color: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-200",
  },
};

const threatLevelColors = {
  critical: "border-l-red-500",
  high: "border-l-orange-500",
  elevated: "border-l-yellow-500",
  moderate: "border-l-green-500",
};

export default function TimelinePage() {
  const [filterType, setFilterType] = useState<string>("all");
  const [filterThreat, setFilterThreat] = useState<string>("all");

  const filteredEvents = mockTimelineEvents.filter((event) => {
    if (filterType !== "all" && event.eventType !== filterType) return false;
    if (filterThreat !== "all" && event.threatLevel !== filterThreat) return false;
    return true;
  });

  // Group events by date
  const groupedEvents = filteredEvents.reduce(
    (acc, event) => {
      const date = event.date;
      if (!acc[date]) acc[date] = [];
      acc[date].push(event);
      return acc;
    },
    {} as Record<string, typeof filteredEvents>
  );

  return (
    <div className="container py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Timeline</h1>
        <p className="text-muted-foreground">
          Track the chronological progression of Project 2025 implementation
        </p>
      </div>

      {/* Filters */}
      <Card className="mb-8">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Event Type Filter */}
            <div>
              <label className="text-sm font-medium mb-2 block">
                Event Type
              </label>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={filterType === "all" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFilterType("all")}
                >
                  All
                </Button>
                {Object.entries(eventTypeConfig).map(([key, config]) => (
                  <Button
                    key={key}
                    variant={filterType === key ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterType(key)}
                  >
                    {config.label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Threat Level Filter */}
            <div>
              <label className="text-sm font-medium mb-2 block">
                Threat Level
              </label>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={filterThreat === "all" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFilterThreat("all")}
                >
                  All
                </Button>
                <Button
                  variant={filterThreat === "critical" ? "default" : "outline"}
                  size="sm"
                  className={filterThreat === "critical" ? "bg-red-500 hover:bg-red-600" : ""}
                  onClick={() => setFilterThreat("critical")}
                >
                  Critical
                </Button>
                <Button
                  variant={filterThreat === "high" ? "default" : "outline"}
                  size="sm"
                  className={filterThreat === "high" ? "bg-orange-500 hover:bg-orange-600" : ""}
                  onClick={() => setFilterThreat("high")}
                >
                  High
                </Button>
                <Button
                  variant={filterThreat === "moderate" ? "default" : "outline"}
                  size="sm"
                  className={filterThreat === "moderate" ? "bg-green-500 hover:bg-green-600" : ""}
                  onClick={() => setFilterThreat("moderate")}
                >
                  Moderate
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Timeline */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-8 top-0 bottom-0 w-px bg-border md:left-1/2" />

        {/* Events grouped by date */}
        <div className="space-y-8">
          {Object.entries(groupedEvents).map(([date, events]) => (
            <div key={date}>
              {/* Date header */}
              <div className="relative flex items-center justify-center mb-4">
                <div className="absolute left-8 md:left-1/2 w-3 h-3 rounded-full bg-primary -translate-x-1/2" />
                <span className="relative z-10 bg-background px-4 py-1 rounded-full border text-sm font-medium">
                  {formatDate(date, { weekday: "long", month: "long", day: "numeric" })}
                </span>
              </div>

              {/* Events for this date */}
              <div className="space-y-4">
                {events.map((event, index) => {
                  const config = eventTypeConfig[event.eventType as keyof typeof eventTypeConfig];
                  const isEven = index % 2 === 0;

                  return (
                    <div
                      key={event.id}
                      className={cn(
                        "relative pl-16 md:pl-0",
                        "md:grid md:grid-cols-2 md:gap-8"
                      )}
                    >
                      {/* Card - alternating sides on desktop */}
                      <div
                        className={cn(
                          "md:col-span-1",
                          isEven ? "md:col-start-1 md:pr-8" : "md:col-start-2 md:pl-8"
                        )}
                      >
                        <Card
                          className={cn(
                            "border-l-4",
                            threatLevelColors[event.threatLevel as keyof typeof threatLevelColors]
                          )}
                        >
                          <CardContent className="pt-4">
                            <div className="flex items-start gap-3">
                              <div className={cn("p-2 rounded-lg", config.color)}>
                                {config.icon}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap mb-1">
                                  <Badge variant="outline" className="text-xs">
                                    {config.label}
                                  </Badge>
                                  <Badge
                                    variant={event.threatLevel as "critical" | "high" | "elevated" | "moderate"}
                                    className="text-xs"
                                  >
                                    {event.threatLevel.toUpperCase()}
                                  </Badge>
                                </div>
                                <h3 className="font-semibold mb-1">{event.title}</h3>
                                <p className="text-sm text-muted-foreground mb-3">
                                  {event.description}
                                </p>

                                {/* Related objectives */}
                                {event.relatedObjectives.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mb-3">
                                    {event.relatedObjectives.map((objId) => (
                                      <Link
                                        key={objId}
                                        href={`/tracker/${objId}`}
                                        className="text-xs text-primary hover:underline"
                                      >
                                        {objId}
                                      </Link>
                                    ))}
                                  </div>
                                )}

                                {event.sourceUrl && (
                                  <a
                                    href={event.sourceUrl}
                                    className="text-xs text-muted-foreground hover:text-primary"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                  >
                                    View source →
                                  </a>
                                )}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {filteredEvents.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">
                No events match your filters.
              </p>
              <Button
                variant="link"
                onClick={() => {
                  setFilterType("all");
                  setFilterThreat("all");
                }}
              >
                Clear filters
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

// Icons
function PenIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
    </svg>
  );
}

function DocumentIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );
}

function ScaleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
    </svg>
  );
}

function MapIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
    </svg>
  );
}

function UserIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  );
}
