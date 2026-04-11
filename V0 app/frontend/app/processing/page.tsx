"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, ArrowLeft, AlertCircle, CheckCircle } from "lucide-react";
import { StepProgress } from "@/components/processing/step-progress";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { AnalysisStatus } from "@/lib/api";

export default function ProcessingPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<AnalysisStatus>({
    status: "idle",
    current_step: 0,
    total_steps: 9,
    step_name: "",
    completed_steps: [],
  });
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const storedSessionId = sessionStorage.getItem("hvac_session_id");
    if (!storedSessionId) {
      router.push("/");
      return;
    }
    setSessionId(storedSessionId);
  }, [router]);

  // Start analysis when session is ready
  useEffect(() => {
    if (!sessionId || started) return;

    const startAnalysis = async () => {
      try {
        const response = await fetch("/api/run-analysis", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId }),
        });

        if (!response.ok) {
          throw new Error("Failed to start analysis");
        }

        setStarted(true);
      } catch (error) {
        console.error("Failed to start analysis:", error);
        setStatus((prev) => ({
          ...prev,
          status: "error",
          error: "Failed to start analysis pipeline",
        }));
      }
    };

    startAnalysis();
  }, [sessionId, started]);

  // Poll for status updates
  useEffect(() => {
    if (!sessionId || !started) return;

    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/analysis-status?session_id=${sessionId}`);
        if (response.ok) {
          const data = await response.json();
          setStatus(data);

          // Redirect to dashboard when complete
          if (data.status === "complete") {
            setTimeout(() => {
              router.push("/dashboard");
            }, 1500);
          }
        }
      } catch (error) {
        console.error("Failed to fetch status:", error);
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 2000);

    return () => clearInterval(interval);
  }, [sessionId, started, router]);

  const progressPercent = status.total_steps > 0 ? (status.current_step / status.total_steps) * 100 : 0;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <Activity className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">HVAC Margin Early Warning</h1>
              <p className="text-xs text-muted-foreground">Processing Pipeline</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={() => router.push("/")} disabled={status.status === "running"}>
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-4xl px-4 py-8">
        {/* Status Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {status.status === "complete" && <CheckCircle className="h-5 w-5 text-green-600" />}
              {status.status === "error" && <AlertCircle className="h-5 w-5 text-red-600" />}
              {status.status === "running" && <Activity className="h-5 w-5 animate-pulse text-blue-600" />}
              {status.status === "idle" && <Activity className="h-5 w-5 text-muted-foreground" />}
              {status.status === "complete"
                ? "Analysis Complete"
                : status.status === "error"
                  ? "Analysis Failed"
                  : status.status === "running"
                    ? "Running Analysis Pipeline"
                    : "Preparing Analysis"}
            </CardTitle>
            <CardDescription>
              {status.status === "complete"
                ? "All 9 steps completed successfully. Redirecting to dashboard..."
                : status.status === "error"
                  ? status.error || "An error occurred during processing"
                  : status.status === "running"
                    ? `Step ${status.current_step} of ${status.total_steps}: ${status.step_name}`
                    : "Initializing the analysis pipeline..."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Progress</span>
                <span className="tabular-nums">{Math.round(progressPercent)}%</span>
              </div>
              <Progress value={progressPercent} className="h-2" />
            </div>
          </CardContent>
        </Card>

        {/* Step Progress */}
        <StepProgress status={status} />

        {/* Error Actions */}
        {status.status === "error" && (
          <div className="mt-6 flex gap-3">
            <Button variant="outline" onClick={() => router.push("/")}>
              <ArrowLeft className="h-4 w-4" />
              Re-upload Files
            </Button>
            <Button
              onClick={() => {
                setStarted(false);
                setStatus({
                  status: "idle",
                  current_step: 0,
                  total_steps: 9,
                  step_name: "",
                  completed_steps: [],
                });
              }}
            >
              Retry Analysis
            </Button>
          </div>
        )}
      </main>
    </div>
  );
}
