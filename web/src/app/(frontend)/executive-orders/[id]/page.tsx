import Link from "next/link";
import { notFound } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import { getExecutiveOrder, getAllExecutiveOrderIds } from "@/lib/data";

// Generate static paths for all executive orders
export async function generateStaticParams() {
  return getAllExecutiveOrderIds().map((id) => ({ id }));
}

export default async function ExecutiveOrderDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const eo = getExecutiveOrder(id);

  if (!eo) {
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
        <span>Executive Orders</span>
        <span>/</span>
        <span className="text-foreground">EO {eo.orderNumber}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-3">
              <Badge variant="destructive">{eo.status.toUpperCase()}</Badge>
              <Badge variant="outline">Executive Order</Badge>
            </div>

            <h1 className="text-3xl font-bold mb-2">EO {eo.orderNumber}</h1>
            <h2 className="text-xl text-muted-foreground mb-4">{eo.title}</h2>

            <p className="text-muted-foreground">{eo.summary}</p>
          </div>

          {/* Related P2025 Objectives */}
          <Card>
            <CardHeader>
              <CardTitle>Related P2025 Objectives</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {eo.relatedObjectives.map((obj) => (
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

          {/* Legal Challenges */}
          <Card>
            <CardHeader>
              <CardTitle>Legal Challenges</CardTitle>
            </CardHeader>
            <CardContent>
              {eo.legalChallenges.length > 0 ? (
                <div className="space-y-2">
                  {eo.legalChallenges.map((challenge) => (
                    <Link
                      key={challenge.id}
                      href={`/cases/${challenge.id}`}
                      className="block p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <p className="font-medium">{challenge.caseName}</p>
                        <Badge variant="outline">{challenge.status}</Badge>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">No legal challenges filed yet</p>
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
              <div>
                <p className="text-sm text-muted-foreground">Order Number</p>
                <p className="font-medium">EO {eo.orderNumber}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Signed</p>
                <p className="font-medium">{formatDate(eo.signingDate)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <Badge variant="destructive">{eo.status}</Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Resources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button className="w-full" variant="outline" asChild>
                <a href={eo.fullTextUrl} target="_blank" rel="noopener noreferrer">
                  View Full Text
                </a>
              </Button>
              <Button className="w-full" variant="action">
                Take Action
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
