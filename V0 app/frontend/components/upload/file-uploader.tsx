"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, Check, X, AlertCircle, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { processFiles, formatBytes, type ProcessedFile } from "@/lib/file-processor";

const REQUIRED_FILES = [
  { name: "contracts_all.csv", description: "Project contracts data" },
  { name: "sov_all.csv", description: "Schedule of values" },
  { name: "sov_budget_all.csv", description: "SOV budget data" },
  { name: "labor_logs_all.csv", description: "Labor time logs" },
  { name: "material_deliveries_all.csv", description: "Material delivery records" },
  { name: "billing_history_all.csv", description: "Billing history" },
  { name: "billing_line_items_all.csv", description: "Billing line items" },
  { name: "change_orders_all.csv", description: "Change order records" },
  { name: "rfis_all.csv", description: "RFI submissions" },
  { name: "field_notes_all.csv", description: "Field notes and logs" },
];

interface FileUploaderProps {
  onUploadComplete: (sessionId: string) => void;
}

type UploadStage = "idle" | "processing" | "uploading";

export function FileUploader({ onUploadComplete }: FileUploaderProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [stage, setStage] = useState<UploadStage>("idle");
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [compressionStats, setCompressionStats] = useState<{
    originalSize: number;
    processedSize: number;
  } | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setError(null);
    setCompressionStats(null);
    setFiles((prev) => {
      const newFiles = [...prev];
      for (const file of acceptedFiles) {
        const existingIndex = newFiles.findIndex((f) => f.name === file.name);
        if (existingIndex >= 0) {
          newFiles[existingIndex] = file;
        } else {
          newFiles.push(file);
        }
      }
      return newFiles;
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
    },
    multiple: true,
  });

  const uploadedFileNames = files.map((f) => f.name);
  const missingFiles = REQUIRED_FILES.filter((rf) => !uploadedFileNames.includes(rf.name));
  const canUpload = missingFiles.length === 0;
  const isProcessing = stage !== "idle";

  const handleUpload = async () => {
    if (!canUpload) return;

    setStage("processing");
    setError(null);
    setProgress(0);
    setCompressionStats(null);

    try {
      // Stage 1: Process files (convert to Parquet, split if needed)
      setStatusMessage("Initializing DuckDB...");
      
      const processedFiles = await processFiles(files, (current, total, fileName, status) => {
        setProgress(Math.round((current / total) * 50)); // 0-50% for processing
        setStatusMessage(`Processing ${fileName}: ${status}`);
      });

      // Calculate compression stats
      const totalOriginal = processedFiles.reduce((sum, f) => sum + f.originalSize, 0);
      const totalProcessed = processedFiles.reduce((sum, f) => sum + f.processedSize, 0);
      setCompressionStats({ originalSize: totalOriginal, processedSize: totalProcessed });

      // Stage 2: Create session and upload
      setStage("uploading");
      setStatusMessage("Creating upload session...");

      const createResponse = await fetch("/api/create-session", {
        method: "POST",
      });

      if (!createResponse.ok) {
        throw new Error("Failed to create upload session");
      }

      const { session_id } = await createResponse.json();

      // Upload all chunks
      const allChunks = processedFiles.flatMap((pf) =>
        pf.chunks.map((chunk) => ({
          ...chunk,
          originalName: pf.originalName,
          format: pf.format,
        }))
      );

      for (let i = 0; i < allChunks.length; i++) {
        const chunk = allChunks[i];
        const uploadProgress = 50 + Math.round((i / allChunks.length) * 50); // 50-100% for uploading
        setProgress(uploadProgress);
        setStatusMessage(
          chunk.totalChunks > 1
            ? `Uploading ${chunk.originalName} (part ${chunk.index + 1}/${chunk.totalChunks})`
            : `Uploading ${chunk.name}`
        );

        const formData = new FormData();
        formData.append("file", chunk.data, chunk.name);
        formData.append("original_name", chunk.originalName);
        formData.append("chunk_index", String(chunk.index));
        formData.append("total_chunks", String(chunk.totalChunks));
        formData.append("format", chunk.format);

        const response = await fetch(`/api/upload/${session_id}`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const contentType = response.headers.get("content-type");
          if (contentType && contentType.includes("application/json")) {
            const data = await response.json();
            throw new Error(data.detail || `Failed to upload ${chunk.name}`);
          } else {
            if (response.status === 413) {
              throw new Error(`Chunk ${chunk.name} is too large - this should not happen`);
            }
            throw new Error(`Failed to upload ${chunk.name}: ${response.statusText}`);
          }
        }
      }

      setProgress(100);
      setStatusMessage("Upload complete!");
      
      // Small delay to show completion
      await new Promise((resolve) => setTimeout(resolve, 500));
      
      onUploadComplete(session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStage("idle");
      setStatusMessage(null);
    }
  };

  const removeFile = (fileName: string) => {
    setFiles((prev) => prev.filter((f) => f.name !== fileName));
  };

  const totalFileSize = files.reduce((sum, f) => sum + f.size, 0);

  return (
    <div className="flex flex-col gap-6">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={cn(
          "relative cursor-pointer rounded-lg border-2 border-dashed p-12 text-center transition-colors",
          isDragActive ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/50",
          isProcessing && "pointer-events-none opacity-50"
        )}
      >
        <input {...getInputProps()} disabled={isProcessing} />
        <div className="flex flex-col items-center gap-4">
          <div className="rounded-full bg-primary/10 p-4">
            <Upload className="h-8 w-8 text-primary" />
          </div>
          <div>
            <p className="text-lg font-medium">
              {isDragActive ? "Drop your CSV files here" : "Drag and drop your CSV files"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              or click to browse. Large files will be automatically compressed.
            </p>
          </div>
        </div>
      </div>

      {/* Processing/Upload Progress */}
      {isProcessing && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  {stage === "processing" && <Zap className="h-4 w-4 text-amber-500" />}
                  {stage === "uploading" && <Upload className="h-4 w-4 text-blue-500" />}
                  <span className="text-muted-foreground">{statusMessage}</span>
                </div>
                <span className="font-medium">{progress}%</span>
              </div>
              <Progress value={progress} className="h-2" />
              {compressionStats && (
                <p className="text-xs text-muted-foreground">
                  Compressed {formatBytes(compressionStats.originalSize)} to{" "}
                  {formatBytes(compressionStats.processedSize)} (
                  {Math.round((1 - compressionStats.processedSize / compressionStats.originalSize) * 100)}% reduction)
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* File Checklist */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Required Files</CardTitle>
          <CardDescription>
            {uploadedFileNames.length} of {REQUIRED_FILES.length} files selected
            {files.length > 0 && ` (${formatBytes(totalFileSize)} total)`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 sm:grid-cols-2">
            {REQUIRED_FILES.map((rf) => {
              const uploadedFile = files.find((f) => f.name === rf.name);
              const isUploaded = !!uploadedFile;
              const isLarge = uploadedFile && uploadedFile.size > 4 * 1024 * 1024;

              return (
                <div
                  key={rf.name}
                  className={cn(
                    "flex items-center gap-3 rounded-md border px-3 py-2",
                    isUploaded ? "border-green-200 bg-green-50" : "border-border"
                  )}
                >
                  {isUploaded ? (
                    <Check className="h-4 w-4 shrink-0 text-green-600" />
                  ) : (
                    <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className={cn("truncate text-sm font-medium", isUploaded && "text-green-700")}>{rf.name}</p>
                    {isUploaded ? (
                      <p className="flex items-center gap-1 text-xs text-green-600">
                        {formatBytes(uploadedFile.size)}
                        {isLarge && (
                          <span className="inline-flex items-center gap-0.5 rounded bg-amber-100 px-1 py-0.5 text-amber-700">
                            <Zap className="h-3 w-3" />
                            will compress
                          </span>
                        )}
                      </p>
                    ) : (
                      <p className="text-xs text-muted-foreground">{rf.description}</p>
                    )}
                  </div>
                  {isUploaded && !isProcessing && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(rf.name);
                      }}
                      className="shrink-0 rounded p-1 hover:bg-green-100"
                    >
                      <X className="h-3 w-3 text-green-600" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Upload Button */}
      <Button onClick={handleUpload} disabled={!canUpload || isProcessing} size="lg" className="w-full">
        {isProcessing ? (
          <>
            <Spinner size="sm" className="text-primary-foreground" />
            {stage === "processing" ? "Compressing files..." : "Uploading..."}
          </>
        ) : canUpload ? (
          <>
            <Upload className="h-4 w-4" />
            Start Analysis
          </>
        ) : (
          <>
            <FileText className="h-4 w-4" />
            {missingFiles.length} file{missingFiles.length !== 1 ? "s" : ""} remaining
          </>
        )}
      </Button>
    </div>
  );
}
