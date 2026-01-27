"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, snakeToTitle } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface APIObjective {
  id: number;
  section: string;
  chapter: string | null;
  agency: string;
  proposal_text: string;
  proposal_summary: string | null;
  page_number: number;
  category: string;
  action_type: string;
  priority: string;
  implementation_timeline: string;
  status: string;
  confidence: number;
}

interface ObjectivesResponse {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  items: APIObjective[];
}

interface ObjectiveMetadata {
  categories: string[];
  statuses: string[];
  priorities: string[];
  timelines: string[];
}

function TrackerContent() {
  const searchParams = useSearchParams();
  const initialCategory = searchParams.get("category") || "all";

  const [objectives, setObjectives] = useState<APIObjective[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [metadata, setMetadata] = useState<ObjectiveMetadata | null>(null);

  const [selectedCategory, setSelectedCategory] = useState(initialCategory);
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedPriority, setSelectedPriority] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    async function fetchMetadata() {
      try {
        const response = await fetch(`${API_BASE}/objectives/metadata`);
        if (!response.ok) return;
        const data: ObjectiveMetadata = await response.json();
        setMetadata(data);
      } catch (err) {
        console.error("Failed to fetch objective metadata:", err);
      }
    }

    fetchMetadata();
  }, []);

  useEffect(() => {
    async function fetchObjectives() {
      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams({
          page: page.toString(),
          per_page: "20",
        });

        if (selectedCategory !== "all") {
          params.set("category", selectedCategory);
        }
        if (selectedStatus !== "all") {
          params.set("status", selectedStatus);
        }
        if (selectedPriority !== "all") {
          params.set("priority", selectedPriority);
        }

        const response = await fetch(`${API_BASE}/objectives?${params}`);

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const data: ObjectivesResponse = await response.json();
        setObjectives(data.items);
        setTotal(data.total);
        setTotalPages(data.total_pages);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch objectives");
        setObjectives([]);
      } finally {
        setLoading(false);
      }
    }

    fetchObjectives();
  }, [page, selectedCategory, selectedStatus, selectedPriority]);

  // Client-side search filter
  const filteredObjectives = objectives.filter((obj) => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        obj.proposal_text.toLowerCase().includes(query) ||
        obj.agency.toLowerCase().includes(query) ||
        (obj.proposal_summary?.toLowerCase().includes(query) ?? false)
      );
    }
    return true;
  });

  const categories = [
    { slug: "all", name: "All Categories" },
    ...(metadata?.categories ?? []).map((slug) => ({
      slug,
      name: snakeToTitle(slug),
    })),
  ];
  const statuses = [
    { slug: "all", name: "All Statuses" },
    ...(metadata?.statuses ?? []).map((slug) => ({
      slug,
      name: snakeToTitle(slug),
    })),
  ];
  const priorities = [
    { slug: "all", name: "All Priorities" },
    ...(metadata?.priorities ?? []).map((slug) => ({
      slug,
      name: snakeToTitle(slug),
    })),
  ];

  return (
    <div className="container py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Project 2025 Tracker</h1>
        <p className="text-muted-foreground">
          Monitor the implementation status of {total > 0 ? total : "Project 2025"} policy objectives from the Mandate for Leadership
        </p>
      </div>

      {/* Filters */}
      <Card className="mb-8">
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Search */}
            <div>
              <label htmlFor="tracker-search" className="text-sm font-medium mb-2 block">
                Search
              </label>
              <input
                id="tracker-search"
                type="text"
                placeholder="Search proposals..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              />
            </div>

            {/* Category */}
            <div>
              <label htmlFor="tracker-category" className="text-sm font-medium mb-2 block">
                Category
              </label>
              <select
                id="tracker-category"
                value={selectedCategory}
                onChange={(e) => {
                  setSelectedCategory(e.target.value);
                  setPage(1);
                }}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                {categories.map((cat) => (
                  <option key={cat.slug} value={cat.slug}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Status */}
            <div>
              <label htmlFor="tracker-status" className="text-sm font-medium mb-2 block">
                Status
              </label>
              <select
                id="tracker-status"
                value={selectedStatus}
                onChange={(e) => {
                  setSelectedStatus(e.target.value);
                  setPage(1);
                }}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                {statuses.map((status) => (
                  <option key={status.slug} value={status.slug}>
                    {status.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Priority */}
            <div>
              <label htmlFor="tracker-priority" className="text-sm font-medium mb-2 block">
                Priority
              </label>
              <select
                id="tracker-priority"
                value={selectedPriority}
                onChange={(e) => {
                  setSelectedPriority(e.target.value);
                  setPage(1);
                }}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                {priorities.map((level) => (
                  <option key={level.slug} value={level.slug}>
                    {level.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results count and pagination */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-muted-foreground">
          {loading ? (
            "Loading..."
          ) : error ? (
            <span className="text-destructive">{error}</span>
          ) : (
            <>Showing {filteredObjectives.length} of {total} objectives</>
          )}
        </p>
        <div className="flex gap-2">
          {totalPages > 1 && (
            <>
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground py-2">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                Next
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="flex flex-col md:flex-row md:items-start gap-4">
                  <div className="flex-1">
                    <div className="flex gap-2 mb-2">
                      <Skeleton className="h-5 w-20" />
                      <Skeleton className="h-5 w-16" />
                      <Skeleton className="h-5 w-12" />
                    </div>
                    <Skeleton className="h-6 w-3/4 mb-2" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-2/3 mt-1" />
                  </div>
                  <Skeleton className="h-8 w-32" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-destructive mb-4">{error}</p>
            <p className="text-muted-foreground mb-4">
              The Project 2025 database may need to be populated.
            </p>
            <Button variant="outline" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {!loading && !error && filteredObjectives.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">
              {total === 0
                ? "No Project 2025 objectives have been ingested yet."
                : "No objectives match your filters."
              }
            </p>
            {total > 0 && (
              <Button
                variant="link"
                onClick={() => {
                  setSelectedCategory("all");
                  setSelectedStatus("all");
                  setSelectedPriority("all");
                  setSearchQuery("");
                  setPage(1);
                }}
              >
                Clear filters
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Objectives List */}
      {!loading && !error && filteredObjectives.length > 0 && (
        <div className="space-y-4">
          {filteredObjectives.map((objective) => (
            <ObjectiveCard key={objective.id} objective={objective} />
          ))}
        </div>
      )}
    </div>
  );
}

function TrackerLoading() {
  return (
    <div className="container py-8">
      <div className="mb-8">
        <Skeleton className="h-9 w-64 mb-2" />
        <Skeleton className="h-5 w-96" />
      </div>
      <Card className="mb-8">
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i}>
                <Skeleton className="h-4 w-16 mb-2" />
                <Skeleton className="h-10 w-full" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function TrackerPage() {
  return (
    <Suspense fallback={<TrackerLoading />}>
      <TrackerContent />
    </Suspense>
  );
}

interface ObjectiveCardProps {
  objective: APIObjective;
}

function ObjectiveCard({ objective }: ObjectiveCardProps) {
  const priorityColors = {
    high: "bg-red-500",
    medium: "bg-orange-500",
    low: "bg-green-500",
  };

  const priorityVariant = objective.priority as "high" | "medium" | "low";
  const statusVariant = objective.status === "in_progress" ? "in_progress" :
                        objective.status === "enacted" ? "enacted" :
                        objective.status === "blocked" ? "blocked" : "proposed";

  // Calculate a progress percentage based on status
  const progressByStatus: Record<string, number> = {
    proposed: 10,
    in_progress: 50,
    enacted: 100,
    blocked: 0,
  };
  const progress = progressByStatus[objective.status] || 0;

  return (
    <Link href={`/tracker/${objective.id}`}>
      <Card className="transition-shadow hover:shadow-md cursor-pointer">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row md:items-start gap-4">
            {/* Left: Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <Badge variant="outline">{snakeToTitle(objective.category)}</Badge>
                <Badge variant={statusVariant as "proposed" | "in_progress" | "enacted" | "blocked"}>
                  {snakeToTitle(objective.status)}
                </Badge>
                <Badge variant={priorityVariant === "high" ? "critical" : priorityVariant === "medium" ? "elevated" : "moderate"}>
                  {objective.priority.toUpperCase()}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {snakeToTitle(objective.action_type)}
                </Badge>
              </div>

              <h3 className="text-lg font-semibold mb-2 break-words">
                {objective.agency}: {snakeToTitle(objective.action_type)}
              </h3>
              <p className="text-sm text-muted-foreground whitespace-normal break-words">
                {objective.proposal_summary || objective.proposal_text}
              </p>

              <p className="text-xs text-muted-foreground mt-2">
                Source: Mandate for Leadership, p. {objective.page_number} | Section: {objective.section}
              </p>
            </div>

            {/* Right: Progress & Timeline */}
            <div className="w-full md:w-48 shrink-0 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Status</span>
                <span className="font-semibold text-xs">
                  {snakeToTitle(objective.implementation_timeline)}
                </span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    priorityColors[priorityVariant] || "bg-gray-500"
                  )}
                  style={{ width: `${progress}%` }}
                />
              </div>
              {objective.confidence > 0 && (
                <p className="text-xs text-muted-foreground text-right">
                  Confidence: {Math.round(objective.confidence * 100)}%
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
