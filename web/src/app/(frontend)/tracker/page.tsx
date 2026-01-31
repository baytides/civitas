"use client";

import { Suspense, useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Fuse, { type IFuseOptions } from "fuse.js";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  type SortingState,
  type ColumnDef,
  flexRender,
} from "@tanstack/react-table";
import { AnimatePresence, motion } from "motion/react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CsvExport } from "@/components/CsvExport";
import { cn, snakeToTitle } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://api.projectcivitas.com/api/v1";

interface APIObjective {
  id: number;
  title: string;
  title_short?: string;
  title_full?: string;
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

type ViewMode = "cards" | "table";

const fuseOptions: IFuseOptions<APIObjective> = {
  keys: [
    { name: "title", weight: 0.4 },
    { name: "title_full", weight: 0.45 },
    { name: "title_short", weight: 0.35 },
    { name: "proposal_summary", weight: 0.25 },
    { name: "proposal_text", weight: 0.15 },
    { name: "agency", weight: 0.15 },
    { name: "section", weight: 0.05 },
  ],
  threshold: 0.4,
  includeScore: true,
  ignoreLocation: true,
};

const CSV_HEADERS = [
  { label: "ID", key: "id" },
  { label: "Title", key: "title_full" },
  { label: "Category", key: "category" },
  { label: "Status", key: "status" },
  { label: "Priority", key: "priority" },
  { label: "Agency", key: "agency" },
  { label: "Action Type", key: "action_type" },
  { label: "Timeline", key: "implementation_timeline" },
  { label: "Section", key: "section" },
  { label: "Page", key: "page_number" },
  { label: "Confidence", key: "confidence" },
];

const tableColumns: ColumnDef<APIObjective>[] = [
  {
    accessorKey: "title",
    header: "Title",
    cell: ({ row }) => (
      <Link
        href={`/tracker/${row.original.id}`}
        className="font-medium text-primary hover:underline line-clamp-2"
      >
        {row.original.title_full ||
          row.original.title ||
          row.original.proposal_summary ||
          row.original.proposal_text}
      </Link>
    ),
    size: 400,
  },
  {
    accessorKey: "category",
    header: "Category",
    cell: ({ getValue }) => (
      <Badge variant="outline" className="text-xs whitespace-nowrap">
        {snakeToTitle(getValue<string>())}
      </Badge>
    ),
    size: 140,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ getValue }) => {
      const status = getValue<string>();
      const variant = status === "in_progress" ? "in_progress" :
                      status === "enacted" ? "enacted" :
                      status === "blocked" ? "blocked" : "proposed";
      return (
        <Badge variant={variant as "proposed" | "in_progress" | "enacted" | "blocked"} className="whitespace-nowrap">
          {snakeToTitle(status)}
        </Badge>
      );
    },
    size: 120,
  },
  {
    accessorKey: "priority",
    header: "Priority",
    cell: ({ getValue }) => {
      const priority = getValue<string>() as "high" | "medium" | "low";
      return (
        <Badge
          variant={priority === "high" ? "critical" : priority === "medium" ? "elevated" : "moderate"}
          className="whitespace-nowrap"
        >
          {priority.toUpperCase()}
        </Badge>
      );
    },
    size: 100,
  },
  {
    accessorKey: "agency",
    header: "Agency",
    cell: ({ getValue }) => (
      <span className="text-sm text-muted-foreground truncate block max-w-[200px]">
        {getValue<string>()}
      </span>
    ),
    size: 200,
  },
  {
    accessorKey: "implementation_timeline",
    header: "Timeline",
    cell: ({ getValue }) => (
      <span className="text-xs text-muted-foreground whitespace-nowrap">
        {getValue<string>() ? snakeToTitle(getValue<string>()) : "N/A"}
      </span>
    ),
    size: 120,
  },
];

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
  const [viewMode, setViewMode] = useState<ViewMode>("cards");
  const [sorting, setSorting] = useState<SortingState>([]);

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

  // Fuse.js fuzzy search
  const fuse = useMemo(() => new Fuse(objectives, fuseOptions), [objectives]);

  const filteredObjectives = useMemo(() => {
    if (!searchQuery.trim()) return objectives;
    return fuse.search(searchQuery).map((result) => result.item);
  }, [fuse, objectives, searchQuery]);

  // TanStack Table instance
  const table = useReactTable({
    data: filteredObjectives,
    columns: tableColumns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
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
                placeholder="Fuzzy search proposals..."
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

      {/* Results count, view toggle, export, and pagination */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <p className="text-sm text-muted-foreground">
          {loading ? (
            "Loading..."
          ) : error ? (
            <span className="text-destructive">{error}</span>
          ) : (
            <>Showing {filteredObjectives.length} of {total} objectives</>
          )}
        </p>
        <div className="flex items-center gap-2">
          {/* CSV Export */}
          {!loading && filteredObjectives.length > 0 && (
            <CsvExport
              data={filteredObjectives as unknown as Record<string, unknown>[]}
              filename="project-2025-objectives.csv"
              headers={CSV_HEADERS}
              label="Export CSV"
            />
          )}

          {/* View Toggle */}
          <div className="flex border rounded-md overflow-hidden">
            <button
              onClick={() => setViewMode("cards")}
              className={cn(
                "px-3 py-1.5 text-sm transition-colors",
                viewMode === "cards"
                  ? "bg-primary text-primary-foreground"
                  : "bg-background hover:bg-muted"
              )}
              aria-pressed={viewMode === "cards"}
            >
              <CardsIcon className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode("table")}
              className={cn(
                "px-3 py-1.5 text-sm transition-colors",
                viewMode === "table"
                  ? "bg-primary text-primary-foreground"
                  : "bg-background hover:bg-muted"
              )}
              aria-pressed={viewMode === "table"}
            >
              <TableIcon className="h-4 w-4" />
            </button>
          </div>

          {/* Pagination */}
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

      {/* Objectives — Card View */}
      {!loading && !error && filteredObjectives.length > 0 && viewMode === "cards" && (
        <AnimatePresence mode="wait">
          <motion.div
            key="cards"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="space-y-4"
          >
            {filteredObjectives.map((objective) => (
              <ObjectiveCard key={objective.id} objective={objective} />
            ))}
          </motion.div>
        </AnimatePresence>
      )}

      {/* Objectives — Table View */}
      {!loading && !error && filteredObjectives.length > 0 && viewMode === "table" && (
        <AnimatePresence mode="wait">
          <motion.div
            key="table"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <Card>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    {table.getHeaderGroups().map((headerGroup) => (
                      <tr key={headerGroup.id} className="border-b">
                        {headerGroup.headers.map((header) => (
                          <th
                            key={header.id}
                            className={cn(
                              "px-4 py-3 text-left font-medium text-muted-foreground",
                              header.column.getCanSort() && "cursor-pointer select-none hover:text-foreground"
                            )}
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            <div className="flex items-center gap-1">
                              {flexRender(header.column.columnDef.header, header.getContext())}
                              {header.column.getIsSorted() === "asc" && " ↑"}
                              {header.column.getIsSorted() === "desc" && " ↓"}
                            </div>
                          </th>
                        ))}
                      </tr>
                    ))}
                  </thead>
                  <tbody>
                    {table.getRowModel().rows.map((row) => (
                      <tr
                        key={row.id}
                        className="border-b last:border-0 hover:bg-muted/50 transition-colors"
                      >
                        {row.getVisibleCells().map((cell) => (
                          <td key={cell.id} className="px-4 py-3">
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </motion.div>
        </AnimatePresence>
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

function getObjectiveTitle(objective: APIObjective) {
  return (
    objective.title_full ||
    objective.title ||
    objective.proposal_summary ||
    objective.proposal_text
  );
}

interface ObjectiveCardProps {
  objective: APIObjective;
}

function ObjectiveCard({ objective }: ObjectiveCardProps) {
  const priorityVariant = objective.priority as "high" | "medium" | "low";
  const statusVariant = objective.status === "in_progress" ? "in_progress" :
                        objective.status === "enacted" ? "enacted" :
                        objective.status === "blocked" ? "blocked" : "proposed";

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
                {getObjectiveTitle(objective)}
              </h3>
              <p className="text-sm text-muted-foreground whitespace-normal break-words">
                {objective.agency} · {snakeToTitle(objective.action_type)}
              </p>

              <p className="text-xs text-muted-foreground mt-2">
                Source: Mandate for Leadership, p. {objective.page_number} | Section: {objective.section}
              </p>
            </div>

            {/* Right: Timeline & Confidence */}
            <div className="w-full md:w-48 shrink-0 space-y-2 text-right">
              <div className="text-sm">
                <span className="text-muted-foreground">Timeline: </span>
                <span className="font-semibold text-xs">
                  {objective.implementation_timeline
                    ? snakeToTitle(objective.implementation_timeline)
                    : "Not specified"}
                </span>
              </div>
              {objective.confidence > 0 && (
                <p className="text-xs text-muted-foreground">
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

// Icons
function CardsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  );
}

function TableIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18M3 6h18M3 18h18" />
    </svg>
  );
}
