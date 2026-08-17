"""
DSATM Smart Hostel Database Model & In-Memory / SQLite Storage Engine.
Manages Student Records, Room Allocations, Check-in/Out Gate Movements,
Leave Requests, and Real-Time Safety Anomaly Alerts.
"""

from datetime import datetime, timedelta
import threading
import uuid

class HostelDatabase:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(HostelDatabase, cls).__new__(cls)
                cls._instance._initialize_db()
            return cls._instance

    def _initialize_db(self):
        self.students = {}
        self.rooms = {}
        self.movements = []
        self.leaves = []
        self.alerts = []

        self._seed_data()

    def _seed_data(self):
        # 1. Seed Rooms (Block A - Boys, Block B - Girls)
        # Block A Rooms (Floors 1-3, 10 rooms per floor)
        for floor in range(1, 4):
            for r in range(1, 7):
                room_no = f"A-{floor}0{r}"
                self.rooms[room_no] = {
                    "room_no": room_no,
                    "block": "Block A - Boys",
                    "floor": floor,
                    "capacity": 2,
                    "occupied_count": 0,
                    "status": "VACANT",
                    "occupants": []
                }
        
        # Block B Rooms (Floors 1-3, 10 rooms per floor)
        for floor in range(1, 4):
            for r in range(1, 7):
                room_no = f"B-{floor}0{r}"
                self.rooms[room_no] = {
                    "room_no": room_no,
                    "block": "Block B - Girls",
                    "floor": floor,
                    "capacity": 2,
                    "occupied_count": 0,
                    "status": "VACANT",
                    "occupants": []
                }

        # 2. Seed Students
        sample_students = [
            # Block A Students
            {"usn": "1DS21CS045", "name": "Rahul Sharma", "dept": "CSE", "year": "3rd Year", "phone": "+91 98765 11001", "guardian_phone": "+91 98765 99001", "room_no": "A-101", "block": "Block A - Boys"},
            {"usn": "1DS21CS088", "name": "Aditya Verma", "dept": "CSE", "year": "3rd Year", "phone": "+91 98765 11002", "guardian_phone": "+91 98765 99002", "room_no": "A-101", "block": "Block A - Boys"},
            {"usn": "1DS22IS012", "name": "Karthik Gowda", "dept": "ISE", "year": "2nd Year", "phone": "+91 98765 11003", "guardian_phone": "+91 98765 99003", "room_no": "A-102", "block": "Block A - Boys"},
            {"usn": "1DS22EC034", "name": "Siddharth Rao", "dept": "ECE", "year": "2nd Year", "phone": "+91 98765 11004", "guardian_phone": "+91 98765 99004", "room_no": "A-102", "block": "Block A - Boys"},
            {"usn": "1DS23ME005", "name": "Vikas Hegde", "dept": "ME", "year": "1st Year", "phone": "+91 98765 11005", "guardian_phone": "+91 98765 99005", "room_no": "A-201", "block": "Block A - Boys"},
            {"usn": "1DS21AI019", "name": "Rohan Deshmukh", "dept": "AIML", "year": "3rd Year", "phone": "+91 98765 11006", "guardian_phone": "+91 98765 99006", "room_no": "A-202", "block": "Block A - Boys"},
            {"usn": "1DS21CS102", "name": "Manish Kumar", "dept": "CSE", "year": "3rd Year", "phone": "+91 98765 11007", "guardian_phone": "+91 98765 99007", "room_no": "A-301", "block": "Block A - Boys"},

            # Block B Students
            {"usn": "1DS21CS015", "name": "Ananya Kulkarni", "dept": "CSE", "year": "3rd Year", "phone": "+91 98765 22001", "guardian_phone": "+91 98765 88001", "room_no": "B-101", "block": "Block B - Girls"},
            {"usn": "1DS21IS042", "name": "Priya Nair", "dept": "ISE", "year": "3rd Year", "phone": "+91 98765 22002", "guardian_phone": "+91 98765 88002", "room_no": "B-101", "block": "Block B - Girls"},
            {"usn": "1DS22EC018", "name": "Sneha Patil", "dept": "ECE", "year": "2nd Year", "phone": "+91 98765 22003", "guardian_phone": "+91 98765 88003", "room_no": "B-102", "block": "Block B - Girls"},
            {"usn": "1DS22AI031", "name": "Meera Reddy", "dept": "AIML", "year": "2nd Year", "phone": "+91 98765 22004", "guardian_phone": "+91 98765 88004", "room_no": "B-201", "block": "Block B - Girls"},
            {"usn": "1DS23CS009", "name": "Pooja Sundaram", "dept": "CSE", "year": "1st Year", "phone": "+91 98765 22005", "guardian_phone": "+91 98765 88005", "room_no": "B-202", "block": "Block B - Girls"},
            {"usn": "1DS21CS150", "name": "Divya Bhat", "dept": "CSE", "year": "3rd Year", "phone": "+91 98765 22006", "guardian_phone": "+91 98765 88006", "room_no": "B-301", "block": "Block B - Girls"},
        ]

        now = datetime.now()

        for s in sample_students:
            usn = s["usn"]
            # Default status is IN_HOSTEL
            status = "IN_HOSTEL"
            qr_code = f"DSATM-HOSTEL-{usn}"
            
            # Put one student as CHECKED_OUT with overstay for demo
            if usn == "1DS21CS045":
                status = "CHECKED_OUT"
            elif usn == "1DS21CS015":
                status = "ON_LEAVE"

            student_obj = {
                "usn": usn,
                "name": s["name"],
                "dept": s["dept"],
                "year": s["year"],
                "phone": s["phone"],
                "guardian_phone": s["guardian_phone"],
                "room_no": s["room_no"],
                "block": s["block"],
                "status": status,
                "qr_code": qr_code,
                "created_at": now.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.students[usn] = student_obj

            # Assign to room
            r_no = s["room_no"]
            if r_no in self.rooms:
                self.rooms[r_no]["occupants"].append(usn)
                self.rooms[r_no]["occupied_count"] = len(self.rooms[r_no]["occupants"])
                if self.rooms[r_no]["occupied_count"] >= self.rooms[r_no]["capacity"]:
                    self.rooms[r_no]["status"] = "FULL"
                else:
                    self.rooms[r_no]["status"] = "PARTIALLY_OCCUPIED"

        # 3. Seed Sample Movements
        past_2_hrs = (now - timedelta(hours=2.5)).strftime("%Y-%m-%d %H:%M:%S")
        past_1_hr = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        exp_return_overdue = (now - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")

        self.movements = [
            {
                "log_id": "LOG-1001",
                "usn": "1DS21CS045",
                "student_name": "Rahul Sharma",
                "block": "Block A - Boys",
                "room_no": "A-101",
                "direction": "OUT",
                "timestamp": past_2_hrs,
                "destination": "Jayanagar Shopping",
                "expected_return_time": exp_return_overdue,
                "actual_return_time": None,
                "status": "OVERSTAY_ANOMALY"
            },
            {
                "log_id": "LOG-1002",
                "usn": "1DS22IS012",
                "student_name": "Karthik Gowda",
                "block": "Block A - Boys",
                "room_no": "A-102",
                "direction": "OUT",
                "timestamp": past_1_hr,
                "destination": "Library",
                "expected_return_time": (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "actual_return_time": None,
                "status": "NORMAL"
            },
            {
                "log_id": "LOG-1003",
                "usn": "1DS21CS088",
                "student_name": "Aditya Verma",
                "block": "Block A - Boys",
                "room_no": "A-101",
                "direction": "IN",
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "destination": "Hostel Gate",
                "expected_return_time": None,
                "actual_return_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "NORMAL"
            }
        ]

        # 4. Seed Sample Leaves
        self.leaves = [
            {
                "leave_id": "LV-501",
                "usn": "1DS21CS015",
                "student_name": "Ananya Kulkarni",
                "room_no": "B-101",
                "block": "Block B - Girls",
                "reason": "Family Function at Mysore",
                "destination": "Mysore, Karnataka",
                "start_date": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
                "end_date": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
                "parent_contacted": True,
                "status": "APPROVED",
                "applied_at": (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "leave_id": "LV-502",
                "usn": "1DS22EC018",
                "student_name": "Sneha Patil",
                "room_no": "B-102",
                "block": "Block B - Girls",
                "reason": "Medical Checkup",
                "destination": "Apollo Hospital, Bangalore",
                "start_date": now.strftime("%Y-%m-%d"),
                "end_date": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
                "parent_contacted": True,
                "status": "PENDING",
                "applied_at": now.strftime("%Y-%m-%d %H:%M:%S")
            }
        ]

        # 5. Seed Safety Alerts
        self.alerts = [
            {
                "alert_id": "ALT-901",
                "usn": "1DS21CS045",
                "student_name": "Rahul Sharma",
                "room_no": "A-101",
                "block": "Block A - Boys",
                "alert_type": "OVERSTAY_ANOMALY",
                "severity": "HIGH",
                "message": "Student Rahul Sharma (1DS21CS045) is 30 mins overdue from expected return time Jayanagar Shopping.",
                "created_at": exp_return_overdue,
                "resolved": False
            }
        ]

    # --- Student Operations ---
    def get_all_students(self, block=None, status=None, search=None):
        res = list(self.students.values())
        if block:
            res = [s for s in res if block.lower() in s["block"].lower()]
        if status:
            res = [s for s in res if s["status"].upper() == status.upper()]
        if search:
            q = search.lower()
            res = [s for s in res if q in s["name"].lower() or q in s["usn"].lower() or q in s["room_no"].lower()]
        return res

    def get_student_by_usn(self, usn):
        return self.students.get(usn.upper())

    def add_student(self, student_dict):
        usn = student_dict["usn"].upper()
        student_dict["usn"] = usn
        student_dict["qr_code"] = f"DSATM-HOSTEL-{usn}"
        student_dict["status"] = student_dict.get("status", "IN_HOSTEL")
        student_dict["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.students[usn] = student_dict

        # Add to room if allocated
        room_no = student_dict.get("room_no")
        if room_no and room_no in self.rooms:
            if usn not in self.rooms[room_no]["occupants"]:
                self.rooms[room_no]["occupants"].append(usn)
                self.rooms[room_no]["occupied_count"] = len(self.rooms[room_no]["occupants"])
                if self.rooms[room_no]["occupied_count"] >= self.rooms[room_no]["capacity"]:
                    self.rooms[room_no]["status"] = "FULL"
                else:
                    self.rooms[room_no]["status"] = "PARTIALLY_OCCUPIED"

        return student_dict

    # --- Room Operations ---
    def get_all_rooms(self, block=None):
        res = list(self.rooms.values())
        if block:
            res = [r for r in res if block.lower() in r["block"].lower()]
        return res

    def get_room_by_number(self, room_no):
        return self.rooms.get(room_no)

    # --- Movement & Gate Terminal Operations ---
    def record_checkout(self, usn, destination, expected_return_time_str):
        usn = usn.upper()
        student = self.get_student_by_usn(usn)
        if not student:
            return {"success": False, "message": f"Student with USN {usn} not found."}

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_id = f"LOG-{uuid.uuid4().hex[:6].upper()}"

        movement = {
            "log_id": log_id,
            "usn": usn,
            "student_name": student["name"],
            "block": student["block"],
            "room_no": student["room_no"],
            "direction": "OUT",
            "timestamp": now_str,
            "destination": destination,
            "expected_return_time": expected_return_time_str,
            "actual_return_time": None,
            "status": "NORMAL"
        }

        student["status"] = "CHECKED_OUT"
        self.movements.insert(0, movement)
        return {"success": True, "message": f"Student {student['name']} ({usn}) checked OUT successfully.", "movement": movement}

    def record_checkin(self, usn):
        usn = usn.upper()
        student = self.get_student_by_usn(usn)
        if not student:
            return {"success": False, "message": f"Student with USN {usn} not found."}

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_id = f"LOG-{uuid.uuid4().hex[:6].upper()}"

        # Resolve open overstay alerts if any
        for alt in self.alerts:
            if alt["usn"] == usn and not alt["resolved"]:
                alt["resolved"] = True
                alt["message"] += f" [RESOLVED at {now_str}]"

        movement = {
            "log_id": log_id,
            "usn": usn,
            "student_name": student["name"],
            "block": student["block"],
            "room_no": student["room_no"],
            "direction": "IN",
            "timestamp": now_str,
            "destination": "Hostel Gate",
            "expected_return_time": None,
            "actual_return_time": now_str,
            "status": "NORMAL"
        }

        student["status"] = "IN_HOSTEL"
        self.movements.insert(0, movement)
        return {"success": True, "message": f"Student {student['name']} ({usn}) checked IN successfully.", "movement": movement}

    def get_movement_logs(self, limit=20):
        return self.movements[:limit]

    # --- Leave Operations ---
    def submit_leave(self, usn, reason, destination, start_date, end_date, parent_contacted=True):
        usn = usn.upper()
        student = self.get_student_by_usn(usn)
        if not student:
            return {"success": False, "message": f"Student with USN {usn} not found."}

        leave_id = f"LV-{uuid.uuid4().hex[:4].upper()}"
        leave_obj = {
            "leave_id": leave_id,
            "usn": usn,
            "student_name": student["name"],
            "room_no": student["room_no"],
            "block": student["block"],
            "reason": reason,
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "parent_contacted": parent_contacted,
            "status": "PENDING",
            "applied_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.leaves.insert(0, leave_obj)
        return {"success": True, "message": "Leave application submitted successfully.", "leave": leave_obj}

    def update_leave_status(self, leave_id, status):
        for lv in self.leaves:
            if lv["leave_id"] == leave_id:
                lv["status"] = status.upper()
                if status.upper() == "APPROVED":
                    s = self.get_student_by_usn(lv["usn"])
                    if s:
                        s["status"] = "ON_LEAVE"
                return {"success": True, "leave": lv}
        return {"success": False, "message": f"Leave ID {leave_id} not found."}

    def get_all_leaves(self):
        return self.leaves

    # --- Safety & Anomaly Operations ---
    def get_safety_alerts(self, unresolved_only=False):
        # Auto refresh check for overdue checkouts
        self.scan_for_overstay_anomalies()
        if unresolved_only:
            return [a for a in self.alerts if not a["resolved"]]
        return self.alerts

    def create_safety_alert(self, usn, alert_type, severity, message):
        usn = usn.upper()
        student = self.get_student_by_usn(usn)
        s_name = student["name"] if student else "Unknown Student"
        r_no = student["room_no"] if student else "N/A"
        blk = student["block"] if student else "N/A"

        alert_id = f"ALT-{uuid.uuid4().hex[:4].upper()}"
        alert_obj = {
            "alert_id": alert_id,
            "usn": usn,
            "student_name": s_name,
            "room_no": r_no,
            "block": blk,
            "alert_type": alert_type.upper(),
            "severity": severity.upper(),
            "message": message,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "resolved": False
        }
        self.alerts.insert(0, alert_obj)
        return alert_obj

    def resolve_alert(self, alert_id):
        for a in self.alerts:
            if a["alert_id"] == alert_id:
                a["resolved"] = True
                return {"success": True, "alert": a}
        return {"success": False, "message": "Alert not found."}

    def scan_for_overstay_anomalies(self):
        now = datetime.now()
        for mov in self.movements:
            if mov["direction"] == "OUT" and mov["expected_return_time"]:
                try:
                    exp_time = datetime.strptime(mov["expected_return_time"], "%Y-%m-%d %H:%M:%S")
                    if now > exp_time and mov["status"] != "OVERSTAY_ANOMALY":
                        # Check if student already checked back IN
                        student = self.get_student_by_usn(mov["usn"])
                        if student and student["status"] == "CHECKED_OUT":
                            mov["status"] = "OVERSTAY_ANOMALY"
                            # Create alert if not exists
                            exists = any(a["usn"] == mov["usn"] and a["alert_type"] == "OVERSTAY_ANOMALY" and not a["resolved"] for a in self.alerts)
                            if not exists:
                                self.create_safety_alert(
                                    usn=mov["usn"],
                                    alert_type="OVERSTAY_ANOMALY",
                                    severity="HIGH",
                                    message=f"Overdue Alert: Student {mov['student_name']} ({mov['usn']}) failed to return by {mov['expected_return_time']}."
                                )
                except Exception:
                    pass

    # --- Dashboard Summary ---
    def get_dashboard_summary(self):
        self.scan_for_overstay_anomalies()
        students_list = list(self.students.values())
        total_students = len(students_list)
        in_hostel = sum(1 for s in students_list if s["status"] == "IN_HOSTEL")
        checked_out = sum(1 for s in students_list if s["status"] == "CHECKED_OUT")
        on_leave = sum(1 for s in students_list if s["status"] == "ON_LEAVE")

        active_alerts = [a for a in self.alerts if not a["resolved"]]
        active_anomalies_count = len(active_alerts)

        rooms_list = list(self.rooms.values())
        total_rooms = len(rooms_list)
        total_capacity = sum(r["capacity"] for r in rooms_list)
        occupied_capacity = sum(r["occupied_count"] for r in rooms_list)
        occupancy_rate = round((occupied_capacity / total_capacity) * 100, 1) if total_capacity > 0 else 0

        return {
            "total_students": total_students,
            "in_hostel": in_hostel,
            "checked_out": checked_out,
            "on_leave": on_leave,
            "active_anomalies_count": active_anomalies_count,
            "total_rooms": total_rooms,
            "total_capacity": total_capacity,
            "occupied_capacity": occupied_capacity,
            "occupancy_rate": occupancy_rate,
            "active_alerts": active_alerts
        }

    def generate_report(self, report_type="daily_summary"):
        summary = self.get_dashboard_summary()
        movements = self.get_movement_logs(limit=10)
        alerts = self.get_safety_alerts(unresolved_only=False)
        leaves = self.get_all_leaves()

        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "report_type": report_type,
            "title": f"DSATM Smart Hostel Administrative Report ({report_type.replace('_', ' ').title()})",
            "summary": summary,
            "recent_movements": movements,
            "active_alerts": [a for a in alerts if not a["resolved"]],
            "all_alerts": alerts,
            "active_leaves": leaves
        }

# Singleton instance export
db = HostelDatabase()
