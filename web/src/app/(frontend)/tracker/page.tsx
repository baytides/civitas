"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn, formatPercentage, snakeToTitle } from "@/lib/utils";

// Mock data - will be replaced with API calls
const mockObjectives = [
  {
    id: "ed-1",
    category: "education",
    subcategory: "federal",
    title: "Eliminate Department of Education",
    description: "Abolish the federal Department of Education and return education policy to states",
    sourcePage: 319,
    implementationStatus: "in_progress",
    threatLevel: "critical",
    progressPercentage: 35,
  },
  {
    id: "env-1",
    category: "environment",
    subcategory: "epa",
    title: "Restructure Environmental Protection Agency",
    description: "Reduce EPA regulatory authority and streamline permitting processes",
    sourcePage: 417,
    implementationStatus: "in_progress",
    threatLevel: "high",
    progressPercentage: 28,
  },
  {
    id: "imm-1",
    category: "immigration",
    subcategory: "enforcement",
    title: "Expand Immigration Enforcement",
    description: "Increase deportation capacity and expand enforcement priorities",
    sourcePage: 133,
    implementationStatus: "enacted",
    threatLevel: "critical",
    progressPercentage: 65,
  },
  {
    id: "hc-1",
    category: "healthcare",
    subcategory: "aca",
    title: "Reform Affordable Care Act",
    description: "Modify or eliminate key provisions of the Affordable Care Act",
    sourcePage: 449,
    implementationStatus: "proposed",
    threatLevel: "elevated",
    progressPercentage: 15,
  },
  {
    id: "cr-1",
    category: "civil_rights",
    subcategory: "dei",
    title: "End DEI Programs in Federal Agencies",
    description: "Eliminate diversity, equity, and inclusion programs across federal government",
    sourcePage: 81,
    implementationStatus: "enacted",
    threatLevel: "critical",
    progressPercentage: 72,
  },
  {
    id: "gov-1",
    category: "government",
    subcategory: "workforce",
    title: "Implement Schedule F",
    description: "Reclassify federal employees to remove civil service protections",
    sourcePage: 71,
    implementationStatus: "in_progress",
    threatLevel: "critical",
    progressPercentage: 45,
  },
];

const categories = [
  { slug: "all", name: "All Categories" },
  { slug: "immigration", name: "Immigration" },
  { slug: "environment", name: "Environment" },
  { slug: "healthcare", name: "Healthcare" },
  { slug: "education", name: "Education" },
  { slug: "civil_rights", name: "Civil Rights" },
  { slug: "government", name: "Government" },
];

const statuses = [
  { slug: "all", name: "All Statuses" },
  { slug: "enacted", name: "Enacted" },
  { slug: "in_progress", name: "In Progress" },
  { slug: "proposed", name: "Proposed" },
  { slug: "blocked", name: "Blocked" },
];

const threatLevels = [
  { slug: "all", name: "All Threat Levels" },
  { slug: "critical", name: "Critical" },
  { slug: "high", name: "High" },
  { slug: "elevated", name: "Elevated" },
  { slug: "moderate", name: "Moderate" },
];

export default function TrackerPage() {
  const searchParams = useSearchParams();
  const initialCategory = searchParams.get("category") || "all";

  const [selectedCategory, setSelectedCategory] = useState(initialCategory);
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedThreat, setSelectedThreat] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredObjectives = mockObjectives.filter((obj) => {
    if (selectedCategory !== "all" && obj.category !== selectedCategory) return false;
    if (selectedStatus !== "all" && obj.implementationStatus !== selectedStatus) return false;
    if (selectedThreat !== "all" && obj.threatLevel !== selectedThreat) return false;
    if (searchQuery && !obj.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="container py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Project 2025 Tracker</h1>
        <p className="text-muted-foreground">
          Monitor the implementation status of Project 2025 policy objectives
        </p>
      </div>

      {/* Filters */}
      <Card className="mb-8">
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Search */}
            <div>
              <label className="text-sm font-medium mb-2 block">Search</label>
              <input
                type="text"
                placeholder="Search objectives..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              />
            </div>

            {/* Category */}
            <div>
              <label className="text-sm font-medium mb-2 block">Category</label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
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
              <label className="text-sm font-medium mb-2 block">Status</label>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                {statuses.map((status) => (
                  <option key={status.slug} value={status.slug}>
                    {status.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Threat Level */}
            <div>
              <label className="text-sm font-medium mb-2 block">Threat Level</label>
              <select
                value={selectedThreat}
                onChange={(e) => setSelectedThreat(e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                {threatLevels.map((level) => (
                  <option key={level.slug} value={level.slug}>
                    {level.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results count */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-muted-foreground">
          Showing {filteredObjectives.length} of {mockObjectives.length} objectives
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            Export CSV
          </Button>
        </div>
      </div>

      {/* Objectives List */}
      <div className="space-y-4">
        {filteredObjectives.map((objective) => (
          <ObjectiveCard key={objective.id} objective={objective} />
        ))}

        {filteredObjectives.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">
                No objectives match your filters.
              </p>
              <Button
                variant="link"
                onClick={() => {
                  setSelectedCategory("all");
                  setSelectedStatus("all");
                  setSelectedThreat("all");
                  setSearchQuery("");
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

interface ObjectiveCardProps {
  objective: {
    id: string;
    category: string;
    subcategory: string;
    title: string;
    description: string;
    sourcePage: number;
    implementationStatus: string;
    threatLevel: string;
    progressPercentage: number;
  };
}

function ObjectiveCard({ objective }: ObjectiveCardProps) {
  const threatColors = {
    critical: "bg-red-500",
    high: "bg-orange-500",
    elevated: "bg-yellow-500",
    moderate: "bg-green-500",
  };

  const statusVariant = objective.implementationStatus as "enacted" | "in_progress" | "proposed" | "blocked";

  return (
    <Link href={`/tracker/${objective.id}`}>
      <Card className="transition-shadow hover:shadow-md cursor-pointer">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row md:items-start gap-4">
            {/* Left: Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <Badge variant="outline">{snakeToTitle(objective.category)}</Badge>
                <Badge variant={statusVariant}>
                  {snakeToTitle(objective.implementationStatus)}
                </Badge>
                <Badge
                  variant={objective.threatLevel as "critical" | "high" | "elevated" | "moderate"}
                >
                  {objective.threatLevel.toUpperCase()}
                </Badge>
              </div>

              <h3 className="text-lg font-semibold mb-2">{objective.title}</h3>
              <p className="text-sm text-muted-foreground line-clamp-2">
                {objective.description}
              </p>

              <p className="text-xs text-muted-foreground mt-2">
                Source: Mandate for Leadership, p. {objective.sourcePage}
              </p>
            </div>

            {/* Right: Progress */}
            <div className="w-full md:w-48 shrink-0">
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-muted-foreground">Progress</span>
                <span className="font-semibold">
                  {formatPercentage(objective.progressPercentage)}
                </span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    threatColors[objective.threatLevel as keyof typeof threatColors]
                  )}
                  style={{ width: `${objective.progressPercentage}%` }}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
