import Link from "next/link";
import { ThreatMeter } from "@/components/dashboard/ThreatMeter";
import { CategoryBreakdown } from "@/components/dashboard/CategoryBreakdown";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { ActionAlertStack } from "@/components/dashboard/ActionAlertBanner";
import { DashboardDataLoader, RecentExecutiveOrders } from "@/components/dashboard/DashboardData";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { categoryStats } from "@/lib/data";

// Recent activity - derived from centralized data
const recentActivity = [
  {
    id: "1",
    type: "executive_order" as const,
    title: "Executive Order on Federal Workforce Restructuring",
    description: "Orders a review of all federal agencies for potential consolidation",
    date: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    threatLevel: "critical" as const,
    url: "/executive-orders/5",
  },
  {
    id: "2",
    type: "court_case" as const,
    title: "State of California v. Department of Education",
    description: "Challenge to new federal education funding requirements",
    date: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    status: "in_progress",
    url: "/cases/1",
  },
  {
    id: "3",
    type: "legislation" as const,
    title: "H.R. 899 - To terminate the Department of Education",
    description: "Would eliminate the Department of Education entirely",
    date: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
    status: "proposed",
    url: "/legislation/1",
  },
  {
    id: "4",
    type: "objective" as const,
    title: "Eliminate Department of Education",
    description: "P2025 objective status updated to 'In Progress'",
    date: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
    threatLevel: "high" as const,
    url: "/tracker/ed-1",
  },
];

const alerts = [
  {
    id: "alert-1",
    title: "URGENT: Comment Period Ending",
    description: "EPA rule change comment period ends in 48 hours. Make your voice heard.",
    urgency: "critical" as const,
    callToAction: {
      text: "Submit Comment",
      url: "/resistance",
    },
  },
];

export default function HomePage() {
  // Overall progress - will be dynamically calculated when objectives are loaded
  const overallProgress = 40; // Approximate baseline

  return (
    <>
      {/* Action Alerts */}
      <ActionAlertStack alerts={alerts} />

      <div className="container py-8 space-y-8">
        {/* Hero Section */}
        <section className="text-center py-8">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            Protecting American Democracy
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto mb-8">
            Fighting Project 2025 implementation through transparency,
            accountability, and collective action.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/tracker">
              <Button size="lg" variant="action">
                Explore Tracker
              </Button>
            </Link>
            <Link href="/resistance">
              <Button size="lg" variant="outline">
                Take Action
              </Button>
            </Link>
          </div>
        </section>

        {/* Threat Level + Stats */}
        <section className="grid lg:grid-cols-3 gap-8">
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle className="text-center">Implementation Status</CardTitle>
            </CardHeader>
            <CardContent>
              <ThreatMeter
                level={overallProgress > 10 ? "high" : overallProgress > 5 ? "elevated" : "moderate"}
                progress={overallProgress}
              />
            </CardContent>
          </Card>

          <div className="lg:col-span-2">
            <h2 className="text-lg font-semibold mb-4">Overview</h2>
            <DashboardDataLoader />
          </div>
        </section>

        {/* Main Content Grid */}
        <section className="grid lg:grid-cols-3 gap-8">
          {/* Categories */}
          <div className="lg:col-span-2">
            <CategoryBreakdown categories={categoryStats} />
          </div>

          {/* Recent Executive Orders */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Recent Executive Orders</CardTitle>
              </CardHeader>
              <CardContent>
                <RecentExecutiveOrders limit={5} />
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Resistance Tiers Preview */}
        <section>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold">Resistance Strategy</h2>
              <p className="text-muted-foreground">
                Three-tier approach to protecting democracy
              </p>
            </div>
            <Link href="/resistance">
              <Button variant="outline">View Full Strategy</Button>
            </Link>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {/* Tier 1 */}
            <Card className="border-l-4 border-l-green-500">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-green-500 text-white font-bold">
                    1
                  </span>
                  <CardTitle>Courts & States</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Immediate action through litigation and state-level protections
                </p>
                <ul className="text-sm space-y-2">
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                    Support ongoing lawsuits
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                    Contact state legislators
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                    Advocate for state protections
                  </li>
                </ul>
              </CardContent>
            </Card>

            {/* Tier 2 */}
            <Card className="border-l-4 border-l-yellow-500">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-yellow-500 text-black font-bold">
                    2
                  </span>
                  <CardTitle>Congress 2026</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Build toward flipping Congress in the 2026 midterms
                </p>
                <ul className="text-sm space-y-2">
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                    Register voters
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                    Support candidates
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                    Build coalitions
                  </li>
                </ul>
              </CardContent>
            </Card>

            {/* Tier 3 */}
            <Card className="border-l-4 border-l-blue-500">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-500 text-white font-bold">
                    3
                  </span>
                  <CardTitle>Presidency 2028</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Long-term strategy to restore executive branch
                </p>
                <ul className="text-sm space-y-2">
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                    Develop new leaders
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                    Build infrastructure
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                    Unite the movement
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* State Map Preview */}
        <section>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>State Protections</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  See which states are fighting back
                </p>
              </div>
              <Link href="/states">
                <Button variant="outline">View State Map</Button>
              </Link>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center py-12 bg-muted/50 rounded-lg">
                <div className="text-center">
                  <MapIcon className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">
                    Interactive state map coming soon
                  </p>
                  <Link href="/states">
                    <Button variant="link" className="mt-2">
                      View state list →
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </>
  );
}

function MapIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
      />
    </svg>
  );
}
