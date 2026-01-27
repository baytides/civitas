import Link from "next/link";
import { notFound } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn, formatDate, formatPercentage, snakeToTitle } from "@/lib/utils";

// Mock data - will be replaced with API call
const mockObjective = {
  id: "ed-1",
  category: "education",
  subcategory: "federal",
  title: "Eliminate Department of Education",
  description:
    "The Project 2025 Mandate for Leadership calls for the complete abolition of the federal Department of Education. This would transfer all education policy authority to individual states, eliminate federal student loan programs, end Title I funding, and remove federal oversight of educational civil rights protections.",
  sourcePage: 319,
  implementationStatus: "in_progress",
  threatLevel: "critical",
  progressPercentage: 35,
  relatedLegislation: [
    {
      id: 1,
      title: "H.R. 899 - To terminate the Department of Education",
      status: "proposed",
      jurisdiction: "federal",
    },
    {
      id: 2,
      title: "S. 323 - Education Freedom Act",
      status: "proposed",
      jurisdiction: "federal",
    },
  ],
  relatedExecutiveOrders: [
    {
      id: 1,
      orderNumber: 14567,
      title: "Executive Order on Education Policy Review",
      signingDate: "2025-01-25",
      status: "active",
    },
  ],
  relatedCourtCases: [
    {
      id: 1,
      citation: "2025 WL 123456",
      caseName: "State of California v. Department of Education",
      court: "Ninth Circuit",
      status: "pending",
    },
  ],
  resistanceActions: [
    {
      id: "ra-1",
      tier: 1,
      title: "Contact Your Senator",
      description: "Call your senators to oppose education defunding bills",
      urgency: "high",
    },
    {
      id: "ra-2",
      tier: 1,
      title: "Support State Protections",
      description: "Advocate for state-level education funding guarantees",
      urgency: "medium",
    },
  ],
  timeline: [
    {
      date: "2025-01-25",
      eventType: "executive_order",
      title: "Education Policy Review Executive Order Signed",
      description: "President signs EO directing review of all federal education programs",
    },
    {
      date: "2025-01-20",
      eventType: "objective",
      title: "Status Changed to In Progress",
      description: "Multiple executive actions signal active implementation",
    },
    {
      date: "2025-01-15",
      eventType: "legislation",
      title: "H.R. 899 Reintroduced",
      description: "Bill to terminate Department of Education reintroduced in new Congress",
    },
  ],
};

export default async function ObjectiveDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  // In production, fetch from API
  // const objective = await api.objectives.get(id);
  const objective = mockObjective;

  if (!objective) {
    notFound();
  }

  const threatColors = {
    critical: "bg-red-500",
    high: "bg-orange-500",
    elevated: "bg-yellow-500",
    moderate: "bg-green-500",
  };

  return (
    <div className="container py-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
        <Link href="/tracker" className="hover:text-foreground">
          Tracker
        </Link>
        <span>/</span>
        <Link
          href={`/tracker?category=${objective.category}`}
          className="hover:text-foreground"
        >
          {snakeToTitle(objective.category)}
        </Link>
        <span>/</span>
        <span className="text-foreground">{objective.title}</span>
      </nav>

      {/* Header */}
      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          {/* Title & Status */}
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-3">
              <Badge variant="outline">{snakeToTitle(objective.category)}</Badge>
              <Badge
                variant={
                  objective.implementationStatus as
                    | "enacted"
                    | "in_progress"
                    | "proposed"
                    | "blocked"
                }
              >
                {snakeToTitle(objective.implementationStatus)}
              </Badge>
              <Badge
                variant={
                  objective.threatLevel as
                    | "critical"
                    | "high"
                    | "elevated"
                    | "moderate"
                }
              >
                {objective.threatLevel.toUpperCase()} THREAT
              </Badge>
            </div>

            <h1 className="text-3xl font-bold mb-4">{objective.title}</h1>
            <p className="text-muted-foreground">{objective.description}</p>

            <p className="text-sm text-muted-foreground mt-4">
              <strong>Source:</strong> Mandate for Leadership, page{" "}
              {objective.sourcePage}
            </p>
          </div>

          {/* Related Legislation */}
          <Card>
            <CardHeader>
              <CardTitle>Related Legislation</CardTitle>
            </CardHeader>
            <CardContent>
              {objective.relatedLegislation.length > 0 ? (
                <div className="space-y-3">
                  {objective.relatedLegislation.map((leg) => (
                    <Link
                      key={leg.id}
                      href={`/legislation/${leg.id}`}
                      className="block p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="font-medium">{leg.title}</p>
                          <p className="text-sm text-muted-foreground">
                            {leg.jurisdiction}
                          </p>
                        </div>
                        <Badge
                          variant={
                            leg.status as "enacted" | "proposed" | "in_progress" | "blocked"
                          }
                        >
                          {snakeToTitle(leg.status)}
                        </Badge>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">
                  No related legislation tracked
                </p>
              )}
            </CardContent>
          </Card>

          {/* Related Executive Orders */}
          <Card>
            <CardHeader>
              <CardTitle>Related Executive Orders</CardTitle>
            </CardHeader>
            <CardContent>
              {objective.relatedExecutiveOrders.length > 0 ? (
                <div className="space-y-3">
                  {objective.relatedExecutiveOrders.map((eo) => (
                    <Link
                      key={eo.id}
                      href={`/executive-orders/${eo.id}`}
                      className="block p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="font-medium">
                            EO {eo.orderNumber}: {eo.title}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            Signed {formatDate(eo.signingDate)}
                          </p>
                        </div>
                        <Badge variant="destructive">{eo.status}</Badge>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">
                  No related executive orders
                </p>
              )}
            </CardContent>
          </Card>

          {/* Related Court Cases */}
          <Card>
            <CardHeader>
              <CardTitle>Related Court Cases</CardTitle>
            </CardHeader>
            <CardContent>
              {objective.relatedCourtCases.length > 0 ? (
                <div className="space-y-3">
                  {objective.relatedCourtCases.map((courtCase) => (
                    <Link
                      key={courtCase.id}
                      href={`/cases/${courtCase.id}`}
                      className="block p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="font-medium">{courtCase.caseName}</p>
                          <p className="text-sm text-muted-foreground">
                            {courtCase.court} • {courtCase.citation}
                          </p>
                        </div>
                        <Badge variant="outline">{courtCase.status}</Badge>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">No related court cases</p>
              )}
            </CardContent>
          </Card>

          {/* Timeline */}
          <Card>
            <CardHeader>
              <CardTitle>Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-0">
                {objective.timeline.map((event, index) => (
                  <div key={index} className="timeline-item">
                    <div className="timeline-dot" />
                    <div className="mb-1">
                      <span className="text-xs text-muted-foreground">
                        {formatDate(event.date)}
                      </span>
                      <Badge variant="outline" className="ml-2 text-xs">
                        {snakeToTitle(event.eventType)}
                      </Badge>
                    </div>
                    <h4 className="font-medium">{event.title}</h4>
                    <p className="text-sm text-muted-foreground">
                      {event.description}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Progress Card */}
          <Card>
            <CardHeader>
              <CardTitle>Implementation Progress</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center mb-4">
                <span
                  className={cn(
                    "text-4xl font-bold",
                    objective.progressPercentage > 50
                      ? "text-red-600"
                      : objective.progressPercentage > 25
                        ? "text-orange-600"
                        : "text-muted-foreground"
                  )}
                >
                  {formatPercentage(objective.progressPercentage)}
                </span>
              </div>
              <div className="h-3 bg-muted rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    threatColors[
                      objective.threatLevel as keyof typeof threatColors
                    ]
                  )}
                  style={{ width: `${objective.progressPercentage}%` }}
                />
              </div>
              <p className="text-sm text-muted-foreground mt-3 text-center">
                Based on legislative, executive, and judicial actions
              </p>
            </CardContent>
          </Card>

          {/* Take Action */}
          <Card className="border-green-500/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldIcon className="h-5 w-5 text-green-500" />
                Take Action
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {objective.resistanceActions.map((action) => (
                <div
                  key={action.id}
                  className="p-3 rounded-lg border bg-green-50 dark:bg-green-950/20"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Badge
                      className={cn(
                        "text-xs",
                        action.urgency === "high"
                          ? "bg-orange-500"
                          : action.urgency === "medium"
                            ? "bg-yellow-500"
                            : "bg-blue-500"
                      )}
                    >
                      {action.urgency}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      Tier {action.tier}
                    </span>
                  </div>
                  <h4 className="font-medium">{action.title}</h4>
                  <p className="text-sm text-muted-foreground">
                    {action.description}
                  </p>
                </div>
              ))}
              <Link href="/resistance">
                <Button className="w-full mt-2" variant="action">
                  View All Actions
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* Share */}
          <Card>
            <CardHeader>
              <CardTitle>Share</CardTitle>
            </CardHeader>
            <CardContent className="flex gap-2">
              <Button variant="outline" size="sm" className="flex-1">
                Copy Link
              </Button>
              <Button variant="outline" size="sm" className="flex-1">
                Twitter
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function ShieldIcon({ className }: { className?: string }) {
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
        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
      />
    </svg>
  );
}
