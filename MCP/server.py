from fastmcp import FastMCP
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Ensure root workspace is in python path to import hostel_db
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from App.models.hostel_db import db

load_dotenv()

mcp = FastMCP("DSATM Smart Hostel MCP Server")

@mcp.tool()
def get_student_profile(usn: str) -> dict:
    """
    Look up complete student profile, room allocation, status (IN_HOSTEL, CHECKED_OUT, ON_LEAVE),
    contact details, and guardian phone number using student USN (e.g., '1DS21CS045').
    """
    student = db.get_student_by_usn(usn)
    if not student:
        return {"error": f"No student found with USN {usn}."}
    return student

@mcp.tool()
def get_room_status(room_no: str) -> dict:
    """
    Get detailed information about a specific hostel room (e.g. 'A-101' or 'B-201'),
    including block, capacity, current occupants count, list of student USNs, and status.
    """
    room = db.get_room_by_number(room_no)
    if not room:
        return {"error": f"Room {room_no} not found."}
    return room

@mcp.tool()
def record_checkout(usn: str, destination: str, expected_return_hours: float = 3.0) -> dict:
    """
    Record a student checking out of the hostel gate for outings or local errands.
    Parameters:
    - usn: Student USN (e.g. '1DS21CS045')
    - destination: Destination location (e.g. 'MG Road Market', 'Library')
    - expected_return_hours: Number of hours after which student is expected to return (default: 3.0 hours)
    """
    now = datetime.now()
    exp_time = (now + timedelta(hours=expected_return_hours)).strftime("%Y-%m-%d %H:%M:%S")
    result = db.record_checkout(usn=usn, destination=destination, expected_return_time_str=exp_time)
    return result

@mcp.tool()
def record_checkin(usn: str) -> dict:
    """
    Record a student checking back IN at the hostel gate. Automatically resolves open overstay alerts.
    Parameters:
    - usn: Student USN (e.g. '1DS21CS045')
    """
    result = db.record_checkin(usn=usn)
    return result

@mcp.tool()
def get_realtime_occupancy() -> dict:
    """
    Retrieve real-time occupancy statistics across Block A (Boys) and Block B (Girls),
    including count of students currently in hostel, checked out, on leave, and occupancy percentage.
    """
    summary = db.get_dashboard_summary()
    return summary

@mcp.tool()
def get_safety_anomalies() -> dict:
    """
    Retrieve all active safety anomalies, overdue return alerts, curfew violations, and emergency alerts.
    """
    alerts = db.get_safety_alerts(unresolved_only=True)
    return {
        "active_anomalies_count": len(alerts),
        "anomalies": alerts
    }

@mcp.tool()
def submit_leave_request(usn: str, reason: str, destination: str, start_date: str, end_date: str) -> dict:
    """
    Submit a formal leave application for a student.
    Parameters:
    - usn: Student USN (e.g. '1DS21CS015')
    - reason: Purpose of leave (e.g. 'Family Function', 'Medical Visit')
    - destination: Destination address/city
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    """
    result = db.submit_leave(usn=usn, reason=reason, destination=destination, start_date=start_date, end_date=end_date)
    return result

@mcp.tool()
def trigger_emergency_alert(usn: str, alert_type: str = "EMERGENCY_SOS", message: str = "Immediate Warden Assistance Required") -> dict:
    """
    Trigger an immediate emergency safety alert for a student to notify the Chief Warden.
    Parameters:
    - usn: Student USN
    - alert_type: 'EMERGENCY_SOS', 'CURFEW_BREACH', 'UNAUTHORIZED_ENTRY'
    - message: Descriptive message / reason for alert
    """
    alert = db.create_safety_alert(usn=usn, alert_type=alert_type, severity="CRITICAL", message=message)
    return {"success": True, "alert": alert}

@mcp.tool()
def generate_hostel_report(report_type: str = "daily_summary") -> dict:
    """
    Generate an administrative hostel summary report.
    Parameters:
    - report_type: 'daily_summary', 'occupancy_report', 'anomaly_report'
    """
    summary = db.get_dashboard_summary()
    movements = db.get_movement_logs(limit=10)
    alerts = db.get_safety_alerts(unresolved_only=False)

    report_content = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "report_type": report_type,
        "executive_summary": f"Total Students: {summary['total_students']} | Present: {summary['in_hostel']} | Out: {summary['checked_out']} | On Leave: {summary['on_leave']} | Occupancy Rate: {summary['occupancy_rate']}%",
        "metrics": summary,
        "recent_movements": movements,
        "all_alerts": alerts
    }
    return report_content

if __name__ == "__main__":
    mcp.run(transport="http", port=5678)