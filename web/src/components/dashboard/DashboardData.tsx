"use client";

import { useState, useEffect } from "react";
import { StatsGrid } from "./StatsGrid";
import { Skeleton } from "@/components/ui/skeleton";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface DashboardStats {
  totalPolicies: number;
  executiveOrders: number;
  states: number;
  courtCases: number;
}

export function DashboardDataLoader() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStats() {
      try {
        // Fetch executive orders count
        let eoCount = 0;
        try {
          const eoResponse = await fetch(`${API_BASE}/executive-orders?per_page=1`);
          if (eoResponse.ok) {
            const eoData = await eoResponse.json();
            eoCount = eoData.total || 0;
          }
        } catch {
          // API unavailable
        }

        // Fetch P2025 objectives/policies count from /objectives/stats
        let policiesCount = 0;
        try {
          const policiesResponse = await fetch(`${API_BASE}/objectives/stats`);
          if (policiesResponse.ok) {
            const policiesData = await policiesResponse.json();
            policiesCount = policiesData.total || 0;
          }
        } catch {
          // API unavailable
        }

        // Fetch states count
        let statesCount = 0;
        try {
          const statesResponse = await fetch(`${API_BASE}/states`);
          if (statesResponse.ok) {
            const statesData = await statesResponse.json();
            statesCount = statesData.items?.length || 0;
          }
        } catch {
          // API unavailable
        }

        // Fetch court cases count from /cases
        let courtCasesCount = 0;
        try {
          const casesResponse = await fetch(`${API_BASE}/cases?per_page=1`);
          if (casesResponse.ok) {
            const casesData = await casesResponse.json();
            courtCasesCount = casesData.total || 0;
          }
        } catch {
          // API unavailable
        }

        setStats({
          totalPolicies: policiesCount,
          executiveOrders: eoCount,
          states: statesCount,
          courtCases: courtCasesCount,
        });
        setLoading(false);
      } catch {
        setError("Failed to load dashboard data");
        setLoading(false);
        setStats({
          totalPolicies: 0,
          executiveOrders: 0,
          states: 0,
          courtCases: 0,
        });
      }
    }

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  if (error && !stats) {
    return <div className="text-destructive">{error}</div>;
  }

  return <StatsGrid stats={stats!} />;
}

interface ExecutiveOrder {
  id: number;
  document_number: string;
  executive_order_number: number | null;
  title: string;
  signing_date: string | null;
  publication_date: string | null;
  president: string | null;
  abstract: string | null;
}

export function RecentExecutiveOrders({ limit = 5 }: { limit?: number }) {
  const [orders, setOrders] = useState<ExecutiveOrder[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchOrders() {
      try {
        const response = await fetch(`${API_BASE}/executive-orders?per_page=${limit}`);
        const data = await response.json();
        setOrders(data.items || []);
      } catch {
        // Silently fail, will show empty state
      }
      setLoading(false);
    }

    fetchOrders();
  }, [limit]);

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(limit)].map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (orders.length === 0) {
    return <p className="text-muted-foreground">No executive orders found.</p>;
  }

  return (
    <div className="space-y-3">
      {orders.map((order) => (
        <div key={order.id} className="p-3 border rounded-lg">
          <h4 className="font-medium text-sm line-clamp-2">{order.title}</h4>
          <p className="text-xs text-muted-foreground mt-1">
            {order.publication_date || "Date unknown"}
            {order.executive_order_number && ` | EO ${order.executive_order_number}`}
          </p>
        </div>
      ))}
    </div>
  );
}
