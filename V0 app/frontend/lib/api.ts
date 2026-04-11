const API_BASE = "/api";

export interface UploadResponse {
  success: boolean;
  files: string[];
  session_id: string;
}

export interface AnalysisStatus {
  status: "idle" | "running" | "complete" | "error";
  current_step: number;
  total_steps: number;
  step_name: string;
  error?: string;
  completed_steps: string[];
}

export interface ProjectData {
  project_id: string;
  risk_score_0_100: number;
  risk_category: string;
  project_cpi: number;
  early_rfi_count: number;
  early_ot_ratio_pct: number;
  total_contract_value: number;
  variance_at_completion: number;
  estimate_at_completion: number;
}

export interface CauseChainData {
  project_id: string;
  chain_a_design_rework: number;
  chain_b_material_idle: number;
  chain_c_rfi_standby: number;
  chain_d_rejected_co_loss: number;
  chain_e_early_co_signals: number;
}

export interface OutputFile {
  filename: string;
  rows: number;
}

export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Upload failed");
  }

  return response.json();
}

export async function runAnalysis(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/run-analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Analysis failed to start");
  }
}

export async function getAnalysisStatus(sessionId: string): Promise<AnalysisStatus> {
  const response = await fetch(`${API_BASE}/analysis-status?session_id=${sessionId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch analysis status");
  }
  return response.json();
}

export async function getOutputData<T>(sessionId: string, filename: string): Promise<T[]> {
  const response = await fetch(`${API_BASE}/outputs/${sessionId}/${filename}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${filename}`);
  }
  return response.json();
}

export async function listOutputFiles(sessionId: string): Promise<OutputFile[]> {
  const response = await fetch(`${API_BASE}/outputs/${sessionId}`);
  if (!response.ok) {
    throw new Error("Failed to list output files");
  }
  return response.json();
}

// DuckDB query types - these map to pre-defined queries in the Python backend
export type QueryName = 
  | "portfolio_summary"
  | "risk_distribution" 
  | "top_at_risk_projects"
  | "all_projects"
  | "cpi_analysis"
  | "cause_chain_summary"
  | "cash_flow_overview"
  | "change_order_summary";

export interface DuckDBQueryResponse<T> {
  success: boolean;
  query_name: string;
  data: T[];
  row_count: number;
}

// Execute a pre-defined DuckDB query via the Python backend
export async function executeDuckDBQuery<T>(
  sessionId: string,
  queryName: QueryName
): Promise<T[]> {
  const response = await fetch(`${API_BASE}/query/${sessionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query_name: queryName }),
  });

  if (!response.ok) {
    throw new Error("Query failed");
  }

  const result: DuckDBQueryResponse<T> = await response.json();
  return result.data;
}

// Execute a custom SQL query (for advanced analytics)
export async function executeCustomQuery<T>(
  sessionId: string,
  query: string
): Promise<T[]> {
  const response = await fetch(`${API_BASE}/query/${sessionId}/custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    throw new Error("Query failed");
  }

  const result = await response.json();
  return result.data;
}

// Get available tables in a session
export async function getAvailableTables(sessionId: string) {
  const response = await fetch(`${API_BASE}/query/${sessionId}/tables`);
  if (!response.ok) {
    throw new Error("Failed to get tables");
  }
  return response.json();
}
