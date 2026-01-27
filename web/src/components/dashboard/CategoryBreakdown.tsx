"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn, formatPercentage } from "@/lib/utils";
import Link from "next/link";

interface CategoryData {
  name: string;
  slug: string;
  total: number;
  enacted: number;
  inProgress: number;
  blocked: number;
}

interface CategoryBreakdownProps {
  categories: CategoryData[];
}

const categoryIcons: Record<string, React.ReactNode> = {
  immigration: <UsersIcon />,
  environment: <LeafIcon />,
  healthcare: <HeartIcon />,
  education: <BookIcon />,
  civil_rights: <ScaleIcon />,
  labor: <BriefcaseIcon />,
  economy: <TrendingIcon />,
  defense: <ShieldIcon />,
  justice: <GavelIcon />,
  government: <BuildingIcon />,
};

export function CategoryBreakdown({ categories }: CategoryBreakdownProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Implementation by Category</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {categories.map((category) => {
          const progress = category.total > 0
            ? Math.round((category.enacted / category.total) * 100)
            : 0;

          return (
            <Link
              key={category.slug}
              href={`/tracker?category=${category.slug}`}
              className="block group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-lg bg-muted group-hover:bg-muted/80 transition-colors">
                    {categoryIcons[category.slug] || <FolderIcon />}
                  </div>
                  <div>
                    <h4 className="font-medium group-hover:text-primary transition-colors">
                      {category.name}
                    </h4>
                    <p className="text-xs text-muted-foreground">
                      {category.total} objectives
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <span
                    className={cn(
                      "text-sm font-semibold",
                      progress > 50
                        ? "text-red-600"
                        : progress > 25
                        ? "text-orange-600"
                        : "text-muted-foreground"
                    )}
                  >
                    {formatPercentage(progress)}
                  </span>
                  <p className="text-xs text-muted-foreground">implemented</p>
                </div>
              </div>

              {/* Progress bar with segments */}
              <div className="h-2 bg-muted rounded-full overflow-hidden flex">
                {category.enacted > 0 && (
                  <div
                    className="h-full bg-red-500"
                    style={{ width: `${(category.enacted / category.total) * 100}%` }}
                  />
                )}
                {category.inProgress > 0 && (
                  <div
                    className="h-full bg-orange-500"
                    style={{ width: `${(category.inProgress / category.total) * 100}%` }}
                  />
                )}
                {category.blocked > 0 && (
                  <div
                    className="h-full bg-green-500"
                    style={{ width: `${(category.blocked / category.total) * 100}%` }}
                  />
                )}
              </div>

              {/* Legend */}
              <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                <span className="flex items-center">
                  <span className="w-2 h-2 rounded-full bg-red-500 mr-1" />
                  {category.enacted} enacted
                </span>
                <span className="flex items-center">
                  <span className="w-2 h-2 rounded-full bg-orange-500 mr-1" />
                  {category.inProgress} in progress
                </span>
                <span className="flex items-center">
                  <span className="w-2 h-2 rounded-full bg-green-500 mr-1" />
                  {category.blocked} blocked
                </span>
              </div>
            </Link>
          );
        })}
      </CardContent>
    </Card>
  );
}

// Icons
function UsersIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  );
}

function LeafIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
    </svg>
  );
}

function HeartIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
    </svg>
  );
}

function BookIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
  );
}

function ScaleIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
    </svg>
  );
}

function BriefcaseIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );
}

function TrendingIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  );
}

function GavelIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
    </svg>
  );
}

function BuildingIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
    </svg>
  );
}

function FolderIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    </svg>
  );
}
