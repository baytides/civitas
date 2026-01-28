"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface JusticeDetail {
  id: number;
  name: string;
  slug: string;
  role?: string | null;
  is_active: boolean;
  official_photo_url?: string | null;
  official_bio_url?: string | null;
  wikipedia_url?: string | null;
  opinion_counts?: Record<string, number>;
  profile_summary?: string | null;
  judicial_philosophy?: string | null;
  voting_tendencies?: string[];
  notable_opinions?: string[];
  statistical_profile?: Record<string, unknown>;
  methodology?: string | null;
  disclaimer?: string | null;
  generated_at?: string | null;
}

export default function JusticeDetailPage({ params }: { params: { slug: string } }) {
  const [justice, setJustice] = useState<JusticeDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchJustice() {
      try {
        const response = await fetch(`${API_BASE}/justices/${params.slug}`);
        if (response.ok) {
          const data = await response.json();
          setJustice(data);
        }
      } catch (error) {
        console.error("Error fetching justice:", error);
      }
      setLoading(false);
    }
    fetchJustice();
  }, [params.slug]);

  if (loading) {
    return (
      <div className="container py-8">
        <Skeleton className="h-10 w-1/3 mb-4" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (!justice) {
    return (
      <div className="container py-8">
        <p className="text-muted-foreground">Justice not found.</p>
        <Button asChild className="mt-4">
          <Link href="/justices">Back to Justices</Link>
        </Button>
      </div>
    );
  }

  const counts = justice.opinion_counts || {};

  return (
    <div className="container py-8">
      <div className="mb-6">
        <Link href="/justices" className="text-sm text-muted-foreground hover:text-primary">
          ← Back to Justices
        </Link>
      </div>

      <div className="flex flex-col gap-6 md:flex-row md:items-start">
        <div className="flex items-center gap-4">
          {justice.official_photo_url ? (
            <Image
              src={justice.official_photo_url}
              alt={justice.name}
              width={96}
              height={96}
              className="h-24 w-24 rounded-full object-cover"
              unoptimized
            />
          ) : (
            <div className="h-24 w-24 rounded-full bg-muted" />
          )}
          <div>
            <h1 className="text-3xl font-bold">{justice.name}</h1>
            <p className="text-muted-foreground">{justice.role}</p>
            <Badge className="mt-2" variant={justice.is_active ? "default" : "outline"}>
              {justice.is_active ? "Active" : "Retired"}
            </Badge>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 md:ml-auto">
          {justice.official_bio_url && (
            <Button asChild variant="outline">
              <a href={justice.official_bio_url} target="_blank" rel="noreferrer">
                Official Bio
              </a>
            </Button>
          )}
          {justice.wikipedia_url && (
            <Button asChild variant="outline">
              <a href={justice.wikipedia_url} target="_blank" rel="noreferrer">
                Wikipedia
              </a>
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4 mt-8">
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-2xl font-semibold">{counts.total || 0}</div>
            <div className="text-sm text-muted-foreground">Opinions Logged</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-2xl font-semibold">{counts.majority || 0}</div>
            <div className="text-sm text-muted-foreground">Majority</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-2xl font-semibold">{counts.dissent || 0}</div>
            <div className="text-sm text-muted-foreground">Dissent</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-2xl font-semibold">{counts.concurrence || 0}</div>
            <div className="text-sm text-muted-foreground">Concurrence</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 mt-8">
        <Card>
          <CardContent className="pt-6">
            <h2 className="text-lg font-semibold mb-2">Profile Summary</h2>
            <p className="text-muted-foreground">
              {justice.profile_summary || "Profile generation in progress."}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <h2 className="text-lg font-semibold mb-2">Judicial Philosophy</h2>
            <p className="text-muted-foreground">
              {justice.judicial_philosophy || "Profile generation in progress."}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <h2 className="text-lg font-semibold mb-2">Voting Tendencies</h2>
            {justice.voting_tendencies && justice.voting_tendencies.length > 0 ? (
              <ul className="list-disc pl-5 text-muted-foreground">
                {justice.voting_tendencies.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground">Profile generation in progress.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <h2 className="text-lg font-semibold mb-2">Notable Opinions</h2>
            {justice.notable_opinions && justice.notable_opinions.length > 0 ? (
              <ul className="list-disc pl-5 text-muted-foreground">
                {justice.notable_opinions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground">Profile generation in progress.</p>
            )}
          </CardContent>
        </Card>

        {justice.statistical_profile && Object.keys(justice.statistical_profile).length > 0 && (
          <Card>
            <CardContent className="pt-6">
              <h2 className="text-lg font-semibold mb-2">Statistical Profile</h2>
              <div className="grid gap-2 md:grid-cols-2">
                {Object.entries(justice.statistical_profile).map(([key, value]) => (
                  <div key={key} className="rounded border p-3 text-sm">
                    <div className="text-muted-foreground">{key}</div>
                    <div className="font-medium">{String(value)}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardContent className="pt-6">
            <h2 className="text-lg font-semibold mb-2">Methodology</h2>
            <p className="text-muted-foreground">
              {justice.methodology || "Profile generation in progress."}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <h2 className="text-lg font-semibold mb-2">Disclaimer</h2>
            <p className="text-muted-foreground">
              {justice.disclaimer ||
                "Analysis is generated from published opinions and does not predict future rulings."}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
