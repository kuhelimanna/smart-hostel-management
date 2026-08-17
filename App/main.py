import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

# Ensure project root is in import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from App.models.hostel_db import db
from App.workflows.hostel_workflow import HostelWorkflow
from App.services.rag_service import EmbeddingService

from mcp.client.streamable_http import streamable_http_client
from mcp.client.session import ClientSession
from langchain_mcp_adapters.tools import convert_mcp_tool_to_langchain_tool

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize RAG retriever
    try:
        rag_svc = EmbeddingService()
        rag_svc.process_hostel_policy_document()
        print("RAG Hostel Knowledge Base initialized successfully.")
    except Exception as e:
        print(f"RAG Init warning: {e}")

    # Connect to MCP Tool Server if available (with timeout)
    mcp_base_url = "http://127.0.0.1:5678/mcp"
    app.state.mcp_tools = []
    app.state.mcp_session = None

    try:
        import httpx
        # Quick ping check before initializing streamable_http_client
        async with httpx.AsyncClient(timeout=1.0) as client:
            resp = await client.get("http://127.0.0.1:5678/mcp")
            if resp.status_code == 200:
                transport_cm = streamable_http_client(mcp_base_url)
                read_stream, write_stream, _ = await transport_cm.__aenter__()
                session_cm = ClientSession(read_stream, write_stream)
                session = await session_cm.__aenter__()
                await session.initialize()
                app.state.mcp_session = session
                response = await session.list_tools()
                raw_tools = response.tools if hasattr(response, "tools") else []
                app.state.mcp_tools = [convert_mcp_tool_to_langchain_tool(session, tool) for tool in raw_tools]
                print(f"Successfully loaded {len(app.state.mcp_tools)} tools from FastMCP Server.")
    except Exception as e:
        print("MCP Server note: FastMCP server not detected on port 5678 (Using built-in DB tools).")

    yield

app = FastAPI(
    title="DSATM Smart Hostel Management & Real-Time Occupancy API",
    version="1.0.0",
    lifespan=lifespan
)

# ----------------- Request Models -----------------
class CheckOutRequest(BaseModel):
    usn: str
    destination: str
    expected_return_hours: Optional[float] = 3.0

class CheckInRequest(BaseModel):
    usn: str

class LeaveSubmissionRequest(BaseModel):
    usn: str
    reason: str
    destination: str
    start_date: str
    end_date: str

class LeaveStatusUpdate(BaseModel):
    status: str

class EmergencyAlertRequest(BaseModel):
    usn: str
    alert_type: str = "EMERGENCY_SOS"
    severity: str = "CRITICAL"
    message: str

class AIChatRequest(BaseModel):
    query: str

class AddStudentRequest(BaseModel):
    usn: str
    name: str
    dept: str
    year: str
    phone: str
    guardian_phone: str
    room_no: str
    block: str

# ----------------- REST API Endpoints -----------------

@app.get("/api/health")
def health_check():
    mcp_tools = getattr(app.state, "mcp_tools", [])
    return {"status": "online", "service": "DSATM Hostel Management API", "mcp_connected": len(mcp_tools) > 0}

@app.get("/api/summary")
def get_summary():
    return db.get_dashboard_summary()

@app.get("/api/students")
def get_students(block: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None):
    return db.get_all_students(block=block, status=status, search=search)

@app.get("/api/students/{usn}")
def get_student(usn: str):
    s = db.get_student_by_usn(usn)
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    return s

@app.post("/api/students")
def add_student(req: AddStudentRequest):
    new_s = db.add_student(req.dict())
    return {"success": True, "student": new_s}

@app.get("/api/rooms")
def get_rooms(block: Optional[str] = None):
    return db.get_all_rooms(block=block)

@app.post("/api/movements/checkout")
def checkout_student(req: CheckOutRequest):
    from datetime import datetime, timedelta
    hrs = req.expected_return_hours or 3.0
    exp_time = (datetime.now() + timedelta(hours=hrs)).strftime("%Y-%m-%d %H:%M:%S")
    res = db.record_checkout(req.usn, req.destination, exp_time)
    return res

@app.post("/api/movements/checkin")
def checkin_student(req: CheckInRequest):
    res = db.record_checkin(req.usn)
    return res

@app.get("/api/movements/logs")
def get_movement_logs(limit: int = 30):
    return db.get_movement_logs(limit=limit)

@app.get("/api/leaves")
def get_leaves():
    return db.get_all_leaves()

@app.post("/api/leaves")
def submit_leave(req: LeaveSubmissionRequest):
    return db.submit_leave(
        usn=req.usn,
        reason=req.reason,
        destination=req.destination,
        start_date=req.start_date,
        end_date=req.end_date
    )

@app.put("/api/leaves/{leave_id}/status")
def update_leave(leave_id: str, req: LeaveStatusUpdate):
    return db.update_leave_status(leave_id, req.status)

@app.get("/api/alerts")
def get_alerts(unresolved_only: bool = False):
    return db.get_safety_alerts(unresolved_only=unresolved_only)

@app.post("/api/alerts")
def create_alert(req: EmergencyAlertRequest):
    alert = db.create_safety_alert(usn=req.usn, alert_type=req.alert_type, severity=req.severity, message=req.message)
    return {"success": True, "alert": alert}

@app.put("/api/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str):
    return db.resolve_alert(alert_id)

@app.get("/api/reports/generate")
@app.post("/api/reports/generate")
def generate_report(report_type: str = "daily_summary"):
    return db.generate_report(report_type=report_type)

@app.get("/api/mcp/tools")
def get_mcp_tools():
    mcp_tools = getattr(app.state, "mcp_tools", [])
    return {"tools": [t.name for t in mcp_tools]}

@app.post("/api/ai/chat")
async def ai_chat(req: AIChatRequest):
    try:
        mcp_tools = getattr(app.state, "mcp_tools", [])
        workflow = HostelWorkflow(mcp_tools=mcp_tools)
        res = await workflow.run_hostel_workflow(req.query)
        messages = res.get("messages", [])
        final_answer = messages[-1].content if messages else "No response generated."

        tools_executed = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tools_executed.append(tc.get("name"))

        return {
            "success": True,
            "response": final_answer,
            "tools_used": list(set(tools_executed))
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response": f"Error processing query: {str(e)}"
        }

# Mount static frontend directory
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "DSATM Hostel Management API Server is running."}