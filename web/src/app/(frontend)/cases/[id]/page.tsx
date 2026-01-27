import Link from "next/link";
import { notFound } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import { getCourtCase, getAllCourtCaseIds } from "@/lib/data";

// Generate static paths for all cases
export async function generateStaticParams() {
  return getAllCourtCaseIds().map((id) => ({ id }));
}

export default async function CaseDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const courtCase = getCourtCase(id);

  if (!courtCase) {
    notFound();
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
        <span className="text-foreground truncate max-w-[200px]">{courtCase.caseName}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-3">
              <Badge variant="outline">{courtCase.status.toUpperCase()}</Badge>
              <Badge variant="outline">Court Case</Badge>
            </div>

            <h1 className="text-2xl font-bold mb-2">{courtCase.caseName}</h1>
            <p className="text-muted-foreground mb-4">{courtCase.citation}</p>

            <p className="text-muted-foreground">{courtCase.summary}</p>
          </div>

          {/* Parties */}
          <Card>
            <CardHeader>
              <CardTitle>Parties</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">Plaintiffs</p>
                <ul className="space-y-1">
                  {courtCase.plaintiffs.map((p, idx) => (
                    <li key={idx} className="text-sm">{p}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">Defendants</p>
                <ul className="space-y-1">
                  {courtCase.defendants.map((d, idx) => (
                    <li key={idx} className="text-sm">{d}</li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Docket */}
          <Card>
            <CardHeader>
              <CardTitle>Docket</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {courtCase.docket.map((entry, idx) => (
                  <div key={idx} className="flex gap-4 items-start">
                    <span className="text-sm text-muted-foreground whitespace-nowrap">
                      {formatDate(entry.date)}
                    </span>
                    <p className="text-sm">{entry.entry}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Related P2025 Objectives */}
          <Card>
            <CardHeader>
              <CardTitle>Related P2025 Objectives</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {courtCase.relatedObjectives.map((obj) => (
                  <Link
                    key={obj.id}
                    href={`/tracker/${obj.id}`}
                    className="block p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                  >
                    <p className="font-medium">{obj.title}</p>
                    <p className="text-sm text-muted-foreground">ID: {obj.id}</p>
                  </Link>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Related Executive Orders */}
          <Card>
            <CardHeader>
              <CardTitle>Related Executive Orders</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {courtCase.relatedExecutiveOrders.map((eo) => (
                  <Link
                    key={eo.id}
                    href={`/executive-orders/${eo.id}`}
                    className="block p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                  >
                    <p className="font-medium">EO {eo.orderNumber}: {eo.title}</p>
                  </Link>
                ))}
              </div>
            </CardContent>
          </Card>
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
                <p className="text-sm text-muted-foreground">Citation</p>
                <p className="font-medium">{courtCase.citation}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Filed</p>
                <p className="font-medium">{formatDate(courtCase.filedDate)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <Badge variant="outline">{courtCase.status}</Badge>
              </div>
            </CardContent>
          </Card>

          <Card className="border-green-500/50">
            <CardHeader>
              <CardTitle>Support This Case</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Legal challenges are critical to defending democracy. Support organizations fighting these battles.
              </p>
              <Button className="w-full" variant="action">
                Find Legal Aid Organizations
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
