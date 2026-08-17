import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain.messages import SystemMessage, ToolMessage, AIMessage

from App.services.rag_service import EmbeddingService
from App.models.hostel_db import db

load_dotenv()

# RAG Policy Retriever Tool
@tool
def hostel_policy_retriever(query: str) -> list:
    """
    Search official DSATM Hostel Policy, Rules, Regulations, Curfew Timings, Mess Menu, Leave Rules,
    and Emergency SOP document.
    """
    svc = EmbeddingService()
    return svc.retrieve_hostel_policy(query)

# DB Tools
@tool
def db_get_student_profile(usn: str) -> dict:
    """Get profile of a student using USN (e.g. 1DS21CS045)."""
    return db.get_student_by_usn(usn) or {"error": "Student not found"}

@tool
def db_get_realtime_occupancy() -> dict:
    """Get live occupancy summary of Block A and Block B hostels."""
    return db.get_dashboard_summary()

@tool
def db_get_safety_anomalies() -> dict:
    """Get list of active overstay alerts, curfew violations, and emergency alerts."""
    return {"anomalies": db.get_safety_alerts(unresolved_only=True)}

@tool
def db_record_checkout(usn: str, destination: str, expected_return_hours: float = 3.0) -> dict:
    """Check out a student from the hostel gate."""
    from datetime import datetime, timedelta
    exp_time = (datetime.now() + timedelta(hours=expected_return_hours)).strftime("%Y-%m-%d %H:%M:%S")
    return db.record_checkout(usn, destination, exp_time)

@tool
def db_record_checkin(usn: str) -> dict:
    """Check in a student at the hostel gate."""
    return db.record_checkin(usn)

@tool
def db_submit_leave(usn: str, reason: str, destination: str, start_date: str, end_date: str) -> dict:
    """Submit a leave or outpass application for a student."""
    return db.submit_leave(usn=usn, reason=reason, destination=destination, start_date=start_date, end_date=end_date)

@tool
def db_trigger_emergency_alert(usn: str, alert_type: str = "EMERGENCY_SOS", message: str = "Immediate assistance required") -> dict:
    """Trigger an emergency safety alert for a student."""
    return {"success": True, "alert": db.create_safety_alert(usn=usn, alert_type=alert_type, severity="CRITICAL", message=message)}

@tool
def db_generate_hostel_report(report_type: str = "daily_summary") -> dict:
    """Generate administrative hostel occupancy and safety report."""
    return db.generate_report(report_type=report_type)

class HostelAssistantAgent:
    def __init__(self, mcp_tools=None):
        api_key = os.getenv("GROQ_API_KEY")
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=1024,
            api_key=api_key
        )

        base_tools = [
            hostel_policy_retriever,
            db_get_student_profile,
            db_get_realtime_occupancy,
            db_get_safety_anomalies,
            db_record_checkout,
            db_record_checkin,
            db_submit_leave,
            db_trigger_emergency_alert,
            db_generate_hostel_report
        ]

        if mcp_tools and len(mcp_tools) > 0:
            tools_dict = {t.name: t for t in base_tools}
            for mt in mcp_tools:
                tools_dict[mt.name] = mt
            self.tools_list = list(tools_dict.values())
        else:
            self.tools_list = base_tools

        self.llm_with_tools = self.llm.bind_tools(self.tools_list)
        self.tools_by_name = {t.name: t for t in self.tools_list}

    def run_llm(self, state: dict) -> dict:
        system_prompt = SystemMessage(content="""
        You are the DSATM Smart Hostel AI Assistant for Dayananda Sagar Academy of Technology and Management, Bangalore.

        Capabilities:
        1. Answer policy & rule questions (curfew, mess timings, outpass rules, emergency SOPs) by retrieving evidence using `hostel_policy_retriever`.
        2. Query live database stats (room occupancy, student status, active overstay anomalies) using `db_get_realtime_occupancy`, `db_get_student_profile`, `db_get_safety_anomalies`, or FastMCP tools.
        3. Execute operational actions like recording gate check-ins and check-outs.

        Guidelines:
        - Ground all policy responses strictly in retrieved document context.
        - Be polite, concise, structured, and helpful.
        """)

        messages = [system_prompt] + state["messages"]
        try:
            response = self.llm_with_tools.invoke(messages)
        except Exception as e:
            # Fallback for expired/invalid API key: direct RAG & DB engine retrieval
            user_text = state["messages"][-1].content if state["messages"] else ""
            svc = EmbeddingService()
            retrieved = svc.retrieve_hostel_policy(user_text, k=2)
            policy_context = "\n\n".join(retrieved) if retrieved else "Curfew is 9:00 PM on weekdays and 9:30 PM on weekends."
            
            summary = db.get_dashboard_summary()
            db_info = f"Current Hostel Stats: Total Residents: {summary['total_students']}, Present: {summary['in_hostel']}, Checked Out: {summary['checked_out']}, On Leave: {summary['on_leave']}, Active Alerts: {summary['active_anomalies_count']}."

            fallback_content = f"**DSATM Hostel Assistant (Rule & Occupancy Engine)**:\n\n{policy_context}\n\n---\n📊 **Live System Data**: {db_info}\n\n*(Note: To enable full conversational LLM features, please update your GROQ_API_KEY in `.env` with a fresh key from https://console.groq.com)*"
            response = AIMessage(content=fallback_content)

        return {
            "messages": [response],
            "llm_calls": state.get("llm_calls", 0) + 1
        }

    async def tool_node(self, state: dict) -> dict:
        result = []
        last_msg = state["messages"][-1]

        for tool_call in getattr(last_msg, "tool_calls", []):
            args = tool_call.get("args", {}).copy()
            if "self" in args:
                del args["self"]

            tool_name = tool_call["name"]
            tool_obj = self.tools_by_name.get(tool_name)

            if tool_obj:
                try:
                    if hasattr(tool_obj, "ainvoke"):
                        obs = await tool_obj.ainvoke(args)
                    else:
                        obs = tool_obj.invoke(args)
                    content_str = str(obs)
                except Exception as e:
                    content_str = f"Error executing tool {tool_name}: {str(e)}"
            else:
                content_str = f"Tool {tool_name} not found."

            result.append(
                ToolMessage(content=content_str, tool_call_id=tool_call["id"])
            )

        return {"messages": result}
