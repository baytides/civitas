/**
 * API client for communicating with the Civitas FastAPI backend.
 * All data is fetched from our own backend, which holds ingested data
 * from Congress.gov, state legislatures, courts, etc.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// Types matching FastAPI schemas
export interface ObjectiveBase {
  id: string;
  category: string;
  subcategory: string | null;
  title: string;
  description: string;
  source_page: number | null;
  implementation_status: "not_started" | "proposed" | "in_progress" | "enacted" | "blocked";
  threat_level: "critical" | "high" | "elevated" | "moderate";
  progress_percentage: number;
}

export interface ObjectiveDetail extends ObjectiveBase {
  related_legislation: LegislationBase[];
  related_executive_orders: ExecutiveOrderBase[];
  related_court_cases: CourtCaseBase[];
  resistance_actions: ResistanceAction[];
  timeline: TimelineEvent[];
}

export interface ObjectiveStats {
  total: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_threat_level: Record<string, number>;
  overall_progress: number;
}

export interface LegislationBase {
  id: number;
  jurisdiction: string;
  legislation_type: string;
  number: number;
  title: string;
  status: string;
  is_enacted: boolean;
  introduced_date: string | null;
}

export interface ExecutiveOrderBase {
  id: number;
  order_number: number | null;
  title: string;
  signing_date: string | null;
  president: string | null;
  status: string;
  summary: string | null;
}

export interface CourtCaseBase {
  id: number;
  citation: string;
  case_name: string;
  court: string;
  court_level: string;
  decision_date: string | null;
  status: string | null;
  outcome: string | null;
}

export interface StateBase {
  code: string;
  name: string;
  resistance_score: number;
  protection_level: "strong" | "moderate" | "weak" | "hostile";
  governor_party: string | null;
  legislature_control: string | null;
  active_protections: number;
  pending_threats: number;
}

export interface StateDetail extends StateBase {
  recent_legislation: LegislationBase[];
  court_cases: CourtCaseBase[];
  resistance_actions: ResistanceAction[];
}

export interface ResistanceAction {
  id: string;
  tier: 1 | 2 | 3;
  action_type: string;
  title: string;
  description: string;
  target_entity: string | null;
  urgency: "critical" | "high" | "medium" | "low";
  effectiveness: number;
  resources: string[];
}

export interface ResistanceRecommendation {
  state: string;
  priority_actions: ResistanceAction[];
  state_specific: ResistanceAction[];
  federal_actions: ResistanceAction[];
}

export interface TimelineEvent {
  date: string;
  event_type: string;
  title: string;
  description: string;
  source_url: string | null;
}

export interface SearchResult {
  type: "objective" | "legislation" | "case" | "executive_order";
  id: string | number;
  title: string;
  snippet: string;
  relevance_score: number;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: SearchResult[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// API Error handling
class APIError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message?: string
  ) {
    super(message || `API Error: ${status} ${statusText}`);
    this.name = "APIError";
  }
}

async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new APIError(response.status, response.statusText);
  }

  return response.json();
}

// Objectives API
export const objectivesAPI = {
  list: (params?: {
    category?: string;
    status?: string;
    threat_level?: string;
    page?: number;
    per_page?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.set("category", params.category);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.threat_level) searchParams.set("threat_level", params.threat_level);
    if (params?.page) searchParams.set("page", params.page.toString());
    if (params?.per_page) searchParams.set("per_page", params.per_page.toString());

    const query = searchParams.toString();
    return fetchAPI<PaginatedResponse<ObjectiveBase>>(
      `/objectives${query ? `?${query}` : ""}`
    );
  },

  get: (id: string) => fetchAPI<ObjectiveDetail>(`/objectives/${id}`),

  stats: () => fetchAPI<ObjectiveStats>("/objectives/stats"),
};

// Executive Orders API
export const executiveOrdersAPI = {
  list: (params?: {
    president?: string;
    status?: string;
    page?: number;
    per_page?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.president) searchParams.set("president", params.president);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.page) searchParams.set("page", params.page.toString());
    if (params?.per_page) searchParams.set("per_page", params.per_page.toString());

    const query = searchParams.toString();
    return fetchAPI<PaginatedResponse<ExecutiveOrderBase>>(
      `/executive-orders${query ? `?${query}` : ""}`
    );
  },

  get: (id: number) => fetchAPI<ExecutiveOrderBase>(`/executive-orders/${id}`),

  recent: (days?: number) =>
    fetchAPI<ExecutiveOrderBase[]>(
      `/executive-orders/recent${days ? `?days=${days}` : ""}`
    ),
};

// Court Cases API
export const casesAPI = {
  list: (params?: {
    court_level?: string;
    status?: string;
    page?: number;
    per_page?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.court_level) searchParams.set("court_level", params.court_level);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.page) searchParams.set("page", params.page.toString());
    if (params?.per_page) searchParams.set("per_page", params.per_page.toString());

    const query = searchParams.toString();
    return fetchAPI<PaginatedResponse<CourtCaseBase>>(
      `/cases${query ? `?${query}` : ""}`
    );
  },

  get: (id: number) => fetchAPI<CourtCaseBase>(`/cases/${id}`),

  byObjective: (objectiveId: string) =>
    fetchAPI<CourtCaseBase[]>(`/cases/objective/${objectiveId}`),
};

// States API
export const statesAPI = {
  list: () => fetchAPI<StateBase[]>("/states"),

  get: (code: string) => fetchAPI<StateDetail>(`/states/${code}`),

  map: () => fetchAPI<Record<string, StateBase>>("/states/map"),
};

// Resistance API
export const resistanceAPI = {
  recommendations: (state?: string) =>
    fetchAPI<ResistanceRecommendation>(
      `/resistance/recommendations${state ? `?state=${state}` : ""}`
    ),

  actions: (params?: { tier?: number; urgency?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.tier) searchParams.set("tier", params.tier.toString());
    if (params?.urgency) searchParams.set("urgency", params.urgency);

    const query = searchParams.toString();
    return fetchAPI<ResistanceAction[]>(
      `/resistance/actions${query ? `?${query}` : ""}`
    );
  },
};

// Search API
export const searchAPI = {
  search: (query: string, params?: { type?: string; limit?: number }) => {
    const searchParams = new URLSearchParams({ q: query });
    if (params?.type) searchParams.set("type", params.type);
    if (params?.limit) searchParams.set("limit", params.limit.toString());

    return fetchAPI<SearchResponse>(`/search?${searchParams.toString()}`);
  },
};

// Export a unified API object
export const api = {
  objectives: objectivesAPI,
  executiveOrders: executiveOrdersAPI,
  cases: casesAPI,
  states: statesAPI,
  resistance: resistanceAPI,
  search: searchAPI,
};

export default api;
