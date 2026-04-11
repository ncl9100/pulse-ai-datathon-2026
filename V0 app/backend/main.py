import os
import sys
import json
import uuid
import subprocess
import shutil
from pathlib import Path
from typing import Optional
import pandas as pd
import duckdb
import fastapi
import fastapi.middleware.cors
from fastapi import UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = fastapi.FastAPI()

app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage paths
# Your scripts use: BASE = os.path.join(os.path.dirname(__file__), "..")
# So we need to put CSV files in the parent of scripts/, and outputs go to scripts/outputs/
BASE_DIR = Path("/tmp/hvac_analysis")
SCRIPTS_DIR = Path(__file__).parent / "scripts"

# In-memory status tracking
analysis_status: dict[str, dict] = {}

# Required input files
REQUIRED_FILES = [
    "contracts_all.csv",
    "sov_all.csv",
    "sov_budget_all.csv",
    "labor_logs_all.csv",
    "material_deliveries_all.csv",
    "billing_history_all.csv",
    "billing_line_items_all.csv",
    "change_orders_all.csv",
    "rfis_all.csv",
    "field_notes_all.csv",
]

# Pipeline steps - no run_all.py needed, we execute sequentially with status tracking
PIPELINE_STEPS = [
    {"name": "Data Cleaning", "script": "step1_data_cleaning.py"},
    {"name": "Project Master Build", "script": "step2_project_master_table.py"},
    {"name": "Cost Calculation", "script": "step3_actual_cost_per_sov_line.py"},
    {"name": "Billing Progress", "script": "step4_billing_progress.py"},
    {"name": "CPI Metrics", "script": "step5_cost_performance_index.py"},
    {"name": "Change Order Analysis", "script": "step6_change_order_analysis.py"},
    {"name": "Cash Flow Analysis", "script": "step7_cash_flow_analysis.py"},
    {"name": "Cause-Effect Diagnosis", "script": "step8_cause_effect_chains.py"},
    {"name": "Early Warning Scoring", "script": "step9_early_warning_model.py"},
]


def setup_session_directories(session_id: str) -> tuple[Path, Path, Path]:
    """
    Set up directory structure that matches your scripts' path expectations.
    
    Your scripts use:
        BASE = os.path.join(os.path.dirname(__file__), "..")  -> parent of scripts folder
        OUT  = os.path.join(os.path.dirname(__file__), "outputs")  -> scripts/outputs folder
    
    So we create:
        /tmp/hvac_analysis/{session_id}/
        /tmp/hvac_analysis/{session_id}/scripts/  <- symlink to real scripts
        /tmp/hvac_analysis/{session_id}/scripts/outputs/  <- where outputs go
        
    And place uploaded CSVs directly in /tmp/hvac_analysis/{session_id}/ (parent of scripts)
    """
    session_dir = BASE_DIR / session_id
    session_scripts_dir = session_dir / "scripts"
    session_outputs_dir = session_scripts_dir / "outputs"
    
    # Create directories
    session_dir.mkdir(parents=True, exist_ok=True)
    session_scripts_dir.mkdir(exist_ok=True)
    session_outputs_dir.mkdir(exist_ok=True)
    
    # Copy actual script files to session scripts directory
    # This way __file__ resolves to session_scripts_dir and BASE becomes session_dir
    if SCRIPTS_DIR.exists():
        for script_file in SCRIPTS_DIR.glob("*.py"):
            dest = session_scripts_dir / script_file.name
            if not dest.exists():
                shutil.copy(script_file, dest)
    
    return session_dir, session_scripts_dir, session_outputs_dir


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/create-session")
async def create_session():
    """Create a new upload session."""
    session_id = str(uuid.uuid4())
    setup_session_directories(session_id)
    
    # Initialize status
    analysis_status[session_id] = {
        "status": "idle",
        "current_step": 0,
        "total_steps": len(PIPELINE_STEPS),
        "step_name": "",
        "error": None,
        "completed_steps": [],
        "step_logs": {},
        "uploaded_files": [],
    }
    
    return {"session_id": session_id}


@app.post("/upload/{session_id}")
async def upload_single_file(session_id: str, file: UploadFile = File(...)):
    """Upload a single file to an existing session."""
    session_dir = BASE_DIR / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Place file in session_dir
    file_path = session_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)
    
    # Track uploaded files
    if session_id in analysis_status:
        if "uploaded_files" not in analysis_status[session_id]:
            analysis_status[session_id]["uploaded_files"] = []
        if file.filename not in analysis_status[session_id]["uploaded_files"]:
            analysis_status[session_id]["uploaded_files"].append(file.filename)
    
    return {"success": True, "filename": file.filename}


@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """Upload CSV files for analysis (legacy endpoint for small files)."""
    session_id = str(uuid.uuid4())
    session_dir, session_scripts_dir, session_outputs_dir = setup_session_directories(session_id)
    
    uploaded_files = []
    for file in files:
        if not file.filename:
            continue
        # Place CSVs in session_dir (which is the "parent" from scripts' perspective)
        file_path = session_dir / file.filename
        content = await file.read()
        file_path.write_bytes(content)
        uploaded_files.append(file.filename)
    
    # Check for required files
    missing_files = [f for f in REQUIRED_FILES if f not in uploaded_files]
    
    # Initialize status
    analysis_status[session_id] = {
        "status": "idle",
        "current_step": 0,
        "total_steps": len(PIPELINE_STEPS),
        "step_name": "",
        "error": None,
        "completed_steps": [],
        "step_logs": {},
    }
    
    return {
        "success": True,
        "session_id": session_id,
        "files": uploaded_files,
        "missing_files": missing_files,
    }


@app.post("/run-analysis")
async def run_analysis(body: dict, background_tasks: BackgroundTasks):
    """Start the analysis pipeline."""
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    session_dir = BASE_DIR / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session_id not in analysis_status:
        analysis_status[session_id] = {
            "status": "idle",
            "current_step": 0,
            "total_steps": len(PIPELINE_STEPS),
            "step_name": "",
            "error": None,
            "completed_steps": [],
            "step_logs": {},
        }
    
    # Start analysis in background
    background_tasks.add_task(run_pipeline, session_id, session_dir)
    
    return {"success": True, "message": "Analysis started"}


def run_pipeline(session_id: str, session_dir: Path):
    """
    Execute the pipeline scripts sequentially using exec() to run in-process.
    
    This ensures all installed packages (pandas, etc.) are available since
    we're running in the same Python process as FastAPI.
    """
    import io
    from contextlib import redirect_stdout, redirect_stderr
    
    status = analysis_status[session_id]
    status["status"] = "running"
    
    session_scripts_dir = session_dir / "scripts"
    session_outputs_dir = session_scripts_dir / "outputs"
    
    # Ensure outputs directory exists
    session_outputs_dir.mkdir(exist_ok=True)
    
    for i, step in enumerate(PIPELINE_STEPS):
        status["current_step"] = i + 1
        status["step_name"] = step["name"]
        
        script_path = session_scripts_dir / step["script"]
        
        if not script_path.exists():
            # If script doesn't exist in session, try to copy from original location
            original_script = SCRIPTS_DIR / step["script"]
            if original_script.exists():
                shutil.copy(original_script, script_path)
            else:
                status["completed_steps"].append(f"{step['name']} (skipped - script not found)")
                status["step_logs"][step["name"]] = "Script file not found"
                continue
        
        try:
            # Read the script content
            script_content = script_path.read_text()
            
            # Capture stdout/stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            # Create a globals dict for the script execution
            # Set __file__ so the script's path calculations work correctly
            script_globals = {
                "__name__": "__main__",
                "__file__": str(script_path),
                "__builtins__": __builtins__,
            }
            
            # Change to script directory temporarily
            original_cwd = os.getcwd()
            os.chdir(str(session_scripts_dir))
            
            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    exec(compile(script_content, str(script_path), "exec"), script_globals)
                
                # Store logs
                status["step_logs"][step["name"]] = {
                    "stdout": stdout_capture.getvalue()[-2000:],
                    "stderr": stderr_capture.getvalue()[-1000:],
                    "returncode": 0,
                }
                status["completed_steps"].append(step["name"])
                
            except Exception as exec_error:
                status["step_logs"][step["name"]] = {
                    "stdout": stdout_capture.getvalue()[-2000:],
                    "stderr": f"{stderr_capture.getvalue()}\n{str(exec_error)}",
                    "returncode": 1,
                }
                status["status"] = "error"
                status["error"] = f"Step {i + 1} ({step['name']}) failed: {str(exec_error)[:500]}"
                return
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            status["status"] = "error"
            status["error"] = f"Step {i + 1} ({step['name']}) error: {str(e)}"
            return
    
    status["status"] = "complete"


@app.get("/analysis-status")
async def get_analysis_status(session_id: str):
    """Get the current analysis status."""
    if session_id not in analysis_status:
        return {
            "status": "idle",
            "current_step": 0,
            "total_steps": len(PIPELINE_STEPS),
            "step_name": "",
            "error": None,
            "completed_steps": [],
            "step_logs": {},
        }
    return analysis_status[session_id]


@app.get("/outputs/{session_id}")
async def list_outputs(session_id: str):
    """List all output files."""
    # Outputs are in session_dir/scripts/outputs/ per your scripts' path structure
    outputs_dir = BASE_DIR / session_id / "scripts" / "outputs"
    if not outputs_dir.exists():
        return []
    
    files = []
    for f in outputs_dir.glob("*.csv"):
        try:
            df = pd.read_csv(f)
            files.append({"filename": f.name, "rows": len(df)})
        except Exception:
            files.append({"filename": f.name, "rows": 0})
    
    return files


@app.get("/outputs/{session_id}/{filename}")
async def get_output_file(session_id: str, filename: str):
    """Get a specific output file as JSON."""
    file_path = BASE_DIR / session_id / "scripts" / "outputs" / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        df = pd.read_csv(file_path)
        # Replace NaN with None for JSON serialization
        df = df.where(pd.notnull(df), None)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@app.get("/pipeline-steps")
async def get_pipeline_steps():
    """Get the list of pipeline steps."""
    return [{"step": i + 1, "name": step["name"]} for i, step in enumerate(PIPELINE_STEPS)]


@app.get("/step-logs/{session_id}/{step_name}")
async def get_step_logs(session_id: str, step_name: str):
    """Get logs for a specific step."""
    if session_id not in analysis_status:
        raise HTTPException(status_code=404, detail="Session not found")
    
    logs = analysis_status[session_id].get("step_logs", {})
    if step_name not in logs:
        raise HTTPException(status_code=404, detail="Step logs not found")
    
    return logs[step_name]


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Clean up a session's data."""
    session_dir = BASE_DIR / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)
    if session_id in analysis_status:
        del analysis_status[session_id]
    return {"success": True}


# ============================================================================
# DuckDB Query Endpoints
# ============================================================================

class QueryRequest(BaseModel):
    query_name: str
    params: Optional[list] = None


def get_outputs_path(session_id: str) -> Path:
    """Get the outputs directory for a session."""
    return BASE_DIR / session_id / "scripts" / "outputs"


def run_duckdb_query(session_id: str, query: str) -> list[dict]:
    """Execute a DuckDB query against the session's output CSVs."""
    outputs_dir = get_outputs_path(session_id)
    if not outputs_dir.exists():
        return []
    
    conn = duckdb.connect(":memory:")
    
    # Load all output CSVs as tables
    csv_files = {
        "early_warning": "early_warning_scores.csv",
        "cpi": "cpi_per_project.csv",
        "cause_effect": "cause_effect_diagnosis.csv",
        "change_orders": "co_analysis_by_project.csv",
        "cash_flow": "cash_flow_summary.csv",
        "billing": "billing_progress.csv",
        "project_master": "project_master.csv",
    }
    
    for table_name, filename in csv_files.items():
        file_path = outputs_dir / filename
        if file_path.exists():
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{file_path}')")
    
    try:
        result = conn.execute(query).fetchdf()
        # Replace NaN with None for JSON serialization
        result = result.where(pd.notnull(result), None)
        return result.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")
    finally:
        conn.close()


# Pre-defined queries for the dashboard
QUERIES = {
    "portfolio_summary": """
        SELECT 
            COUNT(*) as total_projects,
            COUNT(*) FILTER (WHERE risk_score >= 70) as high_risk_count,
            COUNT(*) FILTER (WHERE risk_score >= 40 AND risk_score < 70) as medium_risk_count,
            COUNT(*) FILTER (WHERE risk_score < 40) as low_risk_count,
            ROUND(AVG(risk_score), 1) as avg_risk_score,
            ROUND(AVG(cpi), 3) as avg_cpi
        FROM early_warning
    """,
    
    "risk_distribution": """
        SELECT 
            CASE 
                WHEN risk_score >= 70 THEN 'High Risk'
                WHEN risk_score >= 40 THEN 'Medium Risk'
                ELSE 'Low Risk'
            END as risk_category,
            COUNT(*) as count,
            ROUND(AVG(risk_score), 1) as avg_score
        FROM early_warning
        GROUP BY risk_category
        ORDER BY avg_score DESC
    """,
    
    "top_at_risk_projects": """
        SELECT 
            project_id,
            project_name,
            risk_score,
            cpi,
            top_risk_factor
        FROM early_warning
        ORDER BY risk_score DESC
        LIMIT 10
    """,
    
    "all_projects": """
        SELECT 
            e.project_id,
            e.project_name,
            e.risk_score,
            e.cpi,
            e.top_risk_factor,
            CASE 
                WHEN e.risk_score >= 70 THEN 'high'
                WHEN e.risk_score >= 40 THEN 'medium'
                ELSE 'low'
            END as risk_level
        FROM early_warning e
        ORDER BY e.risk_score DESC
    """,
    
    "cpi_analysis": """
        SELECT 
            project_id,
            project_name,
            cpi,
            CASE 
                WHEN cpi < 0.9 THEN 'critical'
                WHEN cpi < 1.0 THEN 'warning'
                ELSE 'healthy'
            END as cpi_status,
            budget_variance
        FROM cpi
        ORDER BY cpi ASC
    """,
    
    "cause_chain_summary": """
        SELECT 
            root_cause,
            COUNT(*) as occurrence_count,
            ROUND(AVG(impact_score), 1) as avg_impact
        FROM cause_effect
        GROUP BY root_cause
        ORDER BY occurrence_count DESC
        LIMIT 10
    """,
    
    "cash_flow_overview": """
        SELECT 
            project_id,
            total_billed,
            total_costs,
            net_cash_flow,
            cash_flow_status
        FROM cash_flow
        ORDER BY net_cash_flow ASC
    """,
    
    "change_order_summary": """
        SELECT 
            project_id,
            total_co_value,
            co_count,
            avg_co_value,
            co_impact_rating
        FROM change_orders
        ORDER BY total_co_value DESC
    """,
}


@app.post("/query/{session_id}")
async def execute_query(session_id: str, request: QueryRequest):
    """Execute a pre-defined DuckDB query."""
    outputs_dir = get_outputs_path(session_id)
    if not outputs_dir.exists():
        raise HTTPException(status_code=404, detail="Session outputs not found")
    
    query_name = request.query_name
    if query_name not in QUERIES:
        raise HTTPException(status_code=400, detail=f"Unknown query: {query_name}")
    
    query = QUERIES[query_name]
    data = run_duckdb_query(session_id, query)
    
    return {
        "success": True,
        "query_name": query_name,
        "data": data,
        "row_count": len(data)
    }


@app.post("/query/{session_id}/custom")
async def execute_custom_query(session_id: str, body: dict):
    """Execute a custom SQL query (for advanced users)."""
    outputs_dir = get_outputs_path(session_id)
    if not outputs_dir.exists():
        raise HTTPException(status_code=404, detail="Session outputs not found")
    
    query = body.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    # Basic safety check - only allow SELECT queries
    if not query.strip().upper().startswith("SELECT"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    
    data = run_duckdb_query(session_id, query)
    
    return {
        "success": True,
        "data": data,
        "row_count": len(data)
    }


@app.get("/query/{session_id}/tables")
async def list_available_tables(session_id: str):
    """List available tables and their schemas."""
    outputs_dir = get_outputs_path(session_id)
    if not outputs_dir.exists():
        return {"tables": []}
    
    tables = []
    csv_files = list(outputs_dir.glob("*.csv"))
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, nrows=1)
            tables.append({
                "filename": csv_file.name,
                "table_name": csv_file.stem,
                "columns": list(df.columns),
            })
        except Exception:
            continue
    
    return {"tables": tables}
