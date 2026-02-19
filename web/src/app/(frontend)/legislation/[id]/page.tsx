"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, snakeToTitle } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://api.projectcivitas.com/api/v1";

interface LegislationAction {
  action_date: string;
  action_text: string;
  action_code: string | null;
}

interface LegislationDetail {
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
  source_url: string | null;
  summary: string | null;
  full_text: string | null;
  policy_area: string | null;
  subjects: string[];
  actions: LegislationAction[];
  plain_summary?: string | null;
  why_this_matters?: string | null;
  key_impacts?: string[];
  insight_generated_at?: string | null;
  updated_at?: string | null;
}

interface ObjectiveSummary {
  id: number;
  proposal_summary: string | null;
  proposal_text: string;
  category: string;
  agency: string;
  status: string;
}

export default function LegislationDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [legislation, setLegislation] = useState<LegislationDetail | null>(null);
  const [objectives, setObjectives] = useState<ObjectiveSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchLegislation() {
      try {
        const response = await fetch(`${API_BASE}/legislation/${id}`);
        if (response.ok) {
          const data: LegislationDetail = await response.json();
          setLegislation(data);

          try {
            const objRes = await fetch(
              `${API_BASE}/objectives?legislation_id=${id}&per_page=50`
            );
            if (objRes.ok) {
              const objData = await objRes.json();
              setObjectives(objData.items || []);
            }
          } catch {
            // ignore objective fetch failures
          }
        } else if (response.status === 404) {
          setError("This item is still being processed. Check back soon.");
        } else {
          setError("Failed to load legislation");
        }
      } catch {
        setError("Failed to connect to server");
      }
      setLoading(false);
    }

    if (id) fetchLegislation();
  }, [id]);

  if (loading) {
    return (
      <div className="container py-8">
        <Skeleton className="h-4 w-48 mb-6" />
        <div className="grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-20 w-full" />
          </div>
          <div>
            <Skeleton className="h-48 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !legislation) {
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
              {error || "Legislation not found"}
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
      <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
        <Link href="/tracker" className="hover:text-foreground">
          Tracker
        </Link>
        <span>/</span>
        <span>Legislation</span>
        <span>/</span>
        <span className="text-foreground">{legislation.citation}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-3">
              <Badge variant="outline">{snakeToTitle(legislation.jurisdiction)}</Badge>
              <Badge variant="outline">{snakeToTitle(legislation.chamber)}</Badge>
              {legislation.status && (
                <Badge variant="outline">{snakeToTitle(legislation.status)}</Badge>
              )}
              {legislation.is_enacted && <Badge variant="enacted">Enacted</Badge>}
            </div>
            <h1 className="text-2xl font-bold mb-2">
              {legislation.title || legislation.citation}
            </h1>
            {legislation.plain_summary ? (
              <p className="text-muted-foreground">{legislation.plain_summary}</p>
            ) : legislation.summary ? (
              <p className="text-muted-foreground">{legislation.summary}</p>
            ) : null}
          </div>

          {(legislation.why_this_matters || (legislation.key_impacts || []).length > 0) && (
            <Card>
              <CardHeader>
                <CardTitle>Why This Matters</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {legislation.why_this_matters && (
                  <p className="text-sm">{legislation.why_this_matters}</p>
                )}
                {(legislation.key_impacts || []).length > 0 && (
                  <ul className="space-y-2">
                    {legislation.key_impacts?.map((impact, idx) => (
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

          {objectives.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Related Project 2025 Objectives</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {objectives.map((obj) => (
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

          {legislation.actions.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Recent Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {legislation.actions.map((action, idx) => (
                  <div key={`${action.action_date}-${idx}`} className="text-sm">
                    <p className="text-muted-foreground">
                      {formatDate(action.action_date)}
                    </p>
                    <p>{action.action_text}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm text-muted-foreground">Citation</p>
                <p className="font-medium">{legislation.citation}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Session</p>
                <p className="font-medium">{legislation.session}</p>
              </div>
              {legislation.policy_area && (
                <div>
                  <p className="text-sm text-muted-foreground">Policy Area</p>
                  <p className="font-medium">{legislation.policy_area}</p>
                </div>
              )}
              {legislation.introduced_date && (
                <div>
                  <p className="text-sm text-muted-foreground">Introduced</p>
                  <p className="font-medium">{formatDate(legislation.introduced_date)}</p>
                </div>
              )}
              {legislation.enacted_date && (
                <div>
                  <p className="text-sm text-muted-foreground">Enacted</p>
                  <p className="font-medium">{formatDate(legislation.enacted_date)}</p>
                </div>
              )}
              {legislation.subjects.length > 0 && (
                <div>
                  <p className="text-sm text-muted-foreground">Subjects</p>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {legislation.subjects.map((subject) => (
                      <Badge key={subject} variant="outline" className="text-xs">
                        {subject}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {legislation.updated_at && (
                <div className="pt-2 border-t">
                  <p className="text-xs text-muted-foreground">
                    Last updated: {formatDate(legislation.updated_at)}
                  </p>
                  {legislation.insight_generated_at && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Insight generated: {formatDate(legislation.insight_generated_at)}
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {legislation.source_url && (
            <Card>
              <CardHeader>
                <CardTitle>Resources</CardTitle>
              </CardHeader>
              <CardContent>
                <Button className="w-full" variant="outline" asChild>
                  <a
                    href={legislation.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View Source
                  </a>
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
