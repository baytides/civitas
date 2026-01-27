import Link from "next/link";
import { notFound } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate, snakeToTitle } from "@/lib/utils";
import { getLegislation, getAllLegislationIds } from "@/lib/data";

// Generate static paths for all legislation
export async function generateStaticParams() {
  return getAllLegislationIds().map((id) => ({ id }));
}

export default async function LegislationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const legislation = getLegislation(id);

  if (!legislation) {
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
        <span>Legislation</span>
        <span>/</span>
        <span className="text-foreground">{legislation.billNumber}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-3">
              <Badge variant="outline">{legislation.chamber.toUpperCase()}</Badge>
              <Badge variant={legislation.status === "signed" ? "enacted" : legislation.status === "introduced" || legislation.status === "in_committee" ? "proposed" : "in_progress"}>
                {snakeToTitle(legislation.status)}
              </Badge>
              <Badge variant="outline">{legislation.jurisdiction}</Badge>
            </div>

            <h1 className="text-3xl font-bold mb-2">{legislation.billNumber}</h1>
            <h2 className="text-xl text-muted-foreground mb-4">{legislation.title}</h2>

            <p className="text-muted-foreground">{legislation.summary}</p>
          </div>

          {/* Sponsors */}
          <Card>
            <CardHeader>
              <CardTitle>Sponsors</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {legislation.sponsors.map((sponsor, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded border">
                    <span className="font-medium">{sponsor.name}</span>
                    <Badge variant="outline">
                      {sponsor.party}-{sponsor.state}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Legislative Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Legislative Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {legislation.actions.map((action, idx) => (
                  <div key={idx} className="flex gap-4 items-start">
                    <span className="text-sm text-muted-foreground whitespace-nowrap">
                      {formatDate(action.date)}
                    </span>
                    <p>{action.action}</p>
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
                {legislation.relatedObjectives.map((obj) => (
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
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm text-muted-foreground">Jurisdiction</p>
                <p className="font-medium capitalize">{legislation.jurisdiction}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Introduced</p>
                <p className="font-medium">{formatDate(legislation.introducedDate)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Chamber</p>
                <p className="font-medium capitalize">{legislation.chamber}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Take Action</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button className="w-full" variant="action">
                Contact Your Rep
              </Button>
              <Button className="w-full" variant="outline">
                Track This Bill
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
