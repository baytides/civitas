"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatDate, snakeToTitle } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface ObjectiveDetail {
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
  keywords: string[];
  constitutional_concerns: string[];
  matching_eo_ids: number[];
  matching_legislation_ids: number[];
  implementation_notes: string | null;
  created_at: string;
  updated_at: string;
}

interface EOSummary {
  id: number;
  executive_order_number: number | null;
  title: string;
  signing_date: string | null;
}

export default function ObjectiveDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [objective, setObjective] = useState<ObjectiveDetail | null>(null);
  const [matchedEOs, setMatchedEOs] = useState<EOSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchObjective() {
      try {
        const response = await fetch(`${API_BASE}/objectives/${id}`);
        if (response.ok) {
          const data: ObjectiveDetail = await response.json();
          setObjective(data);

          // Fetch matched EOs if any
          if (data.matching_eo_ids && data.matching_eo_ids.length > 0) {
            const eoPromises = data.matching_eo_ids.map(async (eoId) => {
              try {
                const eoRes = await fetch(`${API_BASE}/executive-orders/${eoId}`);
                if (eoRes.ok) {
                  const eoData = await eoRes.json();
                  return {
                    id: eoData.id,
                    executive_order_number: eoData.executive_order_number,
                    title: eoData.title,
                    signing_date: eoData.signing_date,
                  } as EOSummary;
                }
              } catch {
                // skip failed EO fetches
              }
              return null;
            });
            const eos = (await Promise.all(eoPromises)).filter(Boolean) as EOSummary[];
            setMatchedEOs(eos);
          }
        } else if (response.status === 404) {
          setError("Policy not found");
        } else {
          setError("Failed to load policy details");
        }
      } catch {
        setError("Failed to connect to server");
      }
      setLoading(false);
    }

    if (id) fetchObjective();
  }, [id]);

  if (loading) {
    return (
      <div className="container py-8">
        <Skeleton className="h-4 w-48 mb-6" />
        <div className="grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <div>
              <div className="flex gap-2 mb-3">
                <Skeleton className="h-6 w-20" />
                <Skeleton className="h-6 w-24" />
              </div>
              <Skeleton className="h-8 w-3/4 mb-4" />
              <Skeleton className="h-20 w-full" />
            </div>
          </div>
          <div>
            <Skeleton className="h-48 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !objective) {
    return (
      <div className="container py-8">
        <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
          <Link href="/tracker" className="hover:text-foreground">
            Tracker
          </Link>
          <span>/</span>
          <span className="text-foreground">Not Found</span>
        </nav>
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground text-lg">
              {error || "Policy not found"}
            </p>
            <Link href="/tracker">
              <Button variant="outline" className="mt-4">
                Back to Tracker
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const statusVariant = objective.status === "enacted"
    ? "enacted"
    : objective.status === "in_progress"
      ? "in_progress"
      : objective.status === "blocked"
        ? "blocked"
        : "proposed";

  const priorityColors: Record<string, string> = {
    high: "text-red-600",
    medium: "text-orange-600",
    low: "text-muted-foreground",
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
        <span className="text-foreground">Policy #{objective.id}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Header */}
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-3">
              <Badge variant="outline">{snakeToTitle(objective.category)}</Badge>
              <Badge variant={statusVariant as "enacted" | "in_progress" | "proposed" | "blocked"}>
                {snakeToTitle(objective.status)}
              </Badge>
              <Badge variant="outline">{snakeToTitle(objective.priority)} Priority</Badge>
            </div>

            <h1 className="text-2xl font-bold mb-4">
              {objective.proposal_summary || objective.proposal_text.slice(0, 150)}
            </h1>

            <div className="p-4 rounded-lg bg-muted/50 border">
              <p className="text-sm font-medium text-muted-foreground mb-1">Full Proposal Text</p>
              <p className="text-sm">{objective.proposal_text}</p>
            </div>

            <div className="flex flex-wrap gap-4 mt-4 text-sm text-muted-foreground">
              <span>
                <strong>Source:</strong> {objective.section}
                {objective.chapter && `, ${objective.chapter}`}
              </span>
              <span>
                <strong>Page:</strong> {objective.page_number}
              </span>
              <span>
                <strong>Agency:</strong> {objective.agency}
              </span>
            </div>
          </div>

          {/* Constitutional Concerns */}
          {objective.constitutional_concerns.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Constitutional Concerns</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {objective.constitutional_concerns.map((concern, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm">
                      <span className="w-1.5 h-1.5 rounded-full bg-red-500 mt-1.5 shrink-0" />
                      {concern}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Related Executive Orders */}
          <Card>
            <CardHeader>
              <CardTitle>Related Executive Orders</CardTitle>
            </CardHeader>
            <CardContent>
              {matchedEOs.length > 0 ? (
                <div className="space-y-3">
                  {matchedEOs.map((eo) => (
                    <Link
                      key={eo.id}
                      href={`/executive-orders/${eo.id}`}
                      className="block p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="font-medium">
                            {eo.executive_order_number
                              ? `EO ${eo.executive_order_number}: ${eo.title}`
                              : eo.title}
                          </p>
                          {eo.signing_date && (
                            <p className="text-sm text-muted-foreground">
                              Signed {formatDate(eo.signing_date)}
                            </p>
                          )}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">
                  No related executive orders tracked
                </p>
              )}
            </CardContent>
          </Card>

          {/* Keywords */}
          {objective.keywords.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Keywords</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {objective.keywords.map((keyword, idx) => (
                    <Badge key={idx} variant="outline" className="text-xs">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Details Card */}
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <Badge variant={statusVariant as "enacted" | "in_progress" | "proposed" | "blocked"}>
                  {snakeToTitle(objective.status)}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Priority</p>
                <p className={cn("font-medium", priorityColors[objective.priority] || "")}>
                  {snakeToTitle(objective.priority)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Action Type</p>
                <p className="font-medium">{snakeToTitle(objective.action_type)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Timeline</p>
                <p className="font-medium">{snakeToTitle(objective.implementation_timeline)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Confidence</p>
                <p className="font-medium">{Math.round(objective.confidence * 100)}%</p>
              </div>
              {objective.implementation_notes && (
                <div>
                  <p className="text-sm text-muted-foreground">Notes</p>
                  <p className="text-sm">{objective.implementation_notes}</p>
                </div>
              )}
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
              <p className="text-sm text-muted-foreground">
                Help resist the implementation of this policy proposal.
              </p>
              <Link href="/resistance">
                <Button className="w-full" variant="action">
                  View Resistance Strategy
                </Button>
              </Link>
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
