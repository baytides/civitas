import Link from "next/link";
import { notFound } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate, snakeToTitle } from "@/lib/utils";

// Mock data - will be replaced with API call
const mockLegislation: Record<string, {
  id: string;
  title: string;
  number: string;
  type: string;
  status: string;
  jurisdiction: string;
  chamber: string;
  session: string;
  introducedDate: string;
  summary: string;
  sponsors: { name: string; party: string; state: string }[];
  relatedObjectives: { id: string; title: string }[];
  actions: { date: string; description: string }[];
}> = {
  "1": {
    id: "1",
    title: "To terminate the Department of Education",
    number: "H.R. 899",
    type: "bill",
    status: "proposed",
    jurisdiction: "federal",
    chamber: "house",
    session: "119th Congress",
    introducedDate: "2025-01-15",
    summary: "A bill to terminate the Department of Education and transfer its functions to the states.",
    sponsors: [
      { name: "Rep. Thomas Massie", party: "R", state: "KY" },
    ],
    relatedObjectives: [
      { id: "ed-1", title: "Eliminate Department of Education" },
    ],
    actions: [
      { date: "2025-01-15", description: "Introduced in House" },
      { date: "2025-01-16", description: "Referred to Committee on Education and the Workforce" },
    ],
  },
  "2": {
    id: "2",
    title: "Education Freedom Act",
    number: "S. 323",
    type: "bill",
    status: "proposed",
    jurisdiction: "federal",
    chamber: "senate",
    session: "119th Congress",
    introducedDate: "2025-01-18",
    summary: "A bill to provide block grants to states for education and reduce federal education mandates.",
    sponsors: [
      { name: "Sen. Mike Lee", party: "R", state: "UT" },
    ],
    relatedObjectives: [
      { id: "ed-1", title: "Eliminate Department of Education" },
    ],
    actions: [
      { date: "2025-01-18", description: "Introduced in Senate" },
      { date: "2025-01-19", description: "Referred to Committee on Health, Education, Labor, and Pensions" },
    ],
  },
};

export default async function LegislationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const legislation = mockLegislation[id];

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
        <span className="text-foreground">{legislation.number}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-3">
              <Badge variant="outline">{legislation.chamber.toUpperCase()}</Badge>
              <Badge variant={legislation.status as "enacted" | "proposed" | "in_progress" | "blocked"}>
                {snakeToTitle(legislation.status)}
              </Badge>
              <Badge variant="outline">{legislation.jurisdiction}</Badge>
            </div>

            <h1 className="text-3xl font-bold mb-2">{legislation.number}</h1>
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
                    <p>{action.description}</p>
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
                <p className="text-sm text-muted-foreground">Session</p>
                <p className="font-medium">{legislation.session}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Introduced</p>
                <p className="font-medium">{formatDate(legislation.introducedDate)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Type</p>
                <p className="font-medium">{snakeToTitle(legislation.type)}</p>
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
