"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface JusticeAPI {
  id: number;
  name: string;
  slug: string;
  role?: string | null;
  is_active: boolean;
  official_photo_url?: string | null;
}

export default function JusticesPage() {
  const [justices, setJustices] = useState<JusticeAPI[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchJustices() {
      try {
        const response = await fetch(`${API_BASE}/justices?per_page=200`);
        if (response.ok) {
          const data = await response.json();
          setJustices(data.items || []);
        }
      } catch (error) {
        console.error("Error fetching justices:", error);
      }
      setLoading(false);
    }
    fetchJustices();
  }, []);

  if (loading) {
    return (
      <div className="container py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Supreme Court Justices</h1>
          <p className="text-muted-foreground">
            Profiles and analytical summaries of the current Court.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(9)].map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      </div>
    );
  }

  const active = justices.filter((justice) => justice.is_active);
  const inactive = justices.filter((justice) => !justice.is_active);

  return (
    <div className="container py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Supreme Court Justices</h1>
        <p className="text-muted-foreground">
          Profiles and analytical summaries of the Court based on published opinions.
        </p>
      </div>

      <div className="mb-10">
        <h2 className="text-xl font-semibold mb-4">Active Justices</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {active.map((justice) => (
            <Link key={justice.id} href={`/justices/${justice.slug}`}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    {justice.official_photo_url ? (
                      <img
                        src={justice.official_photo_url}
                        alt={justice.name}
                        className="h-16 w-16 rounded-full object-cover"
                      />
                    ) : (
                      <div className="h-16 w-16 rounded-full bg-muted" />
                    )}
                    <div>
                      <div className="text-lg font-semibold">{justice.name}</div>
                      <div className="text-sm text-muted-foreground">{justice.role}</div>
                      <Badge className="mt-2" variant="secondary">
                        Active
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>

      {inactive.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Former Justices</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {inactive.map((justice) => (
              <Link key={justice.id} href={`/justices/${justice.slug}`}>
                <Card className="h-full transition-shadow hover:shadow-md">
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-4">
                      {justice.official_photo_url ? (
                        <img
                          src={justice.official_photo_url}
                          alt={justice.name}
                          className="h-16 w-16 rounded-full object-cover"
                        />
                      ) : (
                        <div className="h-16 w-16 rounded-full bg-muted" />
                      )}
                      <div>
                        <div className="text-lg font-semibold">{justice.name}</div>
                        <div className="text-sm text-muted-foreground">{justice.role}</div>
                        <Badge className="mt-2" variant="outline">
                          Retired
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
