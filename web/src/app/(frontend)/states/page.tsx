"use client";

import { useState, type SVGProps } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Mock data - will be replaced with API calls
const mockStates = [
  {
    code: "CA",
    name: "California",
    resistanceScore: 92,
    protectionLevel: "strong",
    governorParty: "D",
    legislatureControl: "D",
    activeProtections: 45,
    pendingThreats: 3,
  },
  {
    code: "NY",
    name: "New York",
    resistanceScore: 88,
    protectionLevel: "strong",
    governorParty: "D",
    legislatureControl: "D",
    activeProtections: 38,
    pendingThreats: 5,
  },
  {
    code: "TX",
    name: "Texas",
    resistanceScore: 15,
    protectionLevel: "hostile",
    governorParty: "R",
    legislatureControl: "R",
    activeProtections: 2,
    pendingThreats: 28,
  },
  {
    code: "FL",
    name: "Florida",
    resistanceScore: 12,
    protectionLevel: "hostile",
    governorParty: "R",
    legislatureControl: "R",
    activeProtections: 1,
    pendingThreats: 32,
  },
  {
    code: "IL",
    name: "Illinois",
    resistanceScore: 85,
    protectionLevel: "strong",
    governorParty: "D",
    legislatureControl: "D",
    activeProtections: 32,
    pendingThreats: 4,
  },
  {
    code: "PA",
    name: "Pennsylvania",
    resistanceScore: 55,
    protectionLevel: "moderate",
    governorParty: "D",
    legislatureControl: "Split",
    activeProtections: 15,
    pendingThreats: 12,
  },
  {
    code: "OH",
    name: "Ohio",
    resistanceScore: 35,
    protectionLevel: "weak",
    governorParty: "R",
    legislatureControl: "R",
    activeProtections: 8,
    pendingThreats: 18,
  },
  {
    code: "MI",
    name: "Michigan",
    resistanceScore: 78,
    protectionLevel: "strong",
    governorParty: "D",
    legislatureControl: "D",
    activeProtections: 28,
    pendingThreats: 6,
  },
  {
    code: "WA",
    name: "Washington",
    resistanceScore: 90,
    protectionLevel: "strong",
    governorParty: "D",
    legislatureControl: "D",
    activeProtections: 42,
    pendingThreats: 2,
  },
  {
    code: "AZ",
    name: "Arizona",
    resistanceScore: 45,
    protectionLevel: "moderate",
    governorParty: "D",
    legislatureControl: "R",
    activeProtections: 12,
    pendingThreats: 15,
  },
];

const protectionLevelColors = {
  strong: "bg-green-500",
  moderate: "bg-yellow-500",
  weak: "bg-orange-500",
  hostile: "bg-red-500",
};

const protectionLevelLabels = {
  strong: "Strong Protections",
  moderate: "Moderate Protections",
  weak: "Weak Protections",
  hostile: "Hostile Environment",
};

export default function StatesPage() {
  const [sortBy, setSortBy] = useState<"name" | "score">("score");
  const [filterLevel, setFilterLevel] = useState<string>("all");

  const filteredStates = mockStates
    .filter((state) => filterLevel === "all" || state.protectionLevel === filterLevel)
    .sort((a, b) => {
      if (sortBy === "name") return a.name.localeCompare(b.name);
      return b.resistanceScore - a.resistanceScore;
    });

  const statsByLevel = {
    strong: mockStates.filter((s) => s.protectionLevel === "strong").length,
    moderate: mockStates.filter((s) => s.protectionLevel === "moderate").length,
    weak: mockStates.filter((s) => s.protectionLevel === "weak").length,
    hostile: mockStates.filter((s) => s.protectionLevel === "hostile").length,
  };

  return (
    <div className="container py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">State Protections</h1>
        <p className="text-muted-foreground">
          Track which states are protecting rights and which are amplifying
          Project 2025 implementation
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4 mb-8">
        <button
          type="button"
          className="w-full rounded-lg border bg-card text-card-foreground shadow-sm hover:border-green-500 transition-colors text-left"
          onClick={() => setFilterLevel(filterLevel === "strong" ? "all" : "strong")}
          aria-pressed={filterLevel === "strong"}
        >
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Strong</p>
                <p className="text-2xl font-bold text-green-600">
                  {statsByLevel.strong}
                </p>
              </div>
              <div className="w-3 h-3 rounded-full bg-green-500" />
            </div>
          </CardContent>
        </button>

        <button
          type="button"
          className="w-full rounded-lg border bg-card text-card-foreground shadow-sm hover:border-yellow-500 transition-colors text-left"
          onClick={() => setFilterLevel(filterLevel === "moderate" ? "all" : "moderate")}
          aria-pressed={filterLevel === "moderate"}
        >
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Moderate</p>
                <p className="text-2xl font-bold text-yellow-600">
                  {statsByLevel.moderate}
                </p>
              </div>
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
            </div>
          </CardContent>
        </button>

        <button
          type="button"
          className="w-full rounded-lg border bg-card text-card-foreground shadow-sm hover:border-orange-500 transition-colors text-left"
          onClick={() => setFilterLevel(filterLevel === "weak" ? "all" : "weak")}
          aria-pressed={filterLevel === "weak"}
        >
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Weak</p>
                <p className="text-2xl font-bold text-orange-600">
                  {statsByLevel.weak}
                </p>
              </div>
              <div className="w-3 h-3 rounded-full bg-orange-500" />
            </div>
          </CardContent>
        </button>

        <button
          type="button"
          className="w-full rounded-lg border bg-card text-card-foreground shadow-sm hover:border-red-500 transition-colors text-left"
          onClick={() => setFilterLevel(filterLevel === "hostile" ? "all" : "hostile")}
          aria-pressed={filterLevel === "hostile"}
        >
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Hostile</p>
                <p className="text-2xl font-bold text-red-600">
                  {statsByLevel.hostile}
                </p>
              </div>
              <div className="w-3 h-3 rounded-full bg-red-500" />
            </div>
          </CardContent>
        </button>
      </div>

      {/* Map Placeholder */}
      <Card className="mb-8">
        <CardContent className="py-12">
          <div className="flex items-center justify-center">
            <div className="text-center">
              <MapIcon
                className="h-24 w-24 mx-auto text-muted-foreground mb-4"
                aria-hidden="true"
              />
              <h3 className="text-lg font-semibold mb-2">
                Interactive State Map
              </h3>
              <p className="text-muted-foreground max-w-md">
                An interactive map showing state-by-state protection levels will
                be displayed here. Click on any state to see detailed
                information.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Filters & Sort */}
      <div className="flex flex-col sm:flex-row justify-between gap-4 mb-6">
        <fieldset className="flex items-center gap-2 border-0 p-0 m-0">
          <legend className="text-sm text-muted-foreground">Filter:</legend>
          <Button
            variant={filterLevel === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterLevel("all")}
            aria-pressed={filterLevel === "all"}
          >
            All
          </Button>
          <Button
            variant={filterLevel === "strong" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterLevel("strong")}
            aria-pressed={filterLevel === "strong"}
          >
            Strong
          </Button>
          <Button
            variant={filterLevel === "moderate" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterLevel("moderate")}
            aria-pressed={filterLevel === "moderate"}
          >
            Moderate
          </Button>
          <Button
            variant={filterLevel === "weak" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterLevel("weak")}
            aria-pressed={filterLevel === "weak"}
          >
            Weak
          </Button>
          <Button
            variant={filterLevel === "hostile" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterLevel("hostile")}
            aria-pressed={filterLevel === "hostile"}
          >
            Hostile
          </Button>
        </fieldset>

        <fieldset className="flex items-center gap-2 border-0 p-0 m-0">
          <legend className="text-sm text-muted-foreground">Sort by:</legend>
          <Button
            variant={sortBy === "score" ? "default" : "outline"}
            size="sm"
            onClick={() => setSortBy("score")}
            aria-pressed={sortBy === "score"}
          >
            Score
          </Button>
          <Button
            variant={sortBy === "name" ? "default" : "outline"}
            size="sm"
            onClick={() => setSortBy("name")}
            aria-pressed={sortBy === "name"}
          >
            Name
          </Button>
        </fieldset>
      </div>

      {/* State List */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredStates.map((state) => (
          <StateCard key={state.code} state={state} />
        ))}
      </div>
    </div>
  );
}

interface StateCardProps {
  state: {
    code: string;
    name: string;
    resistanceScore: number;
    protectionLevel: string;
    governorParty: string;
    legislatureControl: string;
    activeProtections: number;
    pendingThreats: number;
  };
}

function StateCard({ state }: StateCardProps) {
  return (
    <Link href={`/states/${state.code.toLowerCase()}`}>
      <Card className="h-full transition-shadow hover:shadow-md cursor-pointer">
        <CardContent className="pt-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold">{state.name}</h3>
              <p className="text-sm text-muted-foreground">{state.code}</p>
            </div>
            <div
              className={cn(
                "px-2 py-1 rounded text-xs font-semibold text-white",
                protectionLevelColors[
                  state.protectionLevel as keyof typeof protectionLevelColors
                ]
              )}
            >
              {state.resistanceScore}%
            </div>
          </div>

          {/* Resistance Score Bar */}
          <div className="mb-4">
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  protectionLevelColors[
                    state.protectionLevel as keyof typeof protectionLevelColors
                  ]
                )}
                style={{ width: `${state.resistanceScore}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {
                protectionLevelLabels[
                  state.protectionLevel as keyof typeof protectionLevelLabels
                ]
              }
            </p>
          </div>

          {/* Details */}
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-muted-foreground">Governor:</span>
              <Badge
                variant="outline"
                className={cn(
                  "ml-2",
                  state.governorParty === "D"
                    ? "border-blue-500 text-blue-600"
                    : "border-red-500 text-red-600"
                )}
              >
                {state.governorParty}
              </Badge>
            </div>
            <div>
              <span className="text-muted-foreground">Legislature:</span>
              <Badge
                variant="outline"
                className={cn(
                  "ml-2",
                  state.legislatureControl === "D"
                    ? "border-blue-500 text-blue-600"
                    : state.legislatureControl === "R"
                      ? "border-red-500 text-red-600"
                      : "border-purple-500 text-purple-600"
                )}
              >
                {state.legislatureControl}
              </Badge>
            </div>
          </div>

          <div className="flex justify-between mt-4 pt-4 border-t text-sm">
            <span className="text-green-600">
              {state.activeProtections} protections
            </span>
            <span className="text-red-600">{state.pendingThreats} threats</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

type IconProps = SVGProps<SVGSVGElement> & { className?: string };

function MapIcon({ className, ...props }: IconProps) {
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
        d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
      />
    </svg>
  );
}
