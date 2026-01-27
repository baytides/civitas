import Link from "next/link";
import { DynamicThreatMeter } from "@/components/dashboard/ThreatMeter";
import { DynamicCategoryBreakdown } from "@/components/dashboard/DynamicCategoryBreakdown";
import { DashboardDataLoader, RecentExecutiveOrders } from "@/components/dashboard/DashboardData";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function HomePage() {
  return (
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
              <DynamicThreatMeter />
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
            <DynamicCategoryBreakdown />
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

        {/* State Protections Link */}
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
                <Button variant="outline">View All States</Button>
              </Link>
            </CardHeader>
          </Card>
        </section>
      </div>
  );
}
