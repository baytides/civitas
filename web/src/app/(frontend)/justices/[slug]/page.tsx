import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://api.projectcivitas.com/api/v1";

interface NotableOpinion {
  case_name: string;
  citation?: string | null;
  decision_date?: string | null;
}

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
  voting_tendencies?: string[] | string;
  notable_opinions?: NotableOpinion[];
  statistical_profile?: Record<string, unknown>;
  methodology?: string | null;
  disclaimer?: string | null;
  generated_at?: string | null;
  circuit_assignments?: string[];
  assignments_updated_at?: string | null;
  start_date?: string | null;
  appointed_by?: string | null;
}

// Convert snake_case keys to human-readable labels
function formatStatLabel(key: string): string {
  const labelMap: Record<string, string> = {
    average_opinion_length: "Average Opinion Length",
    median_opinion_year: "Median Opinion Year",
    majority_rate_deviation: "Majority Rate Deviation",
    dissent_rate_deviation: "Dissent Rate Deviation",
    concurrence_rate_deviation: "Concurrence Rate Deviation",
    recent_case_decision_rate: "Recent Case Decision Rate",
    total_opinions: "Total Opinions",
    majority_rate: "Majority Rate",
    dissent_rate: "Dissent Rate",
    concurrence_rate: "Concurrence Rate",
  };
  return labelMap[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default async function JusticeDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const response = await fetch(`${API_BASE}/justices/${slug}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    notFound();
  }
  const justice = (await response.json()) as JusticeDetail;

  const counts = justice.opinion_counts || {};

  return (
    <div className="container py-8">
      <div className="mb-6">
        <Link href="/justices" className="text-sm text-muted-foreground hover:text-primary">
          ← Back to Justices
        </Link>
      </div>

      <div className="flex flex-col gap-6 md:flex-row md:items-start">
        <div className="flex items-center gap-6">
          {justice.official_photo_url ? (
            <Image
              src={justice.official_photo_url}
              alt={justice.name}
              width={160}
              height={160}
              className="h-40 w-40 rounded-full object-cover"
              unoptimized
            />
          ) : (
            <div className="h-40 w-40 rounded-full bg-muted" />
          )}
          <div>
            <h1 className="text-3xl font-bold">{justice.name}</h1>
            <p className="text-muted-foreground">{justice.role}</p>
            {justice.start_date && (
              <Badge className="mt-2" variant="secondary">
                Confirmed {new Date(justice.start_date).getFullYear()}
              </Badge>
            )}
            {justice.appointed_by && (
              <p className="text-sm text-muted-foreground mt-1">
                Appointed by {justice.appointed_by}
              </p>
            )}
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

      {justice.circuit_assignments && justice.circuit_assignments.length > 0 && (
        <Card className="mt-8">
          <CardContent className="pt-6">
            <h2 className="text-lg font-semibold mb-2">Circuit Assignments</h2>
            <div className="flex flex-wrap gap-2">
              {justice.circuit_assignments.map((circuit) => (
                <Badge key={circuit} variant="secondary">
                  {circuit}
                </Badge>
              ))}
            </div>
            {justice.assignments_updated_at && (
              <p className="text-xs text-muted-foreground mt-2">
                Updated {new Date(justice.assignments_updated_at).toLocaleDateString()}
              </p>
            )}
          </CardContent>
        </Card>
      )}

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
            {justice.voting_tendencies ? (
              typeof justice.voting_tendencies === "string" ? (
                <p className="text-muted-foreground">{justice.voting_tendencies}</p>
              ) : justice.voting_tendencies.length === 1 && justice.voting_tendencies[0].length > 100 ? (
                // Single long string in array = narrative format
                <p className="text-muted-foreground">{justice.voting_tendencies[0]}</p>
              ) : justice.voting_tendencies.length > 0 ? (
                <ul className="list-disc pl-5 text-muted-foreground">
                  {justice.voting_tendencies.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground">Profile generation in progress.</p>
              )
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
                {justice.notable_opinions.map((opinion) => (
                  <li key={opinion.citation || opinion.case_name}>
                    <span className="font-medium">{opinion.case_name}</span>
                    {opinion.citation && (
                      <span className="text-sm"> ({opinion.citation})</span>
                    )}
                    {opinion.decision_date && (
                      <span className="text-sm"> - {opinion.decision_date}</span>
                    )}
                  </li>
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
                    <div className="text-muted-foreground">{formatStatLabel(key)}</div>
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
