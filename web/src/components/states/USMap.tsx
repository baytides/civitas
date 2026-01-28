"use client";

import { useState, useMemo, useCallback } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from "react-simple-maps";

const GEO_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

/** FIPS code → state postal code mapping */
const FIPS_TO_CODE: Record<string, string> = {
  "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
  "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
  "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
  "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
  "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
  "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
  "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
  "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
  "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
  "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
  "56": "WY",
};

export interface StateData {
  code: string;
  name: string;
  billCount: number;
  legislatorCount: number;
}

interface USMapProps {
  states: StateData[];
  onStateClick?: (code: string) => void;
}

function getBillActivityColor(billCount: number, maxBills: number): string {
  if (maxBills === 0) return "#334155"; // slate-700
  const ratio = billCount / maxBills;
  if (ratio > 0.6) return "#dc2626"; // red-600 — very high activity
  if (ratio > 0.3) return "#ea580c"; // orange-600 — high
  if (ratio > 0.1) return "#ca8a04"; // yellow-600 — moderate
  if (ratio > 0) return "#16a34a";   // green-600 — low
  return "#334155";                   // slate-700 — no data
}

export function USMap({ states, onStateClick }: USMapProps) {
  const [tooltipContent, setTooltipContent] = useState("");
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const stateMap = useMemo(() => {
    const map = new Map<string, StateData>();
    for (const s of states) {
      map.set(s.code.toUpperCase(), s);
    }
    return map;
  }, [states]);

  const maxBills = useMemo(
    () => Math.max(...states.map((s) => s.billCount), 1),
    [states]
  );

  const handleMouseEnter = useCallback(
    (geo: { properties: { name: string }; id: string }) => {
      const fips = String(geo.id).padStart(2, "0");
      const code = FIPS_TO_CODE[fips];
      const state = code ? stateMap.get(code) : undefined;
      if (state) {
        setTooltipContent(
          `${state.name} (${state.code}): ${state.billCount.toLocaleString()} bills, ${state.legislatorCount.toLocaleString()} legislators`
        );
      } else {
        setTooltipContent(geo.properties.name || "Unknown");
      }
    },
    [stateMap]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      setTooltipPos({ x: e.clientX, y: e.clientY });
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    setTooltipContent("");
  }, []);

  const handleClick = useCallback(
    (geo: { id: string }) => {
      const fips = String(geo.id).padStart(2, "0");
      const code = FIPS_TO_CODE[fips];
      if (code && onStateClick) {
        onStateClick(code.toLowerCase());
      }
    },
    [onStateClick]
  );

  return (
    <div className="relative w-full">
      <ComposableMap
        projection="geoAlbersUsa"
        projectionConfig={{ scale: 1000 }}
        width={800}
        height={500}
        className="w-full h-auto"
      >
        <ZoomableGroup>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const fips = String(geo.id).padStart(2, "0");
                const code = FIPS_TO_CODE[fips];
                const state = code ? stateMap.get(code) : undefined;
                const billCount = state?.billCount ?? 0;

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    onMouseEnter={() => handleMouseEnter(geo)}
                    onMouseMove={handleMouseMove}
                    onMouseLeave={handleMouseLeave}
                    onClick={() => handleClick(geo)}
                    style={{
                      default: {
                        fill: getBillActivityColor(billCount, maxBills),
                        stroke: "#94a3b8",
                        strokeWidth: 0.5,
                        outline: "none",
                        cursor: "pointer",
                      },
                      hover: {
                        fill: "#3b82f6",
                        stroke: "#fff",
                        strokeWidth: 1,
                        outline: "none",
                        cursor: "pointer",
                      },
                      pressed: {
                        fill: "#2563eb",
                        stroke: "#fff",
                        strokeWidth: 1,
                        outline: "none",
                      },
                    }}
                  />
                );
              })
            }
          </Geographies>
        </ZoomableGroup>
      </ComposableMap>

      {/* Tooltip */}
      {tooltipContent && (
        <div
          className="fixed z-50 pointer-events-none px-3 py-2 text-sm bg-popover text-popover-foreground border rounded-md shadow-md"
          style={{
            left: tooltipPos.x + 12,
            top: tooltipPos.y - 40,
          }}
        >
          {tooltipContent}
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-[#334155]" />
          <span>No data</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-[#16a34a]" />
          <span>Low</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-[#ca8a04]" />
          <span>Moderate</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-[#ea580c]" />
          <span>High</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-[#dc2626]" />
          <span>Very High</span>
        </div>
        <span className="ml-2">Legislative Activity</span>
      </div>
    </div>
  );
}
