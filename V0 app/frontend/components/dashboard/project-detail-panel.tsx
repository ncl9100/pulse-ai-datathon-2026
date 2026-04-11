"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, TrendingDown, Lightbulb, BarChart3, Activity, Sparkles, X } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CauseChainChart } from "./cause-chain-chart";
import { CPITrendChart } from "./cpi-trend-chart";
import { cn, formatCurrency, getRiskBgColor } from "@/lib/utils";
import type { ProjectRow } from "./project-table";

interface AIInsights {
  risk_summary: string;
  root_causes: string[];
  recovery_actions: {
    action: string;
    estimated_impact: string;
  }[];
}

interface CauseChainData {
  chain_a_design_rework: number;
  chain_b_material_idle: number;
  chain_c_rfi_standby: number;
  chain_d_rejected_co_loss: number;
  chain_e_early_co_signals: number;
}

interface ProjectDetailPanelProps {
  project: ProjectRow | null;
  onClose: () => void;
  sessionId: string;
  causeChainData?: CauseChainData;
}

export function ProjectDetailPanel({ project, onClose, sessionId, causeChainData }: ProjectDetailPanelProps) {
  const [insights, setInsights] = useState<AIInsights | null>(null);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [insightsError, setInsightsError] = useState<string | null>(null);

  useEffect(() => {
    if (!project) {
      setInsights(null);
      return;
    }

    const fetchInsights = async () => {
      setLoadingInsights(true);
      setInsightsError(null);

      try {
        const response = await fetch("/api/insights", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: project.project_id,
            risk_score: project.risk_score_0_100,
            risk_category: project.risk_category,
            cpi: project.project_cpi,
            early_rfi_count: project.early_rfi_count,
            early_ot_ratio_pct: project.early_ot_ratio_pct,
            variance_at_completion: project.variance_at_completion,
            cause_chain: causeChainData,
          }),
        });

        if (!response.ok) {
          throw new Error("Failed to fetch AI insights");
        }

        const data = await response.json();
        setInsights(data);
      } catch (error) {
        console.error("Error fetching insights:", error);
        setInsightsError("Unable to load AI insights. Please try again.");
      } finally {
        setLoadingInsights(false);
      }
    };

    fetchInsights();
  }, [project, causeChainData]);

  if (!project) return null;

  const defaultCauseChain: CauseChainData = causeChainData || {
    chain_a_design_rework: 25,
    chain_b_material_idle: 20,
    chain_c_rfi_standby: 15,
    chain_d_rejected_co_loss: 25,
    chain_e_early_co_signals: 15,
  };

  return (
    <Sheet open={!!project} onOpenChange={() => onClose()}>
      <SheetContent className="w-full overflow-hidden p-0 sm:max-w-xl">
        <ScrollArea className="h-full">
          <div className="p-6">
            <SheetHeader className="space-y-1">
              <div className="flex items-start justify-between">
                <div>
                  <SheetTitle className="text-xl">{project.project_id}</SheetTitle>
                  <SheetDescription>Project Risk Analysis</SheetDescription>
                </div>
                <Badge className={cn(getRiskBgColor(project.risk_category), "text-sm")}>
                  {project.risk_category}
                </Badge>
              </div>
            </SheetHeader>

            {/* Risk Score */}
            <div className="mt-6 rounded-lg border bg-muted/30 p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Risk Score</span>
                <span className="text-2xl font-bold tabular-nums">{project.risk_score_0_100.toFixed(0)}/100</span>
              </div>
              <div className="mt-2 h-3 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    project.risk_score_0_100 >= 75 && "bg-red-500",
                    project.risk_score_0_100 >= 55 && project.risk_score_0_100 < 75 && "bg-amber-500",
                    project.risk_score_0_100 >= 30 && project.risk_score_0_100 < 55 && "bg-blue-500",
                    project.risk_score_0_100 < 30 && "bg-green-500"
                  )}
                  style={{ width: `${project.risk_score_0_100}%` }}
                />
              </div>
            </div>

            {/* Key Metrics */}
            <div className="mt-4 grid grid-cols-3 gap-3">
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">CPI</p>
                <p className={cn("text-lg font-semibold tabular-nums", project.project_cpi < 1 && "text-red-600")}>
                  {project.project_cpi.toFixed(2)}
                </p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">Early RFIs</p>
                <p className="text-lg font-semibold tabular-nums">{project.early_rfi_count}</p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">OT Ratio</p>
                <p className="text-lg font-semibold tabular-nums">{project.early_ot_ratio_pct.toFixed(1)}%</p>
              </div>
            </div>

            <Separator className="my-6" />

            {/* Tabs for different views */}
            <Tabs defaultValue="insights" className="w-full">
              <TabsList className="w-full">
                <TabsTrigger value="insights" className="flex-1">
                  <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                  AI Insights
                </TabsTrigger>
                <TabsTrigger value="analysis" className="flex-1">
                  <BarChart3 className="mr-1.5 h-3.5 w-3.5" />
                  Analysis
                </TabsTrigger>
              </TabsList>

              <TabsContent value="insights" className="mt-4 space-y-6">
                {loadingInsights ? (
                  <div className="flex flex-col items-center justify-center py-12">
                    <Spinner size="lg" />
                    <p className="mt-4 text-sm text-muted-foreground">Analyzing project with AI...</p>
                  </div>
                ) : insightsError ? (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                    <p className="text-sm text-red-700">{insightsError}</p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-2"
                      onClick={() => {
                        setInsights(null);
                        setInsightsError(null);
                      }}
                    >
                      Retry
                    </Button>
                  </div>
                ) : insights ? (
                  <>
                    {/* Risk Summary */}
                    <div>
                      <div className="mb-2 flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-600" />
                        <h4 className="font-semibold">Risk Summary</h4>
                      </div>
                      <p className="text-sm text-muted-foreground">{insights.risk_summary}</p>
                    </div>

                    {/* Root Causes */}
                    <div>
                      <div className="mb-2 flex items-center gap-2">
                        <TrendingDown className="h-4 w-4 text-red-600" />
                        <h4 className="font-semibold">Root Causes</h4>
                      </div>
                      <ul className="space-y-2">
                        {insights.root_causes.map((cause, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm">
                            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-red-500" />
                            <span className="text-muted-foreground">{cause}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Recovery Actions */}
                    <div>
                      <div className="mb-2 flex items-center gap-2">
                        <Lightbulb className="h-4 w-4 text-green-600" />
                        <h4 className="font-semibold">Recovery Actions</h4>
                      </div>
                      <div className="space-y-2">
                        {insights.recovery_actions.map((action, i) => (
                          <div key={i} className="rounded-lg border bg-green-50 p-3">
                            <p className="text-sm font-medium text-green-800">{action.action}</p>
                            <p className="mt-1 text-xs text-green-600">
                              Estimated Impact: {action.estimated_impact}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="py-8 text-center text-sm text-muted-foreground">
                    Loading AI insights...
                  </div>
                )}
              </TabsContent>

              <TabsContent value="analysis" className="mt-4 space-y-6">
                {/* Cause Chain Chart */}
                <div>
                  <h4 className="mb-3 font-semibold">Risk Driver Breakdown</h4>
                  <CauseChainChart data={defaultCauseChain} />
                </div>

                {/* CPI Trend */}
                <div>
                  <h4 className="mb-3 font-semibold">CPI Performance</h4>
                  <CPITrendChart data={[]} currentCPI={project.project_cpi} />
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
