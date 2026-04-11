"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Activity, ArrowLeft, Database } from "lucide-react";
import { SummaryCards } from "@/components/dashboard/summary-cards";
import { RiskDistributionChart } from "@/components/dashboard/risk-distribution-chart";
import { ProjectTable, type ProjectRow } from "@/components/dashboard/project-table";
import { ProjectDetailPanel } from "@/components/dashboard/project-detail-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Badge } from "@/components/ui/badge";
import { executeDuckDBQuery } from "@/lib/api";

// Demo data for when pipeline outputs aren't available
const DEMO_DATA: ProjectRow[] = [
  { project_id: "HVAC-2024-001", risk_score_0_100: 85, risk_category: "High Risk", project_cpi: 0.72, early_rfi_count: 14, early_ot_ratio_pct: 28.5, total_contract_value: 2450000, variance_at_completion: -245000 },
  { project_id: "HVAC-2024-002", risk_score_0_100: 72, risk_category: "Elevated", project_cpi: 0.85, early_rfi_count: 9, early_ot_ratio_pct: 22.0, total_contract_value: 1850000, variance_at_completion: -148000 },
  { project_id: "HVAC-2024-003", risk_score_0_100: 45, risk_category: "Moderate", project_cpi: 0.95, early_rfi_count: 5, early_ot_ratio_pct: 12.5, total_contract_value: 980000, variance_at_completion: -49000 },
  { project_id: "HVAC-2024-004", risk_score_0_100: 22, risk_category: "Low Risk", project_cpi: 1.05, early_rfi_count: 2, early_ot_ratio_pct: 8.0, total_contract_value: 1200000, variance_at_completion: 60000 },
  { project_id: "HVAC-2024-005", risk_score_0_100: 88, risk_category: "High Risk", project_cpi: 0.68, early_rfi_count: 18, early_ot_ratio_pct: 35.0, total_contract_value: 3200000, variance_at_completion: -512000 },
  { project_id: "HVAC-2024-006", risk_score_0_100: 62, risk_category: "Elevated", project_cpi: 0.88, early_rfi_count: 7, early_ot_ratio_pct: 18.5, total_contract_value: 1450000, variance_at_completion: -116000 },
  { project_id: "HVAC-2024-007", risk_score_0_100: 35, risk_category: "Moderate", project_cpi: 0.98, early_rfi_count: 4, early_ot_ratio_pct: 10.0, total_contract_value: 890000, variance_at_completion: -17800 },
  { project_id: "HVAC-2024-008", risk_score_0_100: 18, risk_category: "Low Risk", project_cpi: 1.08, early_rfi_count: 1, early_ot_ratio_pct: 5.5, total_contract_value: 750000, variance_at_completion: 60000 },
  { project_id: "HVAC-2024-009", risk_score_0_100: 78, risk_category: "High Risk", project_cpi: 0.75, early_rfi_count: 12, early_ot_ratio_pct: 25.0, total_contract_value: 2100000, variance_at_completion: -315000 },
  { project_id: "HVAC-2024-010", risk_score_0_100: 55, risk_category: "Moderate", project_cpi: 0.92, early_rfi_count: 6, early_ot_ratio_pct: 15.0, total_contract_value: 1100000, variance_at_completion: -88000 },
];

interface PortfolioSummary {
  total_projects: number;
  high_risk_count: number;
  elevated_count: number;
  healthy_count: number;
  avg_cpi: number;
  avg_risk_score: number;
  total_at_risk: number;
  total_portfolio_value: number;
}

interface RiskDistributionRow {
  risk_category: string;
  count: number;
  avg_score: number;
  total_value: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummary | null>(null);
  const [riskDistribution, setRiskDistribution] = useState<RiskDistributionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProject, setSelectedProject] = useState<ProjectRow | null>(null);
  const [usingDemoData, setUsingDemoData] = useState(false);
  const [queryEngine, setQueryEngine] = useState<"duckdb" | "fallback">("fallback");

  useEffect(() => {
    const storedSessionId = sessionStorage.getItem("hvac_session_id");
    setSessionId(storedSessionId);

    const loadData = async () => {
      if (storedSessionId) {
        try {
          // Load data using DuckDB queries from Python backend
          const [projectsData, summaryData, riskData] = await Promise.all([
            executeDuckDBQuery<ProjectRow>(storedSessionId, "all_projects"),
            executeDuckDBQuery<PortfolioSummary>(storedSessionId, "portfolio_summary"),
            executeDuckDBQuery<RiskDistributionRow>(storedSessionId, "risk_distribution"),
          ]);

          if (projectsData.length > 0) {
            setProjects(projectsData);
            setPortfolioSummary(summaryData[0] || null);
            setRiskDistribution(riskData);
            setUsingDemoData(false);
            setQueryEngine("duckdb");
          } else {
            throw new Error("No data returned");
          }
        } catch (error) {
          console.error("DuckDB query failed, using demo data:", error);
          // Fall back to demo data
          setProjects(DEMO_DATA);
          setUsingDemoData(true);
          setQueryEngine("fallback");
        }
      } else {
        // No session, use demo data
        setProjects(DEMO_DATA);
        setUsingDemoData(true);
        setQueryEngine("fallback");
      }
      setLoading(false);
    };

    loadData();
  }, []);

  // Calculate summary statistics from demo data if not using DuckDB
  const summaryData = useMemo(() => {
    if (portfolioSummary) {
      return {
        total: portfolioSummary.total_projects,
        highRisk: portfolioSummary.high_risk_count,
        elevated: portfolioSummary.elevated_count,
        healthy: portfolioSummary.healthy_count,
        avgCpi: portfolioSummary.avg_cpi,
        avgRiskScore: portfolioSummary.avg_risk_score,
        totalAtRisk: portfolioSummary.total_at_risk,
        totalPortfolioValue: portfolioSummary.total_portfolio_value,
      };
    }

    // Calculate from projects array (demo mode)
    const total = projects.length;
    const highRisk = projects.filter((p) => p.risk_category === "High Risk").length;
    const elevated = projects.filter((p) => p.risk_category === "Elevated").length;
    const healthy = projects.filter((p) => p.risk_category === "Low Risk" || p.risk_category === "Moderate").length;
    const avgCpi = projects.reduce((sum, p) => sum + p.project_cpi, 0) / projects.length;
    const avgRiskScore = projects.reduce((sum, p) => sum + p.risk_score_0_100, 0) / projects.length;
    const totalAtRisk = projects
      .filter(p => p.variance_at_completion && p.variance_at_completion < 0)
      .reduce((sum, p) => sum + Math.abs(p.variance_at_completion || 0), 0);

    return { total, highRisk, elevated, healthy, avgCpi, avgRiskScore, totalAtRisk };
  }, [projects, portfolioSummary]);

  // Calculate risk distribution for chart (from DuckDB or demo data)
  const chartData = useMemo(() => {
    if (riskDistribution.length > 0) {
      const colorMap: Record<string, string> = {
        "High Risk": "#dc2626",
        "Elevated": "#f59e0b",
        "Moderate": "#3b82f6",
        "Low Risk": "#22c55e",
      };

      return riskDistribution.map((r) => ({
        name: r.risk_category,
        count: Number(r.count),
        color: colorMap[r.risk_category] || "#6b7280",
      }));
    }

    // Calculate from projects (demo mode)
    const categories = [
      { name: "High Risk", count: 0, color: "#dc2626" },
      { name: "Elevated", count: 0, color: "#f59e0b" },
      { name: "Moderate", count: 0, color: "#3b82f6" },
      { name: "Low Risk", count: 0, color: "#22c55e" },
    ];

    projects.forEach((p) => {
      const cat = categories.find((c) => c.name === p.risk_category);
      if (cat) cat.count++;
    });

    return categories.filter((c) => c.count > 0);
  }, [projects, riskDistribution]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <Spinner size="lg" />
          <p className="mt-4 text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b bg-card">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <Activity className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">HVAC Margin Early Warning</h1>
              <p className="text-xs text-muted-foreground">Dashboard</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {queryEngine === "duckdb" && (
              <Badge variant="outline" className="gap-1">
                <Database className="h-3 w-3" />
                DuckDB
              </Badge>
            )}
            <Button variant="outline" size="sm" onClick={() => router.push("/")}>
              <ArrowLeft className="h-4 w-4" />
              New Analysis
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-6">
        {/* Demo Data Banner */}
        {usingDemoData && (
          <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-sm text-amber-800">
              <strong>Demo Mode:</strong> Displaying sample project data. Upload your CSV files to see your actual project portfolio.
            </p>
          </div>
        )}

        {/* Summary Cards */}
        <div className="mb-6">
          <SummaryCards data={summaryData} />
        </div>

        {/* Charts Row */}
        <div className="mb-6 grid gap-6 lg:grid-cols-2">
          <RiskDistributionChart data={chartData} />
          
          <Card>
            <CardHeader>
              <CardTitle>Portfolio Health</CardTitle>
              <CardDescription>Overall risk assessment</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-lg border p-4">
                  <p className="text-sm text-muted-foreground">Average CPI</p>
                  <p className="text-2xl font-bold tabular-nums">
                    {(summaryData.avgCpi || 0).toFixed(2)}
                  </p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-sm text-muted-foreground">Avg Risk Score</p>
                  <p className="text-2xl font-bold tabular-nums">
                    {(summaryData.avgRiskScore || 0).toFixed(0)}
                  </p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-sm text-muted-foreground">Total at Risk</p>
                  <p className="text-2xl font-bold tabular-nums text-red-600">
                    ${((summaryData.totalAtRisk || 0) / 1000000).toFixed(1)}M
                  </p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-sm text-muted-foreground">High Risk Projects</p>
                  <p className="text-2xl font-bold tabular-nums">
                    {summaryData.total > 0 ? ((summaryData.highRisk / summaryData.total) * 100).toFixed(0) : 0}%
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Project Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Project Risk Analysis</CardTitle>
                <CardDescription>Click a row to view detailed insights and recovery recommendations</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ProjectTable data={projects} onRowClick={setSelectedProject} />
          </CardContent>
        </Card>
      </main>

      {/* Project Detail Panel */}
      <ProjectDetailPanel
        project={selectedProject}
        onClose={() => setSelectedProject(null)}
        sessionId={sessionId || ""}
      />
    </div>
  );
}
