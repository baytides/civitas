"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface ThreatMeterProps {
  level: "critical" | "high" | "elevated" | "moderate";
  progress: number; // 0-100
  label?: string;
}

const levelConfig = {
  critical: {
    color: "bg-red-500",
    textColor: "text-red-500",
    label: "CRITICAL",
    description: "Immediate threat to democratic institutions",
  },
  high: {
    color: "bg-orange-500",
    textColor: "text-orange-500",
    label: "HIGH",
    description: "Significant implementation progress",
  },
  elevated: {
    color: "bg-yellow-500",
    textColor: "text-yellow-500",
    label: "ELEVATED",
    description: "Active implementation in progress",
  },
  moderate: {
    color: "bg-green-500",
    textColor: "text-green-500",
    label: "MODERATE",
    description: "Limited current activity",
  },
};

export function ThreatMeter({ level, progress, label }: ThreatMeterProps) {
  const config = levelConfig[level];

  return (
    <div className="relative">
      {/* Background arc */}
      <div className="relative w-48 h-24 mx-auto overflow-hidden">
        <div className="absolute inset-0 flex items-end justify-center">
          {/* Meter background */}
          <svg
            viewBox="0 0 200 100"
            className="w-full h-full"
            style={{ transform: "rotate(0deg)" }}
          >
            {/* Background arc */}
            <path
              d="M 10 100 A 90 90 0 0 1 190 100"
              fill="none"
              stroke="currentColor"
              strokeWidth="20"
              className="text-muted"
            />
            {/* Progress arc */}
            <path
              d="M 10 100 A 90 90 0 0 1 190 100"
              fill="none"
              stroke="currentColor"
              strokeWidth="20"
              strokeDasharray={`${(progress / 100) * 282.7} 282.7`}
              className={config.textColor}
            />
          </svg>
        </div>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
          <span className={cn("text-3xl font-bold", config.textColor)}>
            {progress}%
          </span>
        </div>
      </div>

      {/* Level indicator */}
      <div className="text-center mt-4">
        <span
          className={cn(
            "inline-flex items-center px-3 py-1 rounded-full text-sm font-bold",
            config.color,
            "text-white"
          )}
        >
          {label || config.label}
        </span>
        <p className="text-sm text-muted-foreground mt-2">
          {config.description}
        </p>
      </div>
    </div>
  );
}

export function ThreatMeterCompact({
  level,
  progress,
}: {
  level: "critical" | "high" | "elevated" | "moderate";
  progress: number;
}) {
  const config = levelConfig[level];

  return (
    <div className="flex items-center space-x-3">
      <div className="flex-1">
        <div className="flex justify-between text-sm mb-1">
          <span className="font-medium">Implementation Progress</span>
          <span className={cn("font-bold", config.textColor)}>{progress}%</span>
        </div>
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all", config.color)}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
      <span
        className={cn(
          "px-2 py-1 rounded text-xs font-bold",
          config.color,
          "text-white"
        )}
      >
        {config.label}
      </span>
    </div>
  );
}
