"use client";

import { Check, Circle, AlertCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AnalysisStatus } from "@/lib/api";

const PIPELINE_STEPS = [
  { name: "Data Cleaning", description: "Standardizing and validating input data" },
  { name: "Project Master Build", description: "Building unified project records" },
  { name: "Cost Calculation", description: "Computing actual costs per SOV line" },
  { name: "Billing Progress", description: "Analyzing billing completion rates" },
  { name: "CPI Metrics", description: "Calculating cost performance indices" },
  { name: "Change Order Analysis", description: "Evaluating change order patterns" },
  { name: "Cash Flow Analysis", description: "Assessing cash flow health" },
  { name: "Cause-Effect Diagnosis", description: "Identifying risk driver chains" },
  { name: "Early Warning Scoring", description: "Computing final risk scores" },
];

interface StepProgressProps {
  status: AnalysisStatus;
}

export function StepProgress({ status }: StepProgressProps) {
  const getStepStatus = (stepIndex: number) => {
    if (status.status === "error" && status.current_step === stepIndex + 1) {
      return "error";
    }
    if (stepIndex + 1 < status.current_step) {
      return "complete";
    }
    if (stepIndex + 1 === status.current_step && status.status === "running") {
      return "running";
    }
    if (status.status === "complete") {
      return "complete";
    }
    return "pending";
  };

  return (
    <div className="space-y-4">
      {PIPELINE_STEPS.map((step, index) => {
        const stepStatus = getStepStatus(index);

        return (
          <div
            key={step.name}
            className={cn(
              "flex items-start gap-4 rounded-lg border p-4 transition-colors",
              stepStatus === "complete" && "border-green-200 bg-green-50",
              stepStatus === "running" && "border-blue-200 bg-blue-50",
              stepStatus === "error" && "border-red-200 bg-red-50",
              stepStatus === "pending" && "border-border bg-card"
            )}
          >
            {/* Step Number/Icon */}
            <div
              className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-medium",
                stepStatus === "complete" && "bg-green-600 text-white",
                stepStatus === "running" && "bg-blue-600 text-white",
                stepStatus === "error" && "bg-red-600 text-white",
                stepStatus === "pending" && "bg-muted text-muted-foreground"
              )}
            >
              {stepStatus === "complete" && <Check className="h-4 w-4" />}
              {stepStatus === "running" && <Loader2 className="h-4 w-4 animate-spin" />}
              {stepStatus === "error" && <AlertCircle className="h-4 w-4" />}
              {stepStatus === "pending" && <span>{index + 1}</span>}
            </div>

            {/* Step Info */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <h3
                  className={cn(
                    "font-medium",
                    stepStatus === "complete" && "text-green-700",
                    stepStatus === "running" && "text-blue-700",
                    stepStatus === "error" && "text-red-700",
                    stepStatus === "pending" && "text-muted-foreground"
                  )}
                >
                  Step {index + 1}: {step.name}
                </h3>
                {stepStatus === "running" && (
                  <span className="shrink-0 rounded-full bg-blue-600 px-2 py-0.5 text-xs font-medium text-white">
                    Processing
                  </span>
                )}
              </div>
              <p
                className={cn(
                  "mt-0.5 text-sm",
                  stepStatus === "complete" && "text-green-600",
                  stepStatus === "running" && "text-blue-600",
                  stepStatus === "error" && "text-red-600",
                  stepStatus === "pending" && "text-muted-foreground"
                )}
              >
                {step.description}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
