"use client";

import { CSVLink } from "react-csv";
import { Button } from "@/components/ui/button";

interface CsvExportProps<T extends Record<string, unknown>> {
  data: T[];
  filename: string;
  headers?: { label: string; key: string }[];
  label?: string;
}

export function CsvExport<T extends Record<string, unknown>>({
  data,
  filename,
  headers,
  label = "Export CSV",
}: CsvExportProps<T>) {
  if (data.length === 0) return null;

  return (
    <CSVLink
      data={data}
      filename={filename}
      headers={headers}
      className="inline-flex"
    >
      <Button variant="outline" size="sm">
        <DownloadIcon className="h-4 w-4 mr-2" />
        {label}
      </Button>
    </CSVLink>
  );
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
      />
    </svg>
  );
}
