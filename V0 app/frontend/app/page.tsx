"use client";

import { useRouter } from "next/navigation";
import { FileUploader } from "@/components/upload/file-uploader";
import { Activity, BarChart3, ShieldAlert } from "lucide-react";

export default function UploadPage() {
  const router = useRouter();

  const handleUploadComplete = (sessionId: string) => {
    // Store session ID and redirect to processing
    sessionStorage.setItem("hvac_session_id", sessionId);
    router.push("/processing");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <Activity className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">HVAC Margin Early Warning</h1>
              <p className="text-xs text-muted-foreground">AI-Powered Risk Detection</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-5xl px-4 py-12">
        <div className="mb-10 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-balance">Analyze Your HVAC Project Portfolio</h2>
          <p className="mt-3 text-lg text-muted-foreground text-pretty">
            Upload your project data files to identify margin risks, detect early warning signs, and get AI-powered
            recovery recommendations.
          </p>
        </div>

        {/* Features Grid */}
        <div className="mb-10 grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border bg-card p-5">
            <div className="mb-3 inline-flex rounded-md bg-red-100 p-2">
              <ShieldAlert className="h-5 w-5 text-red-600" />
            </div>
            <h3 className="font-semibold">Early Warning Detection</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Identify at-risk projects before margin erosion becomes critical
            </p>
          </div>
          <div className="rounded-lg border bg-card p-5">
            <div className="mb-3 inline-flex rounded-md bg-blue-100 p-2">
              <BarChart3 className="h-5 w-5 text-blue-600" />
            </div>
            <h3 className="font-semibold">CPI & Performance Metrics</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Track cost performance index and variance at completion
            </p>
          </div>
          <div className="rounded-lg border bg-card p-5">
            <div className="mb-3 inline-flex rounded-md bg-green-100 p-2">
              <Activity className="h-5 w-5 text-green-600" />
            </div>
            <h3 className="font-semibold">AI Recovery Actions</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Get dollar-quantified recommendations to recover margin
            </p>
          </div>
        </div>

        {/* File Uploader */}
        <FileUploader onUploadComplete={handleUploadComplete} />

        {/* Demo Note */}
        <div className="mt-8 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm text-amber-800">
            <strong>Demo Mode:</strong> For testing, you can use sample CSV files with the correct column headers. The
            analysis pipeline will process your data through 9 analytical steps including data cleaning, CPI
            calculation, change order analysis, and early warning scoring.
          </p>
        </div>
      </main>
    </div>
  );
}
