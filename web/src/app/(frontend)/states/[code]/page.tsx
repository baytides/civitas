import Link from "next/link";
import { notFound } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatDate } from "@/lib/utils";
import { getState, getAllStateCodes } from "@/lib/data";

// Generate static paths for all states
export async function generateStaticParams() {
  return getAllStateCodes().map((code) => ({ code }));
}

const protectionLevelColors = {
  strong: "bg-green-500",
  moderate: "bg-yellow-500",
  weak: "bg-orange-500",
  hostile: "bg-red-500",
};

const protectionLevelLabels = {
  strong: "Strong Protections",
  moderate: "Moderate Protections",
  weak: "Weak Protections",
  hostile: "Hostile Environment",
};

export default async function StateDetailPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  const state = getState(code);

  if (!state) {
    notFound();
  }

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
          {/* Header */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <h1 className="text-3xl font-bold">{state.name}</h1>
              <Badge
                className={cn(
                  "text-white",
                  protectionLevelColors[state.protectionLevel]
                )}
              >
                {protectionLevelLabels[state.protectionLevel]}
              </Badge>
            </div>

            {/* Resistance Score */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-muted-foreground">Resistance Score</span>
                <span className="text-2xl font-bold">{state.resistanceScore}%</span>
              </div>
              <div className="h-3 bg-muted rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    protectionLevelColors[state.protectionLevel]
                  )}
                  style={{ width: `${state.resistanceScore}%` }}
                />
              </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900">
                <p className="text-sm text-muted-foreground">Active Protections</p>
                <p className="text-2xl font-bold text-green-600">{state.activeProtections}</p>
              </div>
              <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900">
                <p className="text-sm text-muted-foreground">Pending Threats</p>
                <p className="text-2xl font-bold text-red-600">{state.pendingThreats}</p>
              </div>
            </div>
          </div>

          {/* Key Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Actions</CardTitle>
            </CardHeader>
            <CardContent>
              {state.keyActions.length > 0 ? (
                <div className="space-y-3">
                  {state.keyActions.map((action, index) => (
                    <div
                      key={index}
                      className="flex items-start gap-4 p-3 rounded-lg border"
                    >
                      <div className="flex-1">
                        <p className="font-medium">{action.title}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-sm text-muted-foreground">
                            {formatDate(action.date)}
                          </span>
                          <Badge variant="outline" className="text-xs">
                            {action.type}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">No recent actions tracked</p>
              )}
            </CardContent>
          </Card>

          {/* Resources */}
          {state.resources.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Resources</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {state.resources.map((resource, index) => (
                    <a
                      key={index}
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                    >
                      <p className="font-medium text-primary">{resource.name}</p>
                      <p className="text-sm text-muted-foreground truncate">
                        {resource.url}
                      </p>
                    </a>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Government Info */}
          <Card>
            <CardHeader>
              <CardTitle>Government</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Governor</p>
                <div className="flex items-center gap-2">
                  <p className="font-medium">{state.governorName}</p>
                  <Badge
                    variant="outline"
                    className={cn(
                      state.governorParty === "D"
                        ? "border-blue-500 text-blue-600"
                        : "border-red-500 text-red-600"
                    )}
                  >
                    {state.governorParty}
                  </Badge>
                </div>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Legislature Control</p>
                <Badge
                  variant="outline"
                  className={cn(
                    state.legislatureControl === "D"
                      ? "border-blue-500 text-blue-600"
                      : state.legislatureControl === "R"
                        ? "border-red-500 text-red-600"
                        : "border-purple-500 text-purple-600"
                  )}
                >
                  {state.legislatureControl === "D"
                    ? "Democratic"
                    : state.legislatureControl === "R"
                      ? "Republican"
                      : "Split Control"}
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Take Action */}
          <Card className="border-green-500/50">
            <CardHeader>
              <CardTitle>Take Action in {state.name}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                {state.protectionLevel === "strong" || state.protectionLevel === "moderate"
                  ? "Support and strengthen existing protections in your state."
                  : "Help build resistance infrastructure in your state."}
              </p>
              <Button className="w-full" variant="action">
                Find Local Organizations
              </Button>
              <Button className="w-full" variant="outline">
                Contact Your Representatives
              </Button>
            </CardContent>
          </Card>

          {/* Back Link */}
          <Link href="/states">
            <Button variant="outline" className="w-full">
              ← Back to All States
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
