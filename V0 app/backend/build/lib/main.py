import os
import json
import uuid
import subprocess
import shutil
from pathlib import Path
from typing import Optional
import pandas as pd
import fastapi
import fastapi.middleware.cors
from fastapi import UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

app = fastapi.FastAPI()

app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage paths
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

# Pipeline steps
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """Upload CSV files for analysis."""
    session_id = str(uuid.uuid4())
    session_dir = BASE_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_files = []
    for file in files:
        if not file.filename:
            continue
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
        }
    
    # Start analysis in background
    background_tasks.add_task(run_pipeline, session_id, session_dir)
    
    return {"success": True, "message": "Analysis started"}


def run_pipeline(session_id: str, session_dir: Path):
    """Execute the pipeline scripts sequentially."""
    status = analysis_status[session_id]
    status["status"] = "running"
    
    # Create outputs directory
    outputs_dir = session_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    
    for i, step in enumerate(PIPELINE_STEPS):
        status["current_step"] = i + 1
        status["step_name"] = step["name"]
        
        script_path = SCRIPTS_DIR / step["script"]
        
        if not script_path.exists():
            # If script doesn't exist, skip but log it
            status["completed_steps"].append(f"{step['name']} (skipped - script not found)")
            continue
        
        try:
            # Run the script with the session directory as working directory
            result = subprocess.run(
                ["python", str(script_path)],
                cwd=str(session_dir),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per step
                env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR.parent)},
            )
            
            if result.returncode != 0:
                status["status"] = "error"
                status["error"] = f"Step {i + 1} failed: {result.stderr[:500]}"
                return
            
            status["completed_steps"].append(step["name"])
            
        except subprocess.TimeoutExpired:
            status["status"] = "error"
            status["error"] = f"Step {i + 1} ({step['name']}) timed out"
            return
        except Exception as e:
            status["status"] = "error"
            status["error"] = f"Step {i + 1} error: {str(e)}"
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
        }
    return analysis_status[session_id]


@app.get("/outputs/{session_id}")
async def list_outputs(session_id: str):
    """List all output files."""
    outputs_dir = BASE_DIR / session_id / "outputs"
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
    file_path = BASE_DIR / session_id / "outputs" / filename
    
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


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Clean up a session's data."""
    session_dir = BASE_DIR / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)
    if session_id in analysis_status:
        del analysis_status[session_id]
    return {"success": True}
