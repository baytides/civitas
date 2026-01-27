"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, snakeToTitle } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// =============================================================================
// Types
// =============================================================================

interface APIObjective {
  id: number;
  section: string;
  chapter: string | null;
  agency: string;
  proposal_text: string;
  proposal_summary: string | null;
  page_number: number;
  category: string;
  action_type: string;
  priority: string;
  implementation_timeline: string;
  status: string;
  confidence: number;
}

interface ResistanceRecommendation {
  tier: string;
  action_type: string;
  title: string;
  description: string;
  legal_basis: string | null;
  likelihood: string;
  prerequisites: string[];
}

interface ResistanceAnalysis {
  objective_id: number;
  constitutional_issues: Array<{
    issue: string;
    amendment?: string;
    precedent?: string;
    strength?: string;
  }>;
  challenge_strategies: Array<{
    strategy: string;
    description?: string;
    likelihood?: string;
    timeframe?: string;
  }>;
  state_resistance_options: Array<{
    option: string;
    description?: string;
    states_likely?: string[];
  }>;
  overall_vulnerability_score: number;
}

interface ProgressSummary {
  total_objectives: number;
  by_status: Record<string, number>;
  completion_percentage: number;
  recent_activity: Array<{ description: string; date?: string }>;
  blocked_count: number;
}

interface BlockedPolicy {
  objective_id: number;
  agency: string;
  proposal_summary: string;
  blocked_by: string;
  case_or_action: string;
  blocked_date: string | null;
}

interface ResistanceTierAction {
  title: string;
  description: string;
  urgency: string;
  resources: string[];
}

interface ResistanceTier {
  tier: number;
  id: string;
  title: string;
  subtitle: string;
  color: string;
  description: string;
  general_actions: ResistanceTierAction[];
}

interface ResistanceOrganization {
  name: string;
  url: string;
}

interface ResistanceOrganizationSection {
  title: string;
  items: ResistanceOrganization[];
}

interface ResistanceMeta {
  tiers: ResistanceTier[];
  organization_sections: ResistanceOrganizationSection[];
}

const urgencyColors = {
  critical: "bg-red-500 text-white",
  high: "bg-orange-500 text-white",
  medium: "bg-yellow-500 text-black",
  low: "bg-blue-500 text-white",
};

const tierColors = {
  green: {
    border: "border-l-green-500",
    bg: "bg-green-500",
    text: "text-green-600",
    light: "bg-green-50 dark:bg-green-950/20",
  },
  yellow: {
    border: "border-l-yellow-500",
    bg: "bg-yellow-500",
    text: "text-yellow-600",
    light: "bg-yellow-50 dark:bg-yellow-950/20",
  },
  blue: {
    border: "border-l-blue-500",
    bg: "bg-blue-500",
    text: "text-blue-600",
    light: "bg-blue-50 dark:bg-blue-950/20",
  },
  gray: {
    border: "border-l-gray-400",
    bg: "bg-gray-500",
    text: "text-gray-600",
    light: "bg-gray-50 dark:bg-gray-950/20",
  },
};

const getTierColors = (color: string) =>
  tierColors[color as keyof typeof tierColors] ?? tierColors.gray;

// =============================================================================
// Components
// =============================================================================

function ResistanceContent() {
  const searchParams = useSearchParams();
  const objectiveIdParam = searchParams.get("objective");

  const [expertMode, setExpertMode] = useState(false);
  const [expandedTier, setExpandedTier] = useState<number>(1);
  const [selectedUrgency, setSelectedUrgency] = useState<string>("all");
  const [selectedObjective, setSelectedObjective] = useState<APIObjective | null>(null);
  const [recommendations, setRecommendations] = useState<ResistanceRecommendation[]>([]);
  const [analysis, setAnalysis] = useState<ResistanceAnalysis | null>(null);
  const [progress, setProgress] = useState<ProgressSummary | null>(null);
  const [blockedPolicies, setBlockedPolicies] = useState<BlockedPolicy[]>([]);
  const [highPriorityObjectives, setHighPriorityObjectives] = useState<APIObjective[]>([]);
  const [meta, setMeta] = useState<ResistanceMeta | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  // Fetch initial data
  useEffect(() => {
    async function fetchInitialData() {
      try {
        // Fetch progress summary
        const progressRes = await fetch(`${API_BASE}/resistance/progress`);
        if (progressRes.ok) {
          setProgress(await progressRes.json());
        }

        // Fetch blocked policies
        const blockedRes = await fetch(`${API_BASE}/resistance/blocked`);
        if (blockedRes.ok) {
          setBlockedPolicies(await blockedRes.json());
        }

        // Fetch high-priority objectives that are in progress or enacted
        const objRes = await fetch(`${API_BASE}/objectives?priority=high&per_page=10`);
        if (objRes.ok) {
          const data = await objRes.json();
          setHighPriorityObjectives(data.items || []);
        }

        const metaRes = await fetch(`${API_BASE}/resistance/meta`);
        if (metaRes.ok) {
          setMeta(await metaRes.json());
        }
      } catch (err) {
        console.error("Failed to fetch resistance data:", err);
      }
    }

    fetchInitialData();
  }, []);

  // Fetch specific objective if passed in URL
  useEffect(() => {
    if (objectiveIdParam) {
      fetchObjectiveDetails(parseInt(objectiveIdParam, 10));
    }
  }, [objectiveIdParam]);

  async function fetchObjectiveDetails(objectiveId: number) {
    setAnalysisLoading(true);
    try {
      // Fetch objective details
      const objRes = await fetch(`${API_BASE}/objectives/${objectiveId}`);
      if (objRes.ok) {
        setSelectedObjective(await objRes.json());
      }

      // Fetch recommendations for this objective
      const recRes = await fetch(`${API_BASE}/resistance/recommendations/${objectiveId}`);
      if (recRes.ok) {
        setRecommendations(await recRes.json());
      }

      // Fetch analysis (expert mode)
      if (expertMode) {
        const analysisRes = await fetch(`${API_BASE}/resistance/analysis/${objectiveId}`);
        if (analysisRes.ok) {
          setAnalysis(await analysisRes.json());
        }
      }
    } catch (err) {
      console.error("Failed to fetch objective details:", err);
    }
    setAnalysisLoading(false);
  }

  // Re-fetch analysis when expert mode is toggled
  useEffect(() => {
    if (expertMode && selectedObjective && !analysis) {
      fetchAnalysis(selectedObjective.id);
    }
  }, [expertMode, selectedObjective]);

  async function fetchAnalysis(objectiveId: number) {
    try {
      const analysisRes = await fetch(`${API_BASE}/resistance/analysis/${objectiveId}`);
      if (analysisRes.ok) {
        setAnalysis(await analysisRes.json());
      }
    } catch (err) {
      console.error("Failed to fetch analysis:", err);
    }
  }

  // Group recommendations by tier
  const recommendationsByTier = recommendations.reduce((acc, rec) => {
    if (!acc[rec.tier]) acc[rec.tier] = [];
    acc[rec.tier].push(rec);
    return acc;
  }, {} as Record<string, ResistanceRecommendation[]>);
  const tiers = meta?.tiers ?? [];
  const organizationSections = meta?.organization_sections ?? [];
  const hasTierData = tiers.length > 0;
  const hasOrgData = organizationSections.length > 0;

  return (
    <div className="container py-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2">Resistance Strategy</h1>
          <p className="text-muted-foreground max-w-3xl">
            A three-tier approach to protecting democracy. Focus on what is most
            effective now while building toward longer-term goals.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={expertMode}
              onChange={(e) => setExpertMode(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300"
            />
            <span className="text-sm font-medium">Expert Mode</span>
          </label>
          {expertMode && (
            <Badge variant="outline" className="bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300">
              Legal & Political Analysis
            </Badge>
          )}
        </div>
      </div>

      {/* Progress Summary */}
      {progress && (
        <Card className="mb-8">
          <CardContent className="pt-6">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
              <div>
                <p className="text-3xl font-bold">{progress.total_objectives}</p>
                <p className="text-sm text-muted-foreground">Total Objectives</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-red-600">{progress.by_status?.enacted || 0}</p>
                <p className="text-sm text-muted-foreground">Enacted</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-orange-600">{progress.by_status?.in_progress || 0}</p>
                <p className="text-sm text-muted-foreground">In Progress</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-green-600">{progress.blocked_count}</p>
                <p className="text-sm text-muted-foreground">Blocked</p>
              </div>
              <div>
                <p className="text-3xl font-bold">{Math.round(progress.completion_percentage)}%</p>
                <p className="text-sm text-muted-foreground">Implementation</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Selected Objective (if any) */}
      {selectedObjective && (
        <Card className="mb-8 border-2 border-primary">
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <Badge variant="outline" className="mb-2">{snakeToTitle(selectedObjective.category)}</Badge>
                <CardTitle className="text-xl">Analyzing: {selectedObjective.agency}</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  {selectedObjective.proposal_summary || selectedObjective.proposal_text.slice(0, 200)}...
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSelectedObjective(null);
                  setRecommendations([]);
                  setAnalysis(null);
                }}
              >
                Clear Selection
              </Button>
            </div>
          </CardHeader>
          {analysisLoading && (
            <CardContent>
              <div className="flex items-center gap-2 text-muted-foreground">
                <div className="animate-spin w-4 h-4 border-2 border-primary border-t-transparent rounded-full" />
                Loading personalized recommendations...
              </div>
            </CardContent>
          )}
        </Card>
      )}

      {/* Expert Mode: Legal Analysis */}
      {expertMode && analysis && (
        <div className="mb-8 space-y-4">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <span className="bg-purple-100 dark:bg-purple-900/30 px-2 py-1 rounded text-purple-700 dark:text-purple-300 text-sm">EXPERT</span>
            Legal Vulnerability Analysis
          </h2>

          {/* Vulnerability Score */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">Overall Vulnerability Score</h3>
                  <p className="text-sm text-muted-foreground">
                    Likelihood of successful legal challenge
                  </p>
                </div>
                <div className="text-right">
                  <span className={cn(
                    "text-4xl font-bold",
                    analysis.overall_vulnerability_score >= 70 ? "text-green-600" :
                    analysis.overall_vulnerability_score >= 40 ? "text-yellow-600" : "text-red-600"
                  )}>
                    {analysis.overall_vulnerability_score}%
                  </span>
                  <p className="text-xs text-muted-foreground">
                    {analysis.overall_vulnerability_score >= 70 ? "High chance of challenge" :
                     analysis.overall_vulnerability_score >= 40 ? "Moderate vulnerability" : "Difficult to challenge"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Constitutional Issues */}
          {analysis.constitutional_issues.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Constitutional Issues</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {analysis.constitutional_issues.map((issue, idx) => (
                    <div key={idx} className="p-3 bg-muted/50 rounded-lg">
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-medium">{issue.issue}</h4>
                        {issue.strength && (
                          <Badge variant={issue.strength === "strong" ? "default" : "outline"}>
                            {issue.strength}
                          </Badge>
                        )}
                      </div>
                      {issue.amendment && (
                        <p className="text-sm text-muted-foreground mt-1">Amendment: {issue.amendment}</p>
                      )}
                      {issue.precedent && (
                        <p className="text-sm text-muted-foreground">Precedent: {issue.precedent}</p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Challenge Strategies */}
          {analysis.challenge_strategies.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Challenge Strategies</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {analysis.challenge_strategies.map((strategy, idx) => (
                    <div key={idx} className="p-3 border rounded-lg">
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-medium">{strategy.strategy}</h4>
                        {strategy.likelihood && (
                          <Badge variant={
                            strategy.likelihood === "high" ? "default" :
                            strategy.likelihood === "medium" ? "secondary" : "outline"
                          }>
                            {strategy.likelihood} likelihood
                          </Badge>
                        )}
                      </div>
                      {strategy.description && (
                        <p className="text-sm text-muted-foreground mt-1">{strategy.description}</p>
                      )}
                      {strategy.timeframe && (
                        <p className="text-xs text-muted-foreground mt-1">Timeframe: {strategy.timeframe}</p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* State Resistance Options */}
          {analysis.state_resistance_options.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">State Resistance Options</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {analysis.state_resistance_options.map((option, idx) => (
                    <div key={idx} className="p-3 border rounded-lg">
                      <h4 className="font-medium">{option.option}</h4>
                      {option.description && (
                        <p className="text-sm text-muted-foreground mt-1">{option.description}</p>
                      )}
                      {option.states_likely && option.states_likely.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {option.states_likely.map((state) => (
                            <Badge key={state} variant="outline" className="text-xs">
                              {state}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Blocked Policies (Success Stories) */}
      {blockedPolicies.length > 0 && (
        <Card className="mb-8 border-green-500/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span className="text-green-600">Blocked Policies</span>
              <Badge variant="outline" className="bg-green-100 dark:bg-green-900/30">
                {blockedPolicies.length} Victories
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2">
              {blockedPolicies.slice(0, 4).map((policy) => (
                <div key={policy.objective_id} className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="font-medium text-sm">{policy.agency}</h4>
                    <Badge className="bg-green-600">{policy.blocked_by}</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{policy.proposal_summary}</p>
                  {policy.case_or_action && (
                    <p className="text-xs text-green-700 dark:text-green-400 mt-1">{policy.case_or_action}</p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* High Priority Objectives to Take Action On */}
      {highPriorityObjectives.length > 0 && !selectedObjective && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-lg">Take Action on High-Priority Threats</CardTitle>
            <p className="text-sm text-muted-foreground">
              Select an objective to see personalized resistance recommendations
            </p>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {highPriorityObjectives.map((obj) => (
                <button
                  key={obj.id}
                  onClick={() => fetchObjectiveDetails(obj.id)}
                  className="p-3 border rounded-lg text-left hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <Badge variant="outline" className="text-xs">{snakeToTitle(obj.category)}</Badge>
                    <Badge variant={obj.status === "enacted" ? "critical" : obj.status === "in_progress" ? "elevated" : "outline"} className="text-xs">
                      {snakeToTitle(obj.status)}
                    </Badge>
                  </div>
                  <h4 className="font-medium text-sm">{obj.agency}</h4>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                    {obj.proposal_summary || obj.proposal_text.slice(0, 100)}...
                  </p>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Strategy Overview */}
      <Card className="mb-8">
        <CardContent className="pt-6">
          {hasTierData ? (
            <div className="grid md:grid-cols-3 gap-6">
              {tiers.map((tier) => {
                const colors = getTierColors(tier.color);
                const tierRecs = recommendationsByTier[tier.id] || [];
                const hasPersonalized = tierRecs.length > 0;

                return (
                  <button
                    key={tier.tier}
                    className={cn(
                      "w-full p-4 rounded-lg border-l-4 text-left transition-colors relative",
                      colors.border,
                      expandedTier === tier.tier ? colors.light : "hover:bg-muted/50"
                    )}
                    onClick={() => setExpandedTier(expandedTier === tier.tier ? 0 : tier.tier)}
                    type="button"
                    aria-pressed={expandedTier === tier.tier}
                  >
                    {hasPersonalized && (
                      <Badge className="absolute top-2 right-2 bg-primary text-xs">
                        {tierRecs.length} personalized
                      </Badge>
                    )}
                    <div className="flex items-center gap-3 mb-2">
                      <span className={cn(
                        "inline-flex items-center justify-center w-8 h-8 rounded-full text-white font-bold",
                        colors.bg
                      )}>
                        {tier.tier}
                      </span>
                      <div>
                        <h3 className="font-semibold">{tier.title}</h3>
                        <p className="text-xs text-muted-foreground">{tier.subtitle}</p>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground line-clamp-2">{tier.description}</p>
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Resistance tiers are unavailable right now.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Urgency Filter */}
      <fieldset className="flex items-center gap-2 mb-6 border-0 p-0 m-0">
        <legend className="text-sm text-muted-foreground">Filter by urgency:</legend>
        {["all", "critical", "high", "medium"].map((level) => (
          <Button
            key={level}
            variant={selectedUrgency === level ? "default" : "outline"}
            size="sm"
            className={selectedUrgency === level && level !== "all" ? urgencyColors[level as keyof typeof urgencyColors] : ""}
            onClick={() => setSelectedUrgency(level)}
            aria-pressed={selectedUrgency === level}
          >
            {level.charAt(0).toUpperCase() + level.slice(1)}
          </Button>
        ))}
      </fieldset>

      {/* Tier Details */}
      <div className="space-y-8">
        {hasTierData ? tiers.map((tier) => {
          const colors = getTierColors(tier.color);
          const tierRecs = recommendationsByTier[tier.id] || [];
          const filteredGeneralActions = selectedUrgency === "all"
            ? tier.general_actions
            : tier.general_actions.filter((a) => a.urgency === selectedUrgency);

          // Filter personalized recommendations by urgency
          const filteredRecs = selectedUrgency === "all"
            ? tierRecs
            : tierRecs.filter((r) => r.likelihood === selectedUrgency || selectedUrgency === "all");

          const hasContent = filteredGeneralActions.length > 0 || filteredRecs.length > 0;
          if (!hasContent) return null;

          return (
            <Card key={tier.tier} className={cn("border-l-4", colors.border)}>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <span className={cn(
                    "inline-flex items-center justify-center w-10 h-10 rounded-full text-white font-bold text-lg",
                    colors.bg
                  )}>
                    {tier.tier}
                  </span>
                  <div>
                    <CardTitle>{tier.title}</CardTitle>
                    <p className="text-sm text-muted-foreground">{tier.subtitle}</p>
                  </div>
                </div>
                <p className="text-muted-foreground mt-2">{tier.description}</p>
              </CardHeader>
              <CardContent>
                {/* Personalized Recommendations */}
                {filteredRecs.length > 0 && (
                  <div className="mb-6">
                    <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <Badge className="bg-primary">Personalized</Badge>
                      Based on selected objective
                    </h4>
                    <div className="grid gap-4 md:grid-cols-2">
                      {filteredRecs.map((rec, idx) => (
                        <PersonalizedActionCard key={idx} recommendation={rec} expertMode={expertMode} />
                      ))}
                    </div>
                  </div>
                )}

                {/* General Actions */}
                <div className={filteredRecs.length > 0 ? "pt-4 border-t" : ""}>
                  {filteredRecs.length > 0 && (
                    <h4 className="text-sm font-semibold mb-3 text-muted-foreground">General Actions</h4>
                  )}
                  <div className="grid gap-4 md:grid-cols-2">
                    {filteredGeneralActions.map((action, idx) => (
                      <GeneralActionCard key={idx} action={action} />
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        }) : (
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">
                No resistance tier content is available right now.
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Resources Section */}
      <section className="mt-12">
        <h2 className="text-2xl font-bold mb-6">Key Organizations</h2>
        {hasOrgData ? (
          <div className="grid gap-4 md:grid-cols-3">
            {organizationSections.map((section) => (
              <Card key={section.title}>
                <CardHeader>
                  <CardTitle className="text-lg">{section.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm">
                    {section.items.map((item) => (
                      <li key={item.url}>
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:underline"
                        >
                          {item.name}
                        </a>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Organization resources are unavailable right now.
          </p>
        )}
      </section>
    </div>
  );
}

// =============================================================================
// Action Card Components
// =============================================================================

interface PersonalizedActionCardProps {
  recommendation: ResistanceRecommendation;
  expertMode: boolean;
}

function PersonalizedActionCard({ recommendation, expertMode }: PersonalizedActionCardProps) {
  return (
    <div className="p-4 rounded-lg border bg-card border-primary/30">
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className="font-semibold">{recommendation.title}</h4>
        <Badge className={cn(
          recommendation.likelihood === "high" ? "bg-green-600" :
          recommendation.likelihood === "medium" ? "bg-yellow-600" : "bg-gray-600"
        )}>
          {recommendation.likelihood} likelihood
        </Badge>
      </div>
      <p className="text-sm text-muted-foreground mb-3">{recommendation.description}</p>

      {expertMode && recommendation.legal_basis && (
        <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded text-xs mb-3">
          <span className="font-medium text-purple-700 dark:text-purple-300">Legal Basis:</span>
          <span className="ml-1 text-muted-foreground">{recommendation.legal_basis}</span>
        </div>
      )}

      {recommendation.prerequisites.length > 0 && (
        <div className="text-xs text-muted-foreground">
          <span className="font-medium">Prerequisites:</span>
          <ul className="list-disc list-inside mt-1">
            {recommendation.prerequisites.map((prereq, idx) => (
              <li key={idx}>{prereq}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

interface GeneralActionCardProps {
  action: {
    title: string;
    description: string;
    urgency: string;
    resources: string[];
  };
}

function GeneralActionCard({ action }: GeneralActionCardProps) {
  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className="font-semibold">{action.title}</h4>
        <Badge className={cn(urgencyColors[action.urgency as keyof typeof urgencyColors])}>
          {action.urgency}
        </Badge>
      </div>
      <p className="text-sm text-muted-foreground mb-3">{action.description}</p>
      <div className="flex flex-wrap gap-1">
        {action.resources.map((resource) => (
          <Badge key={resource} variant="outline" className="text-xs">
            {resource}
          </Badge>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// Loading State
// =============================================================================

function ResistanceLoading() {
  return (
    <div className="container py-8">
      <div className="mb-8">
        <Skeleton className="h-9 w-64 mb-2" />
        <Skeleton className="h-5 w-96" />
      </div>
      <Card className="mb-8">
        <CardContent className="pt-6">
          <div className="grid grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-20" />
            ))}
          </div>
        </CardContent>
      </Card>
      <Card className="mb-8">
        <CardContent className="pt-6">
          <div className="grid md:grid-cols-3 gap-6">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// Main Export
// =============================================================================

export default function ResistancePage() {
  return (
    <Suspense fallback={<ResistanceLoading />}>
      <ResistanceContent />
    </Suspense>
  );
}
