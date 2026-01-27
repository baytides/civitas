"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface StateBill {
  id: number;
  identifier: string;
  title: string | null;
  chamber: string;
  session: string;
  status: string | null;
  introduced_date: string | null;
}

interface StateLegislator {
  id: number;
  full_name: string;
  chamber: string;
  district: string | null;
  party: string;
  state: string;
}

interface StateDetail {
  code: string;
  name: string;
  bill_count: number;
  legislator_count: number;
  resistance_action_count: number;
  recent_bills: StateBill[];
  legislators: StateLegislator[];
}

export default function StateDetailPage() {
  const params = useParams();
  const code = params.code as string;
  const [state, setState] = useState<StateDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchState() {
      try {
        const response = await fetch(`${API_BASE}/states/${code}`);
        if (response.ok) {
          setState(await response.json());
        } else if (response.status === 404) {
          setError("State not found");
        } else {
          setError("Failed to load state data");
        }
      } catch {
        setError("Failed to connect to server");
      }
      setLoading(false);
    }

    if (code) fetchState();
  }, [code]);

  if (loading) {
    return (
      <div className="container py-8">
        <Skeleton className="h-4 w-48 mb-6" />
        <div className="grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-10 w-48 mb-4" />
            <div className="grid grid-cols-3 gap-4">
              <Skeleton className="h-20" />
              <Skeleton className="h-20" />
              <Skeleton className="h-20" />
            </div>
            <Skeleton className="h-48 w-full" />
          </div>
          <div>
            <Skeleton className="h-48 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !state) {
    return (
      <div className="container py-8">
        <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
          <Link href="/states" className="hover:text-foreground">
            States
          </Link>
          <span>/</span>
          <span className="text-foreground">Not Found</span>
        </nav>
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground text-lg">
              {error || "State not found"}
            </p>
            <Link href="/states">
              <Button variant="outline" className="mt-4">
                Back to All States
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Group legislators by chamber
  const senateMembers = state.legislators.filter(l => l.chamber.toLowerCase() === "senate" || l.chamber.toLowerCase() === "upper");
  const houseMembers = state.legislators.filter(l => l.chamber.toLowerCase() !== "senate" && l.chamber.toLowerCase() !== "upper");

  return (
    <div className="container py-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
        <Link href="/states" className="hover:text-foreground">
          States
        </Link>
        <span>/</span>
        <span className="text-foreground">{state.name}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <h1 className="text-3xl font-bold mb-4">{state.name}</h1>

            {/* Quick Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 rounded-lg border text-center">
                <p className="text-2xl font-bold">{state.bill_count}</p>
                <p className="text-sm text-muted-foreground">Bills Tracked</p>
              </div>
              <div className="p-4 rounded-lg border text-center">
                <p className="text-2xl font-bold">{state.legislator_count}</p>
                <p className="text-sm text-muted-foreground">Legislators</p>
              </div>
              <div className="p-4 rounded-lg border text-center">
                <p className="text-2xl font-bold">{state.resistance_action_count}</p>
                <p className="text-sm text-muted-foreground">Actions</p>
              </div>
            </div>
          </div>

          {/* Recent Bills */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Bills</CardTitle>
            </CardHeader>
            <CardContent>
              {state.recent_bills.length > 0 ? (
                <div className="space-y-3">
                  {state.recent_bills.map((bill) => (
                    <div
                      key={bill.id}
                      className="p-3 rounded-lg border"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="font-medium">{bill.identifier}</p>
                          {bill.title && (
                            <p className="text-sm text-muted-foreground mt-1">
                              {bill.title}
                            </p>
                          )}
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="outline" className="text-xs">
                              {bill.chamber}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {bill.session}
                            </span>
                            {bill.introduced_date && (
                              <span className="text-xs text-muted-foreground">
                                {formatDate(bill.introduced_date)}
                              </span>
                            )}
                          </div>
                        </div>
                        {bill.status && (
                          <Badge variant="outline" className="shrink-0 text-xs">
                            {bill.status}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">No bills tracked for this state</p>
              )}
            </CardContent>
          </Card>

          {/* Legislators */}
          {state.legislators.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Legislators</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {senateMembers.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-2">
                      Senate ({senateMembers.length})
                    </p>
                    <div className="space-y-1">
                      {senateMembers.slice(0, 20).map((leg) => (
                        <div
                          key={leg.id}
                          className="flex items-center justify-between p-2 rounded border text-sm"
                        >
                          <span className="font-medium">{leg.full_name}</span>
                          <div className="flex items-center gap-2">
                            {leg.district && (
                              <span className="text-xs text-muted-foreground">
                                Dist. {leg.district}
                              </span>
                            )}
                            <Badge
                              variant="outline"
                              className={
                                leg.party === "D" || leg.party === "Democratic"
                                  ? "border-blue-500 text-blue-600"
                                  : leg.party === "R" || leg.party === "Republican"
                                    ? "border-red-500 text-red-600"
                                    : ""
                              }
                            >
                              {leg.party}
                            </Badge>
                          </div>
                        </div>
                      ))}
                      {senateMembers.length > 20 && (
                        <p className="text-xs text-muted-foreground text-center pt-1">
                          and {senateMembers.length - 20} more
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {houseMembers.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-2">
                      House/Assembly ({houseMembers.length})
                    </p>
                    <div className="space-y-1">
                      {houseMembers.slice(0, 20).map((leg) => (
                        <div
                          key={leg.id}
                          className="flex items-center justify-between p-2 rounded border text-sm"
                        >
                          <span className="font-medium">{leg.full_name}</span>
                          <div className="flex items-center gap-2">
                            {leg.district && (
                              <span className="text-xs text-muted-foreground">
                                Dist. {leg.district}
                              </span>
                            )}
                            <Badge
                              variant="outline"
                              className={
                                leg.party === "D" || leg.party === "Democratic"
                                  ? "border-blue-500 text-blue-600"
                                  : leg.party === "R" || leg.party === "Republican"
                                    ? "border-red-500 text-red-600"
                                    : ""
                              }
                            >
                              {leg.party}
                            </Badge>
                          </div>
                        </div>
                      ))}
                      {houseMembers.length > 20 && (
                        <p className="text-xs text-muted-foreground text-center pt-1">
                          and {houseMembers.length - 20} more
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card className="border-green-500/50">
            <CardHeader>
              <CardTitle>Take Action in {state.name}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Support resistance efforts in your state.
              </p>
              <Link href="/resistance">
                <Button className="w-full" variant="action">
                  View Resistance Strategy
                </Button>
              </Link>
              <Button className="w-full" variant="outline">
                Contact Your Representatives
              </Button>
            </CardContent>
          </Card>

          <Link href="/states">
            <Button variant="outline" className="w-full">
              Back to All States
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
