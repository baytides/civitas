"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, snakeToTitle } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface MatchedObjective {
  id: number;
  section: string;
  agency: string;
  proposal_text: string;
  proposal_summary: string | null;
  category: string;
  status: string;
  priority: string;
}

interface ExecutiveOrderDetail {
  id: number;
  document_number: string;
  executive_order_number: number | null;
  title: string;
  signing_date: string | null;
  publication_date: string | null;
  president: string | null;
  abstract: string | null;
  pdf_url: string | null;
  html_url: string | null;
  matched_objectives: MatchedObjective[];
}

export default function ExecutiveOrderDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [eo, setEO] = useState<ExecutiveOrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchEO() {
      try {
        const response = await fetch(`${API_BASE}/executive-orders/${id}`);
        if (response.ok) {
          setEO(await response.json());
        } else if (response.status === 404) {
          setError("Executive order not found");
        } else {
          setError("Failed to load executive order");
        }
      } catch {
        setError("Failed to connect to server");
      }
      setLoading(false);
    }

    if (id) fetchEO();
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

  if (error || !eo) {
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
              {error || "Executive order not found"}
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

  const displayNumber = eo.executive_order_number
    ? `EO ${eo.executive_order_number}`
    : eo.document_number;

  return (
    <div className="container py-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
        <Link href="/tracker" className="hover:text-foreground">
          Tracker
        </Link>
        <span>/</span>
        <span>Executive Orders</span>
        <span>/</span>
        <span className="text-foreground">{displayNumber}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-3">
              <Badge variant="destructive">EXECUTIVE ORDER</Badge>
              {eo.president && <Badge variant="outline">{eo.president}</Badge>}
            </div>

            <h1 className="text-3xl font-bold mb-2">{displayNumber}</h1>
            <h2 className="text-xl text-muted-foreground mb-4">{eo.title}</h2>

            {eo.abstract && (
              <p className="text-muted-foreground">{eo.abstract}</p>
            )}
          </div>

          {/* Matched P2025 Objectives */}
          <Card>
            <CardHeader>
              <CardTitle>Related P2025 Objectives</CardTitle>
            </CardHeader>
            <CardContent>
              {eo.matched_objectives.length > 0 ? (
                <div className="space-y-3">
                  {eo.matched_objectives.map((obj) => (
                    <Link
                      key={obj.id}
                      href={`/tracker/${obj.id}`}
                      className="block p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
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
                        </div>
                        <Badge
                          variant={
                            obj.status === "enacted"
                              ? "enacted"
                              : obj.status === "blocked"
                                ? "blocked"
                                : "proposed"
                          }
                          className="shrink-0"
                        >
                          {snakeToTitle(obj.status)}
                        </Badge>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">
                  No matched P2025 objectives
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {eo.executive_order_number && (
                <div>
                  <p className="text-sm text-muted-foreground">Order Number</p>
                  <p className="font-medium">EO {eo.executive_order_number}</p>
                </div>
              )}
              <div>
                <p className="text-sm text-muted-foreground">Document Number</p>
                <p className="font-medium">{eo.document_number}</p>
              </div>
              {eo.signing_date && (
                <div>
                  <p className="text-sm text-muted-foreground">Signed</p>
                  <p className="font-medium">{formatDate(eo.signing_date)}</p>
                </div>
              )}
              {eo.publication_date && (
                <div>
                  <p className="text-sm text-muted-foreground">Published</p>
                  <p className="font-medium">{formatDate(eo.publication_date)}</p>
                </div>
              )}
              {eo.president && (
                <div>
                  <p className="text-sm text-muted-foreground">President</p>
                  <p className="font-medium">{eo.president}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Resources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {eo.html_url && (
                <Button className="w-full" variant="outline" asChild>
                  <a href={eo.html_url} target="_blank" rel="noopener noreferrer">
                    View Full Text
                  </a>
                </Button>
              )}
              {eo.pdf_url && (
                <Button className="w-full" variant="outline" asChild>
                  <a href={eo.pdf_url} target="_blank" rel="noopener noreferrer">
                    Download PDF
                  </a>
                </Button>
              )}
              {!eo.html_url && !eo.pdf_url && (
                <p className="text-sm text-muted-foreground text-center">
                  No full text available
                </p>
              )}
              <Link href="/resistance">
                <Button className="w-full" variant="action">
                  Take Action
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
