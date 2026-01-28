import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://api.projectcivitas.com/api/v1";

type StatusResponse = {
  generated_at: string;
  objectives_total: number;
  objectives_titled: number;
  objectives_title_pct: number;
  objectives_with_insights: number;
  objectives_insight_pct: number;
  expert_analyses: number;
  expert_analyses_pct: number;
  expert_last_generated_at: string | null;
  insights_last_generated_at: string | null;
  justices_total: number;
  justices_active: number;
  justice_profiles: number;
  justice_profiles_pct: number;
  justice_profiles_last_generated_at: string | null;
  executive_orders_total: number;
  cases_total: number;
  legislation_total: number;
};

function formatTimestamp(value: string | null) {
  if (!value) return "Not yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-US", { timeZoneName: "short" });
}

function formatPercent(value: number) {
  return `${value.toFixed(1)}%`;
}

async function getStatus(): Promise<StatusResponse> {
  const res = await fetch(`${API_BASE}/status`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error("Failed to load status");
  }
  return res.json();
}

export default async function StatsPage() {
  const status = await getStatus();

  return (
    <div className="container py-10 space-y-8">
      <div>
        <h1 className="text-3xl font-semibold">Site Generation Status</h1>
        <p className="text-sm text-muted-foreground mt-2">
          Last refreshed: {formatTimestamp(status.generated_at)}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle>Objectives</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-2xl font-semibold">{status.objectives_total}</p>
            <p className="text-sm text-muted-foreground">
              Short titles: {status.objectives_titled} ({formatPercent(status.objectives_title_pct)})
            </p>
            <p className="text-sm text-muted-foreground">
              Insights: {status.objectives_with_insights} ({formatPercent(status.objectives_insight_pct)})
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Expert Analyses</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-2xl font-semibold">{status.expert_analyses}</p>
            <p className="text-sm text-muted-foreground">
              Coverage: {formatPercent(status.expert_analyses_pct)}
            </p>
            <p className="text-sm text-muted-foreground">
              Last run: {formatTimestamp(status.expert_last_generated_at)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Justices</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-2xl font-semibold">{status.justices_active}</p>
            <p className="text-sm text-muted-foreground">
              Profiles: {status.justice_profiles} ({formatPercent(status.justice_profiles_pct)})
            </p>
            <p className="text-sm text-muted-foreground">
              Last run: {formatTimestamp(status.justice_profiles_last_generated_at)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Data Totals</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Executive Orders: {status.executive_orders_total}
            </p>
            <p className="text-sm text-muted-foreground">Court Cases: {status.cases_total}</p>
            <p className="text-sm text-muted-foreground">
              Legislation: {status.legislation_total}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Insights Pipeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Last insight generation: {formatTimestamp(status.insights_last_generated_at)}
            </p>
            <p className="text-sm text-muted-foreground">
              Titles generated: {status.objectives_titled}/{status.objectives_total}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Expert Pipeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Expert analyses: {status.expert_analyses}/{status.objectives_total}
            </p>
            <p className="text-sm text-muted-foreground">
              Last expert run: {formatTimestamp(status.expert_last_generated_at)}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
