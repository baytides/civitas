"use client";

import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function LegislationDetailPage() {
  return (
    <div className="container py-8">
      <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
        <Link href="/tracker" className="hover:text-foreground">
          Tracker
        </Link>
        <span>/</span>
        <span className="text-foreground">Legislation</span>
      </nav>
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground text-lg">
            Legislation tracking is coming soon. Browse policies and executive orders in the tracker.
          </p>
          <Link href="/tracker">
            <Button variant="outline" className="mt-4">
              Back to Tracker
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
