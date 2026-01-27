"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Mock data
const resistanceTiers = [
  {
    tier: 1,
    title: "Courts & States",
    subtitle: "Immediate Actions (Now)",
    color: "green",
    description:
      "Challenge unconstitutional actions through litigation and strengthen state-level protections. These are the most effective immediate tools available.",
    actions: [
      {
        id: "1-1",
        title: "Support Constitutional Litigation",
        description:
          "Donate to and spread awareness about lawsuits challenging executive overreach",
        urgency: "critical",
        effectiveness: 85,
        resources: ["ACLU", "Brennan Center", "Democracy Forward"],
      },
      {
        id: "1-2",
        title: "Contact State Legislators",
        description:
          "Push for state laws that protect rights and resist federal overreach",
        urgency: "high",
        effectiveness: 75,
        resources: ["Find your state rep", "Model legislation"],
      },
      {
        id: "1-3",
        title: "Support State Attorney Generals",
        description:
          "State AGs are filing suits against unconstitutional federal actions",
        urgency: "high",
        effectiveness: 80,
        resources: ["AG contact info", "State lawsuits tracker"],
      },
      {
        id: "1-4",
        title: "Engage Local Government",
        description:
          "Cities and counties can pass protective ordinances and resolutions",
        urgency: "medium",
        effectiveness: 60,
        resources: ["Local government guide", "Model ordinances"],
      },
    ],
  },
  {
    tier: 2,
    title: "Congress 2026",
    subtitle: "Midterm Strategy",
    color: "yellow",
    description:
      "Work toward flipping Congress in the 2026 midterm elections to provide legislative checks on executive power.",
    actions: [
      {
        id: "2-1",
        title: "Register New Voters",
        description:
          "Every new registered voter increases our chances in 2026",
        urgency: "high",
        effectiveness: 90,
        resources: ["Vote.org", "Rock the Vote"],
      },
      {
        id: "2-2",
        title: "Support Candidates",
        description:
          "Identify and support candidates committed to democratic values",
        urgency: "medium",
        effectiveness: 85,
        resources: ["ActBlue", "Run for Something"],
      },
      {
        id: "2-3",
        title: "Join or Start Organizing Groups",
        description:
          "Local organizing is the foundation of electoral success",
        urgency: "medium",
        effectiveness: 80,
        resources: ["Indivisible", "Swing Left"],
      },
      {
        id: "2-4",
        title: "Combat Disinformation",
        description:
          "Help friends and family understand what's actually happening",
        urgency: "high",
        effectiveness: 70,
        resources: ["Media literacy resources", "Fact-checking tools"],
      },
    ],
  },
  {
    tier: 3,
    title: "Presidency 2028",
    subtitle: "Long-term Vision",
    color: "blue",
    description:
      "Build toward restoring democratic leadership in the executive branch in 2028, while preparing institutional reforms.",
    actions: [
      {
        id: "3-1",
        title: "Develop New Leaders",
        description:
          "Support programs that train the next generation of democratic leaders",
        urgency: "medium",
        effectiveness: 75,
        resources: ["Arena", "New Politics"],
      },
      {
        id: "3-2",
        title: "Build Coalition Infrastructure",
        description:
          "Create lasting organizations that can sustain the movement",
        urgency: "medium",
        effectiveness: 70,
        resources: ["Local chapters", "Coalition building guides"],
      },
      {
        id: "3-3",
        title: "Reform Advocacy",
        description:
          "Push for systemic reforms to prevent future democratic backsliding",
        urgency: "low",
        effectiveness: 65,
        resources: ["Democracy reform orgs", "Constitutional amendments"],
      },
    ],
  },
];

const urgencyColors = {
  critical: "bg-red-500 text-white",
  high: "bg-orange-500 text-white",
  medium: "bg-yellow-500 text-black",
  low: "bg-blue-500 text-white",
};

const tierColors = {
  green: {
    border: "border-l-green-500",
    bg: "bg-green-500",
    text: "text-green-600",
    light: "bg-green-50 dark:bg-green-950/20",
  },
  yellow: {
    border: "border-l-yellow-500",
    bg: "bg-yellow-500",
    text: "text-yellow-600",
    light: "bg-yellow-50 dark:bg-yellow-950/20",
  },
  blue: {
    border: "border-l-blue-500",
    bg: "bg-blue-500",
    text: "text-blue-600",
    light: "bg-blue-50 dark:bg-blue-950/20",
  },
};

export default function ResistancePage() {
  const [expandedTier, setExpandedTier] = useState<number | null>(1);
  const [selectedUrgency, setSelectedUrgency] = useState<string>("all");

  return (
    <div className="container py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Resistance Strategy</h1>
        <p className="text-muted-foreground max-w-3xl">
          A three-tier approach to protecting democracy. Focus on what is most
          effective now while building toward longer-term goals.
        </p>
      </div>

      {/* Strategy Overview */}
      <Card className="mb-8">
        <CardContent className="pt-6">
          <div className="grid md:grid-cols-3 gap-6">
            {resistanceTiers.map((tier) => {
              const colors = tierColors[tier.color as keyof typeof tierColors];
              return (
                <button
                  key={tier.tier}
                  className={cn(
                    "w-full p-4 rounded-lg border-l-4 text-left transition-colors",
                    colors.border,
                    expandedTier === tier.tier ? colors.light : "hover:bg-muted/50"
                  )}
                  onClick={() =>
                    setExpandedTier(expandedTier === tier.tier ? null : tier.tier)
                  }
                  type="button"
                  aria-pressed={expandedTier === tier.tier}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span
                      className={cn(
                        "inline-flex items-center justify-center w-8 h-8 rounded-full text-white font-bold",
                        colors.bg
                      )}
                    >
                      {tier.tier}
                    </span>
                    <div>
                      <h3 className="font-semibold">{tier.title}</h3>
                      <p className="text-xs text-muted-foreground">
                        {tier.subtitle}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {tier.description}
                  </p>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Urgency Filter */}
      <fieldset className="flex items-center gap-2 mb-6 border-0 p-0 m-0">
        <legend className="text-sm text-muted-foreground">
          Filter by urgency:
        </legend>
        <Button
          variant={selectedUrgency === "all" ? "default" : "outline"}
          size="sm"
          onClick={() => setSelectedUrgency("all")}
          aria-pressed={selectedUrgency === "all"}
        >
          All
        </Button>
        <Button
          variant={selectedUrgency === "critical" ? "default" : "outline"}
          size="sm"
          className={selectedUrgency === "critical" ? "bg-red-500 hover:bg-red-600" : ""}
          onClick={() => setSelectedUrgency("critical")}
          aria-pressed={selectedUrgency === "critical"}
        >
          Critical
        </Button>
        <Button
          variant={selectedUrgency === "high" ? "default" : "outline"}
          size="sm"
          className={selectedUrgency === "high" ? "bg-orange-500 hover:bg-orange-600" : ""}
          onClick={() => setSelectedUrgency("high")}
          aria-pressed={selectedUrgency === "high"}
        >
          High
        </Button>
        <Button
          variant={selectedUrgency === "medium" ? "default" : "outline"}
          size="sm"
          className={selectedUrgency === "medium" ? "bg-yellow-500 hover:bg-yellow-600" : ""}
          onClick={() => setSelectedUrgency("medium")}
          aria-pressed={selectedUrgency === "medium"}
        >
          Medium
        </Button>
      </fieldset>

      {/* Tier Details */}
      <div className="space-y-8">
        {resistanceTiers.map((tier) => {
          const colors = tierColors[tier.color as keyof typeof tierColors];
          const filteredActions =
            selectedUrgency === "all"
              ? tier.actions
              : tier.actions.filter((a) => a.urgency === selectedUrgency);

          if (filteredActions.length === 0) return null;

          return (
            <Card key={tier.tier} className={cn("border-l-4", colors.border)}>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <span
                    className={cn(
                      "inline-flex items-center justify-center w-10 h-10 rounded-full text-white font-bold text-lg",
                      colors.bg
                    )}
                  >
                    {tier.tier}
                  </span>
                  <div>
                    <CardTitle>{tier.title}</CardTitle>
                    <p className="text-sm text-muted-foreground">
                      {tier.subtitle}
                    </p>
                  </div>
                </div>
                <p className="text-muted-foreground mt-2">{tier.description}</p>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2">
                  {filteredActions.map((action) => (
                    <ActionCard key={action.id} action={action} />
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Resources Section */}
      <section className="mt-12">
        <h2 className="text-2xl font-bold mb-6">Key Organizations</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Legal Defense</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                <li>
                  <a href="#" className="text-primary hover:underline">
                    ACLU
                  </a>
                </li>
                <li>
                  <a href="#" className="text-primary hover:underline">
                    Brennan Center for Justice
                  </a>
                </li>
                <li>
                  <a href="#" className="text-primary hover:underline">
                    Democracy Forward
                  </a>
                </li>
                <li>
                  <a href="#" className="text-primary hover:underline">
                    NAACP Legal Defense Fund
                  </a>
                </li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Voter Engagement</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                <li>
                  <a href="#" className="text-primary hover:underline">
                    Vote.org
                  </a>
                </li>
                <li>
                  <a href="#" className="text-primary hover:underline">
                    Rock the Vote
                  </a>
                </li>
                <li>
                  <a href="#" className="text-primary hover:underline">
                    League of Women Voters
                  </a>
                </li>
                <li>
                  <a href="#" className="text-primary hover:underline">
                    When We All Vote
                  </a>
                </li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Organizing</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                <li>
                  <a href="#" className="text-primary hover:underline">
                    Indivisible
                  </a>
                </li>
                <li>
                  <a href="#" className="text-primary hover:underline">
                    Swing Left
                  </a>
                </li>
                <li>
                  <a href="#" className="text-primary hover:underline">
                    Run for Something
                  </a>
                </li>
                <li>
                  <a href="#" className="text-primary hover:underline">
                    Sister District
                  </a>
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}

interface ActionCardProps {
  action: {
    id: string;
    title: string;
    description: string;
    urgency: string;
    effectiveness: number;
    resources: string[];
  };
}

function ActionCard({ action }: ActionCardProps) {
  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className="font-semibold">{action.title}</h4>
        <Badge
          className={cn(
            urgencyColors[action.urgency as keyof typeof urgencyColors]
          )}
        >
          {action.urgency}
        </Badge>
      </div>
      <p className="text-sm text-muted-foreground mb-3">{action.description}</p>

      {/* Effectiveness meter */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-muted-foreground">Effectiveness</span>
          <span className="font-medium">{action.effectiveness}%</span>
        </div>
        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 rounded-full"
            style={{ width: `${action.effectiveness}%` }}
          />
        </div>
      </div>

      {/* Resources */}
      <div className="flex flex-wrap gap-1">
        {action.resources.map((resource) => (
          <Badge key={resource} variant="outline" className="text-xs">
            {resource}
          </Badge>
        ))}
      </div>
    </div>
  );
}
