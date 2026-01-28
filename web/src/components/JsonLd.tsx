"use client";

interface JsonLdProps {
  data: Record<string, unknown>;
}

/**
 * Renders Schema.org JSON-LD structured data.
 * Uses dangerouslySetInnerHTML with JSON.stringify on trusted, controlled data
 * objects (not user input). This is the standard Next.js pattern for JSON-LD.
 */
export function JsonLd({ data }: JsonLdProps) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

export function WebsiteJsonLd() {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "WebSite",
        name: "Project Civitas",
        url: "https://projectcivitas.com",
        description:
          "Track the implementation of Project 2025 policy objectives, executive orders, court cases, and state legislation.",
        potentialAction: {
          "@type": "SearchAction",
          target: {
            "@type": "EntryPoint",
            urlTemplate:
              "https://projectcivitas.com/tracker?search={search_term_string}",
          },
          "query-input": "required name=search_term_string",
        },
      }}
    />
  );
}

export function ObjectiveJsonLd({
  id,
  title,
  description,
  category,
  status,
  datePublished,
}: {
  id: number;
  title: string;
  description: string;
  category: string;
  status: string;
  datePublished?: string;
}) {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "Article",
        headline: title,
        description,
        articleSection: category,
        url: `https://projectcivitas.com/tracker/${id}`,
        publisher: {
          "@type": "Organization",
          name: "Project Civitas",
          url: "https://projectcivitas.com",
        },
        ...(datePublished && { datePublished }),
        keywords: [category, status, "Project 2025", "policy tracker"],
      }}
    />
  );
}

export function ExecutiveOrderJsonLd({
  id,
  title,
  description,
  datePublished,
  president,
}: {
  id: number;
  title: string;
  description: string;
  datePublished?: string;
  president?: string;
}) {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "LegislationObject",
        name: title,
        description,
        legislationType: "Executive Order",
        url: `https://projectcivitas.com/executive-orders/${id}`,
        ...(datePublished && { datePublished }),
        ...(president && {
          legislationPassedBy: {
            "@type": "Person",
            name: president,
          },
        }),
      }}
    />
  );
}

export function CourtCaseJsonLd({
  id,
  caseName,
  court,
  decisionDate,
  citation,
}: {
  id: number;
  caseName: string;
  court?: string;
  decisionDate?: string;
  citation?: string;
}) {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "LegalCase",
        name: caseName,
        url: `https://projectcivitas.com/cases/${id}`,
        ...(court && { courtName: court }),
        ...(decisionDate && { datePublished: decisionDate }),
        ...(citation && { identifier: citation }),
      }}
    />
  );
}
