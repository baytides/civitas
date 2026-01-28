"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, snakeToTitle } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface LinkedObjective {
  id: number;
  section: string;
  agency: string;
  proposal_text: string;
  proposal_summary: string | null;
  category: string;
  status: string;
}

interface CourtCaseDetail {
  id: number;
  citation: string;
  case_name: string;
  court_level: string;
  court: string;
  decision_date: string | null;
  status: string | null;
  docket_number: string | null;
  holding: string | null;
  majority_author: string | null;
  dissent_author: string | null;
  source_url: string | null;
  linked_objectives: LinkedObjective[];
  plain_summary?: string | null;
  why_this_matters?: string | null;
  key_impacts?: string[];
  insight_generated_at?: string | null;
  updated_at?: string | null;
}

export default function CaseDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [courtCase, setCourtCase] = useState<CourtCaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchCase() {
      try {
        const response = await fetch(`${API_BASE}/cases/${id}`);
        if (response.ok) {
          setCourtCase(await response.json());
        } else if (response.status === 404) {
          setError("Court case not found");
        } else {
          setError("Failed to load court case");
        }
      } catch {
        setError("Failed to connect to server");
      }
      setLoading(false);
    }

    if (id) fetchCase();
  }, [id]);

  if (loading) {
    return (
      <div className="container py-8">
        <Skeleton className="h-4 w-48 mb-6" />
        <div className="grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <div>
              <Skeleton className="h-6 w-32 mb-3" />
              <Skeleton className="h-8 w-3/4 mb-2" />
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

  if (error || !courtCase) {
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
              {error || "Court case not found"}
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

  return (
    <div className="container py-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
        <Link href="/tracker" className="hover:text-foreground">
          Tracker
        </Link>
        <span>/</span>
        <span>Court Cases</span>
        <span>/</span>
        <span className="text-foreground truncate max-w-[200px]">
          {courtCase.case_name}
        </span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-3">
              {courtCase.status && (
                <Badge variant="outline">{courtCase.status.toUpperCase()}</Badge>
              )}
              <Badge variant="outline">
                {snakeToTitle(courtCase.court_level)}
              </Badge>
            </div>

            <h1 className="text-2xl font-bold mb-2">{courtCase.case_name}</h1>
            <p className="text-muted-foreground mb-4">{courtCase.citation}</p>

            {courtCase.holding && (
              <div className="p-4 rounded-lg bg-muted/50 border">
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  Holding
                </p>
                <p className="text-sm">{courtCase.holding}</p>
              </div>
            )}
          </div>

          {/* Why This Matters */}
          {(courtCase.why_this_matters || (courtCase.key_impacts || []).length > 0) && (
            <Card>
              <CardHeader>
                <CardTitle>Why This Matters</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {courtCase.plain_summary && (
                  <p className="text-sm text-muted-foreground">{courtCase.plain_summary}</p>
                )}
                {courtCase.why_this_matters && (
                  <p className="text-sm">{courtCase.why_this_matters}</p>
                )}
                {(courtCase.key_impacts || []).length > 0 && (
                  <ul className="space-y-2">
                    {courtCase.key_impacts?.map((impact, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
                        {impact}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          )}

          {/* Related Project 2025 Objectives */}
          {courtCase.linked_objectives.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Related Project 2025 Objectives</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {courtCase.linked_objectives.map((obj) => (
                    <Link
                      key={obj.id}
                      href={`/tracker/${obj.id}`}
                      className="block p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                    >
                      <p className="font-medium">
                        {obj.proposal_summary || obj.proposal_text.slice(0, 120) + "..."}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {snakeToTitle(obj.category)}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {obj.agency}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Case Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm text-muted-foreground">Court</p>
                <p className="font-medium text-sm">{courtCase.court}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Court Level</p>
                <p className="font-medium">{snakeToTitle(courtCase.court_level)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Citation</p>
                <p className="font-medium">{courtCase.citation}</p>
              </div>
              {courtCase.docket_number && (
                <div>
                  <p className="text-sm text-muted-foreground">Docket</p>
                  <p className="font-medium">{courtCase.docket_number}</p>
                </div>
              )}
              {courtCase.decision_date && (
                <div>
                  <p className="text-sm text-muted-foreground">Decision Date</p>
                  <p className="font-medium">{formatDate(courtCase.decision_date)}</p>
                </div>
              )}
              {courtCase.status && (
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <Badge variant="outline">{courtCase.status}</Badge>
                </div>
              )}
              {courtCase.majority_author && (
                <div>
                  <p className="text-sm text-muted-foreground">Majority Author</p>
                  <p className="font-medium">{courtCase.majority_author}</p>
                </div>
              )}
              {courtCase.dissent_author && (
                <div>
                  <p className="text-sm text-muted-foreground">Dissent Author</p>
                  <p className="font-medium">{courtCase.dissent_author}</p>
                </div>
              )}
              {courtCase.updated_at && (
                <div className="pt-2 border-t">
                  <p className="text-xs text-muted-foreground">
                    Last updated: {formatDate(courtCase.updated_at)}
                  </p>
                  {courtCase.insight_generated_at && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Insight generated: {formatDate(courtCase.insight_generated_at)}
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {courtCase.source_url && (
            <Card>
              <CardHeader>
                <CardTitle>Resources</CardTitle>
              </CardHeader>
              <CardContent>
                <Button className="w-full" variant="outline" asChild>
                  <a
                    href={courtCase.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View Source
                  </a>
                </Button>
              </CardContent>
            </Card>
          )}

          <Card className="border-green-500/50">
            <CardHeader>
              <CardTitle>Support Legal Action</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Legal challenges are critical to defending democracy.
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
