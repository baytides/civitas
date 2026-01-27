"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatDate } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface APIExecutiveOrder {
  id: number;
  document_number: string;
  executive_order_number: number | null;
  title: string;
  signing_date: string | null;
  publication_date: string;
  president: string | null;
  abstract: string | null;
}

interface TimelineEvent {
  id: string;
  date: string;
  eventType: string;
  title: string;
  description: string;
  sourceUrl?: string;
}

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

export default function TimelinePage() {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("all");

  useEffect(() => {
    async function fetchTimeline() {
      try {
        // Fetch executive orders as the primary timeline source
        const eoResponse = await fetch(`${API_BASE}/executive-orders?limit=50`);
        if (eoResponse.ok) {
          const eoData = await eoResponse.json();
          const eoEvents: TimelineEvent[] = eoData.items.map((eo: APIExecutiveOrder) => ({
            id: `eo-${eo.id}`,
            date: eo.publication_date,
            eventType: "executive_order",
            title: eo.title,
            description: eo.abstract || `Executive order published on ${eo.publication_date}`,
            sourceUrl: `/executive-orders/${eo.id}`,
          }));
          setEvents(eoEvents);
        }
      } catch (error) {
        console.error("Error fetching timeline:", error);
      }
      setLoading(false);
    }
    fetchTimeline();
  }, []);

  const filteredEvents = events.filter((event) => {
    if (filterType !== "all" && event.eventType !== filterType) return false;
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

  if (loading) {
    return (
      <div className="container py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Timeline</h1>
          <p className="text-muted-foreground">
            Track the chronological progression of policy changes
          </p>
        </div>
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="container py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Timeline</h1>
        <p className="text-muted-foreground">
          Track the chronological progression of executive actions and policy changes
        </p>
      </div>

      {/* Filters */}
      <Card className="mb-8">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <fieldset className="min-w-0 border-0 p-0 m-0">
              <legend className="text-sm font-medium mb-2 block">
                Event Type
              </legend>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Event type">
                <Button
                  variant={filterType === "all" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFilterType("all")}
                  aria-pressed={filterType === "all"}
                >
                  All
                </Button>
                {Object.entries(eventTypeConfig).map(([key, config]) => (
                  <Button
                    key={key}
                    variant={filterType === key ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterType(key)}
                    aria-pressed={filterType === key}
                  >
                    {config.label}
                  </Button>
                ))}
              </div>
            </fieldset>
          </div>
        </CardContent>
      </Card>

      {/* Timeline */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-8 top-0 bottom-0 w-px bg-border md:left-1/2" />

        {/* Events grouped by date */}
        <div className="space-y-8">
          {Object.entries(groupedEvents)
            .sort(([a], [b]) => new Date(b).getTime() - new Date(a).getTime())
            .map(([date, dateEvents]) => (
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
                {dateEvents.map((event, index) => {
                  const config = eventTypeConfig[event.eventType as keyof typeof eventTypeConfig] || eventTypeConfig.executive_order;
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
                        <Card className="border-l-4 border-l-purple-500">
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
                                </div>
                                <h3 className="font-semibold mb-1 line-clamp-2">{event.title}</h3>
                                <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                                  {event.description}
                                </p>

                                {event.sourceUrl && (
                                  <Link
                                    href={event.sourceUrl}
                                    className="text-xs text-primary hover:underline"
                                  >
                                    View details →
                                  </Link>
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

        {filteredEvents.length === 0 && !loading && (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">
                No events found.
              </p>
              <Button
                variant="link"
                onClick={() => setFilterType("all")}
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
