"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface APIState {
  code: string;
  name: string;
  bill_count: number;
  legislator_count: number;
  resistance_action_count: number;
}

interface StateDisplay {
  code: string;
  name: string;
  billCount: number;
  legislatorCount: number;
}

export default function StatesPage() {
  const [states, setStates] = useState<StateDisplay[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<"name" | "bills">("name");

  useEffect(() => {
    async function fetchStates() {
      try {
        const response = await fetch(`${API_BASE}/states`);
        if (response.ok) {
          const data = await response.json();
          const stateData: StateDisplay[] = data.items.map((s: APIState) => ({
            code: s.code.toUpperCase(),
            name: s.name,
            billCount: s.bill_count,
            legislatorCount: s.legislator_count,
          }));
          setStates(stateData);
        }
      } catch (error) {
        console.error("Error fetching states:", error);
      }
      setLoading(false);
    }
    fetchStates();
  }, []);

  const sortedStates = [...states].sort((a, b) => {
    if (sortBy === "name") return a.name.localeCompare(b.name);
    return b.billCount - a.billCount;
  });

  if (loading) {
    return (
      <div className="container py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">State Information</h1>
          <p className="text-muted-foreground">
            Browse state legislative data and activity
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(12)].map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="container py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">State Information</h1>
        <p className="text-muted-foreground">
          Browse state legislative data and activity
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-3 mb-8">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-3xl font-bold">{states.length}</p>
              <p className="text-sm text-muted-foreground">States & Territories</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-3xl font-bold">
                {states.reduce((sum, s) => sum + s.billCount, 0).toLocaleString()}
              </p>
              <p className="text-sm text-muted-foreground">Total Bills Tracked</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-3xl font-bold">
                {states.reduce((sum, s) => sum + s.legislatorCount, 0).toLocaleString()}
              </p>
              <p className="text-sm text-muted-foreground">Legislators</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Interactive Map */}
      {states.length > 0 && (
        <Card className="mb-8">
          <CardContent className="pt-6">
            <h2 className="text-lg font-semibold mb-2 text-center">
              Legislative Activity by State
            </h2>
            <p className="text-sm text-muted-foreground text-center mb-4">
              Interactive map is temporarily disabled while we improve compatibility.
            </p>
            <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              Map coming back soon. Use the state list below to browse details.
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sort Options */}
      <div className="flex justify-end gap-2 mb-6">
        <span className="text-sm text-muted-foreground self-center">Sort by:</span>
        <Button
          variant={sortBy === "name" ? "default" : "outline"}
          size="sm"
          onClick={() => setSortBy("name")}
        >
          Name
        </Button>
        <Button
          variant={sortBy === "bills" ? "default" : "outline"}
          size="sm"
          onClick={() => setSortBy("bills")}
        >
          Bill Count
        </Button>
      </div>

      {/* State Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {sortedStates.map((state) => (
          <Link key={state.code} href={`/states/${state.code.toLowerCase()}`}>
            <Card className="h-full transition-shadow hover:shadow-md cursor-pointer">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">{state.name}</h3>
                    <Badge variant="outline" className="mt-1">{state.code}</Badge>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-2xl font-bold">{state.billCount}</p>
                    <p className="text-muted-foreground">Bills</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{state.legislatorCount}</p>
                    <p className="text-muted-foreground">Legislators</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {states.length === 0 && !loading && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">
              No state data available. Check back later.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
