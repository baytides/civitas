import { ImageResponse } from "next/og";
import { NextRequest } from "next/server";

export const runtime = "edge";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const title = searchParams.get("title") || "Project Civitas";
  const subtitle =
    searchParams.get("subtitle") || "Tracking Project 2025 Implementation";
  const type = searchParams.get("type") || "page";

  const typeColors: Record<string, string> = {
    objective: "#7c3aed",
    executive_order: "#9333ea",
    court_case: "#d97706",
    legislation: "#2563eb",
    state: "#059669",
    page: "#1e293b",
  };

  const accentColor = typeColors[type] || typeColors.page;

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          backgroundColor: "#0f172a",
          padding: "60px",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        {/* Top accent bar */}
        <div
          style={{
            width: "100%",
            height: "6px",
            backgroundColor: accentColor,
            borderRadius: "3px",
            marginBottom: "40px",
          }}
        />

        {/* Type badge */}
        <div
          style={{
            display: "flex",
            marginBottom: "20px",
          }}
        >
          <span
            style={{
              backgroundColor: accentColor,
              color: "white",
              padding: "6px 16px",
              borderRadius: "20px",
              fontSize: "18px",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            {type.replace(/_/g, " ")}
          </span>
        </div>

        {/* Title */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            flex: 1,
            justifyContent: "center",
          }}
        >
          <h1
            style={{
              color: "white",
              fontSize: title.length > 80 ? "36px" : "48px",
              fontWeight: 700,
              lineHeight: 1.2,
              margin: 0,
              maxWidth: "900px",
            }}
          >
            {title.length > 120 ? title.slice(0, 117) + "..." : title}
          </h1>
          {subtitle && (
            <p
              style={{
                color: "#94a3b8",
                fontSize: "24px",
                marginTop: "16px",
                maxWidth: "800px",
              }}
            >
              {subtitle.length > 100
                ? subtitle.slice(0, 97) + "..."
                : subtitle}
            </p>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: "40px",
          }}
        >
          <span
            style={{
              color: "#64748b",
              fontSize: "20px",
              fontWeight: 600,
            }}
          >
            projectcivitas.com
          </span>
          <span
            style={{
              color: "#475569",
              fontSize: "16px",
            }}
          >
            Civic Accountability Platform
          </span>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
