"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatDate } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const PAGE_SIZE = 50;

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

interface APICourtCase {
  id: number;
  case_name: string;
  citation: string | null;
  court: string | null;
  decision_date: string | null;
  status: string | null;
}

interface APILegislation {
  id: number;
  citation: string;
  title: string | null;
  jurisdiction: string;
  session: string;
  chamber: string;
  number: number;
  status: string | null;
  is_enacted: boolean;
  introduced_date: string | null;
  last_action_date: string | null;
  enacted_date: string | null;
}

interface TimelineEvent {
  id: string;
  date: string;
  eventType: string;
  title: string;
  description: string;
  sourceUrl?: string;
}

interface PaginationState {
  eoPage: number;
  eoTotal: number;
  casePage: number;
  caseTotal: number;
  legPage: number;
  legTotal: number;
}

const eventTypeConfig = {
  executive_order: {
    icon: <PenIcon className="h-4 w-4" />,
    label: "Executive Order",
    color:
      "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-200",
    borderColor: "border-l-purple-500",
  },
  legislation: {
    icon: <DocumentIcon className="h-4 w-4" />,
    label: "Legislation",
    color:
      "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200",
    borderColor: "border-l-blue-500",
  },
  court_case: {
    icon: <ScaleIcon className="h-4 w-4" />,
    label: "Court Case",
    color:
      "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200",
    borderColor: "border-l-amber-500",
  },
};

function toEOEvent(eo: APIExecutiveOrder): TimelineEvent | null {
  if (!eo.publication_date) return null;
  return {
    id: `eo-${eo.id}`,
    date: eo.publication_date,
    eventType: "executive_order",
    title: eo.title,
    description:
      eo.abstract || `Executive order published on ${eo.publication_date}`,
    sourceUrl: `/executive-orders/${eo.id}`,
  };
}

function toCaseEvent(c: APICourtCase): TimelineEvent | null {
  if (!c.decision_date) return null;
  return {
    id: `case-${c.id}`,
    date: c.decision_date,
    eventType: "court_case",
    title: c.case_name || c.citation || "Court case",
    description: c.citation
      ? `${c.citation}${c.court ? ` · ${c.court}` : ""}`
      : c.court || "Court case decision",
    sourceUrl: `/cases/${c.id}`,
  };
}

function toLegEvent(bill: APILegislation): TimelineEvent | null {
  const date =
    bill.last_action_date || bill.enacted_date || bill.introduced_date;
  if (!date) return null;
  const title = bill.title || bill.citation;
  const statusLabel = bill.is_enacted
    ? "Enacted"
    : bill.status || "Introduced";
  return {
    id: `leg-${bill.id}`,
    date,
    eventType: "legislation",
    title,
    description: `${bill.citation} · ${statusLabel} · ${bill.jurisdiction.toUpperCase()}`,
    sourceUrl: `/legislation/${bill.id}`,
  };
}

async function fetchPage<T>(
  path: string,
  page: number,
  perPage: number
): Promise<{ items: T[]; totalPages: number; total: number }> {
  const separator = path.includes("?") ? "&" : "?";
  const response = await fetch(
    `${API_BASE}/${path}${separator}page=${page}&per_page=${perPage}`,
    { cache: "no-store" }
  );
  if (!response.ok) return { items: [], totalPages: 0, total: 0 };
  const data = await response.json();
  return {
    items: data.items ?? [],
    totalPages: data.total_pages ?? 1,
    total: data.total ?? 0,
  };
}

export default function TimelinePage() {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [filterType, setFilterType] = useState<string>("all");
  const [pagination, setPagination] = useState<PaginationState>({
    eoPage: 1,
    eoTotal: 1,
    casePage: 1,
    caseTotal: 1,
    legPage: 1,
    legTotal: 1,
  });

  // Initial load — fetch first page of each
  useEffect(() => {
    async function fetchInitial() {
      try {
        const [eoData, caseData, legData] = await Promise.all([
          fetchPage<APIExecutiveOrder>("executive-orders", 1, PAGE_SIZE),
          fetchPage<APICourtCase>("cases", 1, PAGE_SIZE),
          fetchPage<APILegislation>(
            "legislation?since=2017-01-01&matched_only=true",
            1,
            PAGE_SIZE
          ),
        ]);

        const newEvents: TimelineEvent[] = [
          ...eoData.items.map(toEOEvent).filter(Boolean),
          ...caseData.items.map(toCaseEvent).filter(Boolean),
          ...legData.items.map(toLegEvent).filter(Boolean),
        ] as TimelineEvent[];

        setEvents(newEvents);
        setPagination({
          eoPage: 1,
          eoTotal: eoData.totalPages,
          casePage: 1,
          caseTotal: caseData.totalPages,
          legPage: 1,
          legTotal: legData.totalPages,
        });
      } catch (error) {
        console.error("Error fetching timeline:", error);
      }
      setLoading(false);
    }
    fetchInitial();
  }, []);

  const hasMore =
    pagination.eoPage < pagination.eoTotal ||
    pagination.casePage < pagination.caseTotal ||
    pagination.legPage < pagination.legTotal;

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);

    try {
      const promises: Promise<TimelineEvent[]>[] = [];
      const newPagination = { ...pagination };

      if (pagination.eoPage < pagination.eoTotal) {
        const nextPage = pagination.eoPage + 1;
        promises.push(
          fetchPage<APIExecutiveOrder>(
            "executive-orders",
            nextPage,
            PAGE_SIZE
          ).then((d) => d.items.map(toEOEvent).filter(Boolean) as TimelineEvent[])
        );
        newPagination.eoPage = nextPage;
      }

      if (pagination.casePage < pagination.caseTotal) {
        const nextPage = pagination.casePage + 1;
        promises.push(
          fetchPage<APICourtCase>("cases", nextPage, PAGE_SIZE).then(
            (d) => d.items.map(toCaseEvent).filter(Boolean) as TimelineEvent[]
          )
        );
        newPagination.casePage = nextPage;
      }

      if (pagination.legPage < pagination.legTotal) {
        const nextPage = pagination.legPage + 1;
        promises.push(
          fetchPage<APILegislation>(
            "legislation?since=2017-01-01&matched_only=true",
            nextPage,
            PAGE_SIZE
          ).then(
            (d) => d.items.map(toLegEvent).filter(Boolean) as TimelineEvent[]
          )
        );
        newPagination.legPage = nextPage;
      }

      const results = await Promise.all(promises);
      const moreEvents = results.flat();

      setEvents((prev) => [...prev, ...moreEvents]);
      setPagination(newPagination);
    } catch (error) {
      console.error("Error loading more timeline events:", error);
    }
    setLoadingMore(false);
  }, [loadingMore, hasMore, pagination]);

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

  const totalLoaded = events.length;

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
          Track the chronological progression of executive actions and court
          decisions
        </p>
      </div>

      {/* Filters */}
      <Card className="mb-8">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
            <fieldset className="min-w-0 border-0 p-0 m-0">
              <legend className="text-sm font-medium mb-2 block">
                Event Type
              </legend>
              <div
                className="flex flex-wrap gap-2"
                role="group"
                aria-label="Event type"
              >
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
            <p className="text-xs text-muted-foreground">
              {totalLoaded.toLocaleString()} events loaded
            </p>
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
            .sort(
              ([a], [b]) => new Date(b).getTime() - new Date(a).getTime()
            )
            .map(([date, dateEvents]) => (
              <div key={date}>
                {/* Date header */}
                <div className="relative flex items-center justify-center mb-4">
                  <div className="absolute left-8 md:left-1/2 w-3 h-3 rounded-full bg-primary -translate-x-1/2" />
                  <span className="relative z-10 bg-background px-4 py-1 rounded-full border text-sm font-medium">
                    {formatDate(date, {
                      weekday: "long",
                      month: "long",
                      day: "numeric",
                    })}
                  </span>
                </div>

                {/* Events for this date */}
                <div className="space-y-4">
                  {dateEvents.map((event, index) => {
                    const config =
                      eventTypeConfig[
                        event.eventType as keyof typeof eventTypeConfig
                      ] || eventTypeConfig.executive_order;
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
                            isEven
                              ? "md:col-start-1 md:pr-8"
                              : "md:col-start-2 md:pl-8"
                          )}
                        >
                          <Card className={cn("border-l-4", config.borderColor)}>
                            <CardContent className="pt-4">
                              <div className="flex items-start gap-3">
                                <div
                                  className={cn("p-2 rounded-lg", config.color)}
                                >
                                  {config.icon}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap mb-1">
                                    <Badge variant="outline" className="text-xs">
                                      {config.label}
                                    </Badge>
                                  </div>
                                  <h3 className="font-semibold mb-1 line-clamp-2">
                                    {event.title}
                                  </h3>
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

        {/* Load More */}
        {hasMore && (
          <div className="mt-8 text-center">
            <Button
              variant="outline"
              onClick={loadMore}
              disabled={loadingMore}
            >
              {loadingMore ? "Loading..." : "Load More Events"}
            </Button>
          </div>
        )}

        {filteredEvents.length === 0 && !loading && (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">No events found.</p>
              <Button variant="link" onClick={() => setFilterType("all")}>
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
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
      />
    </svg>
  );
}

function DocumentIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  );
}

function ScaleIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"
      />
    </svg>
  );
}
