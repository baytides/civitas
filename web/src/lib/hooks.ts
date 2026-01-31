/**
 * React hooks for fetching data from the Civitas API.
 * Used for client-side data fetching in static export.
 */
"use client";

import { useState, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://api.projectcivitas.com/api/v1";

interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

export function useAPI<T>(endpoint: string): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) {
          throw new Error(`API Error: ${response.status}`);
        }
        const data = await response.json();
        setState({ data, loading: false, error: null });
      } catch (error) {
        setState({ data: null, loading: false, error: error as Error });
      }
    };

    fetchData();
  }, [endpoint]);

  return state;
}

// Typed hooks for specific endpoints
export function useObjectives(params?: {
  category?: string;
  status?: string;
  threat_level?: string;
  page?: number;
  per_page?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set("category", params.category);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.threat_level) searchParams.set("threat_level", params.threat_level);
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.per_page) searchParams.set("per_page", params.per_page.toString());

  const query = searchParams.toString();
  return useAPI<{
    items: Array<{
      id: string;
      category: string;
      subcategory: string | null;
      title: string;
      description: string;
      source_page: number | null;
      implementation_status: string;
      threat_level: string;
      progress_percentage: number;
    }>;
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
  }>(`/objectives${query ? `?${query}` : ""}`);
}

export function useObjectiveStats() {
  return useAPI<{
    total: number;
    by_status: Record<string, number>;
    by_category: Record<string, number>;
    by_threat_level: Record<string, number>;
    overall_progress: number;
  }>("/objectives/stats");
}

export function useExecutiveOrders(params?: {
  president?: string;
  status?: string;
  page?: number;
  per_page?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.president) searchParams.set("president", params.president);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.per_page) searchParams.set("per_page", params.per_page.toString());

  const query = searchParams.toString();
  return useAPI<{
    items: Array<{
      id: number;
      order_number: number | null;
      title: string;
      signing_date: string | null;
      president: string | null;
      status: string;
      summary: string | null;
    }>;
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
  }>(`/executive-orders${query ? `?${query}` : ""}`);
}

export function useLegislation(params?: {
  jurisdiction?: string;
  status?: string;
  page?: number;
  per_page?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.jurisdiction) searchParams.set("jurisdiction", params.jurisdiction);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.per_page) searchParams.set("per_page", params.per_page.toString());

  const query = searchParams.toString();
  return useAPI<{
    items: Array<{
      id: number;
      jurisdiction: string;
      legislation_type: string;
      number: number;
      title: string;
      status: string;
      is_enacted: boolean;
      introduced_date: string | null;
    }>;
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
  }>(`/legislation${query ? `?${query}` : ""}`);
}

export function useStates() {
  return useAPI<Array<{
    code: string;
    name: string;
    resistance_score: number;
    protection_level: string;
    governor_party: string | null;
    legislature_control: string | null;
    active_protections: number;
    pending_threats: number;
  }>>("/states");
}

export function useDBStats() {
  return useAPI<{
    legislation: number;
    enacted: number;
    executive_orders: number;
    legislators: number;
  }>("/stats");
}
