// DSATM Smart Hostel Management - Frontend Client Logic

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    setupTabNavigation();
    setupEventListeners();
    refreshAllData();
    setInterval(refreshAllData, 10000); // Auto-refresh every 10 sec
}

// ----------------- 1. Tab Navigation -----------------
function setupTabNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            navButtons.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const targetPane = document.getElementById(targetTab);
            if (targetPane) targetPane.classList.add('active');

            // Refresh specific pane data if needed
            if (targetTab === 'rooms-tab') fetchAndRenderRooms();
            if (targetTab === 'students-tab') { fetchAndRenderStudents(); fetchAndRenderLeaves(); }
            if (targetTab === 'safety-tab') fetchAndRenderSafetyAlerts();
        });
    });
}

// ----------------- 2. Event Listeners & Modals -----------------
function setupEventListeners() {
    // AI Drawer Toggle
    const aiToggleBtn = document.getElementById('ai-toggle-btn');
    const closeAiBtn = document.getElementById('close-ai-drawer');
    const aiDrawer = document.getElementById('ai-chat-drawer');

    aiToggleBtn.addEventListener('click', () => aiDrawer.classList.toggle('hidden'));
    closeAiBtn.addEventListener('click', () => aiDrawer.classList.add('hidden'));

    // AI Form Submission
    const aiForm = document.getElementById('ai-chat-form');
    aiForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleAiChatSubmit();
    });

    // Quick Prompt Chips
    document.querySelectorAll('.prompt-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const q = chip.getAttribute('data-query');
            document.getElementById('ai-input').value = q;
            handleAiChatSubmit();
        });
    });

    // Gate Lookup USN
    document.getElementById('lookup-usn-btn').addEventListener('click', verifyStudentForGate);
    document.getElementById('checkout-act-btn').addEventListener('click', handleGateCheckout);
    document.getElementById('checkin-act-btn').addEventListener('click', handleGateCheckin);

    // Quick Simulator Buttons
    document.querySelectorAll('.sim-student-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const usn = btn.getAttribute('data-usn');
            document.getElementById('gate-usn-input').value = usn;
            verifyStudentForGate();
        });
    });

    // Block Filter in Rooms Tab
    document.querySelectorAll('#block-filter-group .btn-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#block-filter-group .btn-tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const block = btn.getAttribute('data-block');
            fetchAndRenderRooms(block === 'all' ? null : block);
        });
    });

    // Modals Initialization & Attachments
    const addStudentModal = document.getElementById('add-student-modal');
    const leaveModal = document.getElementById('leave-modal');
    const sosModal = document.getElementById('sos-modal');

    document.getElementById('open-add-student-modal').addEventListener('click', () => addStudentModal.classList.remove('hidden'));
    document.getElementById('open-leave-modal').addEventListener('click', () => leaveModal.classList.remove('hidden'));
    document.getElementById('trigger-sos-modal-btn').addEventListener('click', () => sosModal.classList.remove('hidden'));

    // Universal Close Buttons
    document.querySelectorAll('.close-modal-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.modal-overlay').forEach(m => m.classList.add('hidden'));
        });
    });

    document.getElementById('add-student-form').addEventListener('submit', handleAddStudent);
    document.getElementById('add-leave-form').addEventListener('submit', handleLeaveSubmit);
    document.getElementById('add-sos-form').addEventListener('submit', handleSosSubmit);

    // Live Student Search Filter
    const searchInput = document.getElementById('student-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => filterStudentTable(e.target.value));
    }

    // Quick Action Buttons
    document.getElementById('quick-scan-btn').addEventListener('click', () => switchTab('gate-tab'));
    document.getElementById('quick-leave-btn').addEventListener('click', () => leaveModal.classList.remove('hidden'));
    document.getElementById('quick-sos-btn').addEventListener('click', () => sosModal.classList.remove('hidden'));
    document.getElementById('quick-report-btn').addEventListener('click', generateAndShowReport);
    document.getElementById('refresh-dashboard-btn').addEventListener('click', refreshAllData);
}

function switchTab(tabId) {
    const btn = document.querySelector(`.nav-btn[data-tab="${tabId}"]`);
    if (btn) btn.click();
}

// ----------------- 3. Refresh Dashboard & Data -----------------
async function refreshAllData() {
    try {
        const res = await fetch('/api/summary');
        const data = await res.json();

        document.getElementById('kpi-total-students').textContent = data.total_students;
        document.getElementById('kpi-in-hostel').textContent = data.in_hostel;
        document.getElementById('kpi-checked-out').textContent = data.checked_out;
        document.getElementById('kpi-on-leave').textContent = data.on_leave;
        document.getElementById('kpi-anomalies').textContent = data.active_anomalies_count;

        document.getElementById('header-alert-count').textContent = data.active_anomalies_count;
        document.getElementById('safety-active-count').textContent = `${data.active_anomalies_count} Active`;

        const presentPct = data.total_students > 0 ? Math.round((data.in_hostel / data.total_students) * 100) : 0;
        document.getElementById('kpi-present-pct').textContent = `${presentPct}% Present`;

        // Update Block Progress Bars
        updateBlockBars();
        fetchAndRenderMovementLogs();
    } catch (e) {
        console.error("Dashboard refresh error:", e);
    }
}

async function updateBlockBars() {
    try {
        const res = await fetch('/api/rooms');
        const rooms = await res.json();

        const blockARooms = rooms.filter(r => r.block.includes('Block A'));
        const blockBRooms = rooms.filter(r => r.block.includes('Block B'));

        const aCap = blockARooms.reduce((acc, r) => acc + r.capacity, 0);
        const aOcc = blockARooms.reduce((acc, r) => acc + r.occupied_count, 0);
        const aPct = aCap > 0 ? Math.round((aOcc / aCap) * 100) : 0;

        const bCap = blockBRooms.reduce((acc, r) => acc + r.capacity, 0);
        const bOcc = blockBRooms.reduce((acc, r) => acc + r.occupied_count, 0);
        const bPct = bCap > 0 ? Math.round((bOcc / bCap) * 100) : 0;

        document.getElementById('block-a-stat').textContent = `${aOcc} / ${aCap} Beds Occupied (${aPct}%)`;
        document.getElementById('block-a-progress').style.width = `${aPct}%`;

        document.getElementById('block-b-stat').textContent = `${bOcc} / ${bCap} Beds Occupied (${bPct}%)`;
        document.getElementById('block-b-progress').style.width = `${bPct}%`;
    } catch (e) {
        console.error(e);
    }
}

async function fetchAndRenderMovementLogs() {
    try {
        const res = await fetch('/api/movements/logs?limit=8');
        const logs = await res.json();
        const tbody = document.getElementById('movements-tbody');

        if (!logs || logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center">No movement logs recorded yet.</td></tr>';
            return;
        }

        tbody.innerHTML = logs.map(l => {
            const dirBadge = l.direction === 'OUT' 
                ? '<span class="badge badge-warning"><i class="fa-solid fa-arrow-right-from-bracket"></i> OUT</span>'
                : '<span class="badge badge-success"><i class="fa-solid fa-arrow-right-to-bracket"></i> IN</span>';
            
            const statusBadge = l.status === 'OVERSTAY_ANOMALY'
                ? '<span class="badge badge-danger">OVERSTAY</span>'
                : '<span class="badge badge-info">NORMAL</span>';

            return `
                <tr>
                    <td>${l.timestamp}</td>
                    <td><strong>${l.usn}</strong></td>
                    <td>${l.student_name}</td>
                    <td>${l.room_no}</td>
                    <td>${dirBadge}</td>
                    <td>${l.destination || 'Gate'}</td>
                    <td>${l.expected_return_time || '-'}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error(e);
    }
}

// ----------------- 4. Room Grid Rendering -----------------
async function fetchAndRenderRooms(blockFilter = null) {
    try {
        let url = '/api/rooms';
        if (blockFilter) url += `?block=${encodeURIComponent(blockFilter)}`;
        
        const res = await fetch(url);
        const rooms = await res.json();

        const container = document.getElementById('room-grid-container');
        if (!rooms || rooms.length === 0) {
            container.innerHTML = '<p class="text-muted">No rooms found for selected block.</p>';
            return;
        }

        container.innerHTML = rooms.map(r => `
            <div class="room-card status-${r.status}" onclick="openRoomModal('${r.room_no}')">
                <div class="room-card-head">
                    <h4>${r.room_no}</h4>
                    <span class="badge badge-${r.status === 'FULL' ? 'danger' : (r.status === 'VACANT' ? 'success' : 'warning')}">${r.status}</span>
                </div>
                <div class="room-card-body">
                    <p><i class="fa-solid fa-bed"></i> Occupancy: <strong>${r.occupied_count} / ${r.capacity}</strong></p>
                    <p class="text-dim">${r.block}</p>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

// ----------------- 5. Gate Terminal Actions -----------------
async function verifyStudentForGate() {
    const usn = document.getElementById('gate-usn-input').value.trim();
    if (!usn) return showToast("Please enter a valid Student USN.", "danger");

    try {
        const res = await fetch(`/api/students/${encodeURIComponent(usn)}`);
        if (!res.ok) {
            document.getElementById('student-preview-box').classList.add('hidden');
            return showToast(`Student USN ${usn} not found!`, "danger");
        }
        const s = await res.json();
        
        document.getElementById('prev-name').textContent = s.name;
        document.getElementById('prev-usn-dept').textContent = `${s.usn} • ${s.dept} ${s.year}`;
        document.getElementById('prev-room').textContent = `Room ${s.room_no} (${s.block})`;
        
        const statusElem = document.getElementById('prev-status');
        statusElem.textContent = s.status;
        statusElem.className = `badge badge-${s.status === 'IN_HOSTEL' ? 'success' : (s.status === 'CHECKED_OUT' ? 'warning' : 'info')}`;

        document.getElementById('student-preview-box').classList.remove('hidden');
        showToast(`Verified resident: ${s.name}`, "success");
    } catch (e) {
        showToast("Error verifying student.", "danger");
    }
}

async function handleGateCheckout() {
    const usn = document.getElementById('gate-usn-input').value.trim();
    const dest = document.getElementById('gate-dest-input').value.trim() || "Local Outing";
    const hrs = parseFloat(document.getElementById('gate-duration-select').value);

    if (!usn) return showToast("Please enter or scan Student USN.", "danger");

    try {
        const res = await fetch('/api/movements/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ usn: usn, destination: dest, expected_return_hours: hrs })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            verifyStudentForGate();
            refreshAllData();
        } else {
            showToast(data.message || "Checkout failed", "danger");
        }
    } catch (e) {
        showToast("Checkout API error.", "danger");
    }
}

async function handleGateCheckin() {
    const usn = document.getElementById('gate-usn-input').value.trim();
    if (!usn) return showToast("Please enter or scan Student USN.", "danger");

    try {
        const res = await fetch('/api/movements/checkin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ usn: usn })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            verifyStudentForGate();
            refreshAllData();
        } else {
            showToast(data.message || "Checkin failed", "danger");
        }
    } catch (e) {
        showToast("Checkin API error.", "danger");
    }
}

// ----------------- 6. Student & Leave Management -----------------
async function fetchAndRenderStudents() {
    try {
        const res = await fetch('/api/students');
        const students = await res.json();
        const tbody = document.getElementById('students-tbody');

        tbody.innerHTML = students.map(s => `
            <tr>
                <td><strong>${s.usn}</strong></td>
                <td>${s.name}</td>
                <td>${s.dept} (${s.year})</td>
                <td>${s.room_no} (${s.block.split('-')[0]})</td>
                <td>${s.phone}</td>
                <td>${s.guardian_phone}</td>
                <td><span class="badge badge-${s.status === 'IN_HOSTEL' ? 'success' : (s.status === 'CHECKED_OUT' ? 'warning' : 'info')}">${s.status}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="quickSelectGate('${s.usn}')"><i class="fa-solid fa-qrcode"></i> Gate</button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

window.quickSelectGate = function(usn) {
    document.getElementById('gate-usn-input').value = usn;
    switchTab('gate-tab');
    verifyStudentForGate();
};

async function fetchAndRenderLeaves() {
    try {
        const res = await fetch('/api/leaves');
        const leaves = await res.json();
        const tbody = document.getElementById('leaves-tbody');

        if (!leaves || leaves.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center">No leave applications found.</td></tr>';
            return;
        }

        tbody.innerHTML = leaves.map(l => `
            <tr>
                <td><strong>${l.leave_id}</strong></td>
                <td>${l.student_name} (${l.usn})</td>
                <td>${l.reason}</td>
                <td>${l.destination}</td>
                <td>${l.start_date} to ${l.end_date}</td>
                <td>${l.parent_contacted ? '<span class="badge badge-success">Verified</span>' : '<span class="badge badge-warning">Pending</span>'}</td>
                <td><span class="badge badge-${l.status === 'APPROVED' ? 'success' : (l.status === 'PENDING' ? 'warning' : 'danger')}">${l.status}</span></td>
                <td>
                    ${l.status === 'PENDING' ? `
                        <button class="btn btn-sm btn-success" onclick="updateLeave('${l.leave_id}', 'APPROVED')">Approve</button>
                        <button class="btn btn-sm btn-danger" onclick="updateLeave('${l.leave_id}', 'REJECTED')">Reject</button>
                    ` : '<span class="text-dim">Done</span>'}
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

window.updateLeave = async function(leaveId, status) {
    try {
        const res = await fetch(`/api/leaves/${leaveId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: status })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Leave ${status} successfully.`, "success");
            fetchAndRenderLeaves();
            refreshAllData();
        }
    } catch (e) {
        showToast("Failed to update leave.", "danger");
    }
};

async function handleAddStudent(e) {
    e.preventDefault();
    const payload = {
        usn: document.getElementById('new-usn').value.trim(),
        name: document.getElementById('new-name').value.trim(),
        dept: document.getElementById('new-dept').value.trim(),
        year: document.getElementById('new-year').value,
        block: document.getElementById('new-block').value,
        room_no: document.getElementById('new-room').value.trim(),
        phone: document.getElementById('new-phone').value.trim(),
        guardian_phone: document.getElementById('new-gphone').value.trim()
    };

    try {
        const res = await fetch('/api/students', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Resident ${payload.name} added successfully!`, "success");
            document.getElementById('add-student-modal').classList.add('hidden');
            fetchAndRenderStudents();
            refreshAllData();
        }
    } catch (e) {
        showToast("Failed to register student.", "danger");
    }
}

// ----------------- 7. Safety Alerts -----------------
async function fetchAndRenderSafetyAlerts() {
    try {
        const res = await fetch('/api/alerts');
        const alerts = await res.json();
        const container = document.getElementById('safety-alerts-list');

        if (!alerts || alerts.length === 0) {
            container.innerHTML = '<p class="text-muted">No safety alerts recorded. All systems normal.</p>';
            return;
        }

        container.innerHTML = alerts.map(a => `
            <div class="glass-card margin-bottom-sm ${a.resolved ? 'opacity-70' : 'border-danger'}">
                <div class="card-header">
                    <h4><i class="fa-solid fa-triangle-exclamation text-danger"></i> ${a.alert_type} (${a.severity})</h4>
                    <span class="badge badge-${a.resolved ? 'success' : 'danger'}">${a.resolved ? 'RESOLVED' : 'ACTIVE'}</span>
                </div>
                <p><strong>Student:</strong> ${a.student_name} (${a.usn}) • Room ${a.room_no}</p>
                <p class="margin-top-xs">${a.message}</p>
                <div class="card-footer margin-top-sm">
                    <span class="text-dim font-xs">${a.created_at}</span>
                    ${!a.resolved ? `<button class="btn btn-sm btn-outline" onclick="resolveAlert('${a.alert_id}')">Resolve Alert</button>` : ''}
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

window.resolveAlert = async function(alertId) {
    try {
        const res = await fetch(`/api/alerts/${alertId}/resolve`, { method: 'PUT' });
        const data = await res.json();
        if (data.success) {
            showToast("Alert resolved.", "success");
            fetchAndRenderSafetyAlerts();
            refreshAllData();
        }
    } catch (e) {
        showToast("Error resolving alert.", "danger");
    }
};

// ----------------- 8. AI Chat Assistant -----------------
async function handleAiChatSubmit() {
    const inputElem = document.getElementById('ai-input');
    const query = inputElem.value.trim();
    if (!query) return;

    inputElem.value = '';

    const container = document.getElementById('ai-messages-container');

    // Render User Message
    container.innerHTML += `
        <div class="ai-msg user-msg">
            <div class="msg-avatar"><i class="fa-solid fa-user"></i></div>
            <div class="msg-content"><p>${escapeHtml(query)}</p></div>
        </div>
    `;

    // Render Loading Bot Message
    const loadingId = `bot-loading-${Date.now()}`;
    container.innerHTML += `
        <div class="ai-msg bot-msg" id="${loadingId}">
            <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="msg-content"><p><i class="fa-solid fa-spinner fa-spin"></i> Consulting Hostel Agent & Tools...</p></div>
        </div>
    `;
    container.scrollTop = container.scrollHeight;

    try {
        const res = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        const data = await res.json();

        const loadingElem = document.getElementById(loadingId);
        if (loadingElem) loadingElem.remove();

        const toolsBadge = data.tools_used && data.tools_used.length > 0 
            ? `<div class="margin-top-xs font-xs text-dim"><i class="fa-solid fa-wrench"></i> Executed Tools: <strong>${data.tools_used.join(', ')}</strong></div>`
            : '';

        container.innerHTML += `
            <div class="ai-msg bot-msg">
                <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="msg-content">
                    <p>${formatMarkdownText(data.response)}</p>
                    ${toolsBadge}
                </div>
            </div>
        `;
        container.scrollTop = container.scrollHeight;

        // Auto-refresh main UI in case AI performed an operational action (e.g. checkin/checkout)
        refreshAllData();
    } catch (e) {
        const loadingElem = document.getElementById(loadingId);
        if (loadingElem) {
            loadingElem.querySelector('.msg-content').innerHTML = '<p class="text-danger">Failed to communicate with AI Assistant backend.</p>';
        }
    }
}

// Helper Utilities
function showToast(message, type = "success") {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<i class="fa-solid fa-${type === 'success' ? 'circle-check' : 'circle-exclamation'}"></i> ${message}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

async function handleLeaveSubmit(e) {
    e.preventDefault();
    const payload = {
        usn: document.getElementById('leave-usn').value.trim(),
        reason: document.getElementById('leave-reason').value.trim(),
        destination: document.getElementById('leave-dest').value.trim(),
        start_date: document.getElementById('leave-start').value,
        end_date: document.getElementById('leave-end').value
    };

    try {
        const res = await fetch('/api/leaves', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast("Leave application submitted successfully!", "success");
            document.getElementById('leave-modal').classList.add('hidden');
            fetchAndRenderLeaves();
            refreshAllData();
        } else {
            showToast(data.message || "Failed to submit leave.", "danger");
        }
    } catch (e) {
        showToast("Error submitting leave application.", "danger");
    }
}

async function handleSosSubmit(e) {
    e.preventDefault();
    const payload = {
        usn: document.getElementById('sos-usn').value.trim(),
        alert_type: document.getElementById('sos-type').value,
        severity: document.getElementById('sos-severity').value,
        message: document.getElementById('sos-message').value.trim()
    };

    try {
        const res = await fetch('/api/alerts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast("Emergency Alert Triggered! Warden notified.", "danger");
            document.getElementById('sos-modal').classList.add('hidden');
            fetchAndRenderSafetyAlerts();
            refreshAllData();
        } else {
            showToast("Failed to trigger alert.", "danger");
        }
    } catch (e) {
        showToast("Error sending SOS alert.", "danger");
    }
}

async function openRoomModal(roomNo) {
    try {
        const res = await fetch('/api/rooms');
        const rooms = await res.json();
        const room = rooms.find(r => r.room_no === roomNo);
        if (!room) return;

        const modal = document.getElementById('room-detail-modal');
        document.getElementById('room-modal-title').innerHTML = `<i class="fa-solid fa-door-open"></i> Room ${room.room_no} (${room.block})`;

        let occupantsHtml = '';
        if (room.occupants && room.occupants.length > 0) {
            const studentPromises = room.occupants.map(usn => fetch(`/api/students/${usn}`).then(r => r.json()));
            const students = await Promise.all(studentPromises);

            occupantsHtml = students.map(s => `
                <div class="glass-card margin-bottom-xs p-3">
                    <div class="flex-between">
                        <strong><i class="fa-solid fa-user-graduate"></i> ${s.name} (${s.usn})</strong>
                        <span class="badge badge-${s.status === 'IN_HOSTEL' ? 'success' : (s.status === 'CHECKED_OUT' ? 'warning' : 'info')}">${s.status}</span>
                    </div>
                    <p class="font-xs text-dim margin-top-xs">${s.dept} ${s.year} • Phone: ${s.phone}</p>
                    <p class="font-xs text-dim">Guardian Phone: ${s.guardian_phone}</p>
                    <div class="margin-top-xs">
                        <button class="btn btn-sm btn-outline" onclick="document.getElementById('room-detail-modal').classList.add('hidden'); quickSelectGate('${s.usn}');">Gate Action</button>
                    </div>
                </div>
            `).join('');
        } else {
            occupantsHtml = '<p class="text-muted">Room is currently vacant.</p>';
        }

        document.getElementById('room-modal-body').innerHTML = `
            <div class="margin-bottom-sm flex-between">
                <div>Status: <span class="badge badge-${room.status === 'FULL' ? 'danger' : (room.status === 'VACANT' ? 'success' : 'warning')}">${room.status}</span></div>
                <div>Occupancy: <strong>${room.occupied_count} / ${room.capacity} Beds</strong></div>
            </div>
            <h4 class="margin-top-sm margin-bottom-xs">Assigned Occupants:</h4>
            ${occupantsHtml}
        `;
        modal.classList.remove('hidden');
    } catch (e) {
        showToast("Error loading room details.", "danger");
    }
}

function filterStudentTable(query) {
    const q = query.toLowerCase().trim();
    const rows = document.querySelectorAll('#students-tbody tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(q)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

async function generateAndShowReport() {
    const modal = document.getElementById('report-modal');
    const container = document.getElementById('report-modal-body');
    modal.classList.remove('hidden');
    container.innerHTML = '<div class="text-center p-4"><i class="fa-solid fa-spinner fa-spin"></i> Generating administrative report...</div>';

    try {
        const res = await fetch('/api/reports/generate?report_type=daily_summary');
        const report = await res.json();
        const s = report.summary;

        container.innerHTML = `
            <div class="report-header text-center margin-bottom-md">
                <h2>DAYANANDA SAGAR ACADEMY OF TECHNOLOGY & MANAGEMENT</h2>
                <p class="font-xs text-dim">Kanankapura Road, Bangalore • Hostel Administrative Department</p>
                <h3 class="margin-top-xs text-primary">${report.title}</h3>
                <span class="badge badge-primary">Generated at: ${report.generated_at}</span>
            </div>

            <div class="kpi-grid margin-bottom-md">
                <div class="kpi-card glass-card p-3">
                    <span class="kpi-label">Total Resident Students</span>
                    <h2>${s.total_students}</h2>
                </div>
                <div class="kpi-card glass-card p-3">
                    <span class="kpi-label">Present in Hostel</span>
                    <h2 class="text-success">${s.in_hostel}</h2>
                </div>
                <div class="kpi-card glass-card p-3">
                    <span class="kpi-label">Checked Out (Outings)</span>
                    <h2 class="text-warning">${s.checked_out}</h2>
                </div>
                <div class="kpi-card glass-card p-3">
                    <span class="kpi-label">Active Safety Alerts</span>
                    <h2 class="text-danger">${s.active_anomalies_count}</h2>
                </div>
            </div>

            <h4 class="margin-top-md"><i class="fa-solid fa-triangle-exclamation text-danger"></i> Active Anomalies & Curfew Alerts</h4>
            ${report.active_alerts && report.active_alerts.length > 0 ? `
                <table class="data-table margin-top-xs">
                    <thead><tr><th>ID</th><th>Student</th><th>Room</th><th>Type</th><th>Message</th></tr></thead>
                    <tbody>${report.active_alerts.map(a => `<tr><td>${a.alert_id}</td><td>${a.student_name} (${a.usn})</td><td>${a.room_no}</td><td><span class="badge badge-danger">${a.alert_type}</span></td><td>${a.message}</td></tr>`).join('')}</tbody>
                </table>
            ` : '<p class="text-success font-xs margin-top-xs"><i class="fa-solid fa-circle-check"></i> No active safety anomalies recorded.</p>'}

            <h4 class="margin-top-md"><i class="fa-solid fa-clock-rotate-left"></i> Recent Gate Movements</h4>
            <table class="data-table margin-top-xs">
                <thead><tr><th>Time</th><th>USN</th><th>Student</th><th>Direction</th><th>Destination</th></tr></thead>
                <tbody>${report.recent_movements.slice(0, 5).map(m => `<tr><td>${m.timestamp}</td><td>${m.usn}</td><td>${m.student_name}</td><td><span class="badge badge-${m.direction==='OUT'?'warning':'success'}">${m.direction}</span></td><td>${m.destination||'-'}</td></tr>`).join('')}</tbody>
            </table>
        `;
    } catch (e) {
        container.innerHTML = '<div class="text-danger p-4 text-center">Failed to generate administrative report.</div>';
    }
}

function showToast(message, type = "success") {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<i class="fa-solid fa-${type === 'success' ? 'circle-check' : 'circle-exclamation'}"></i> ${message}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function formatMarkdownText(txt) {
    if (!txt) return '';
    let formatted = escapeHtml(txt);

    // Headers
    formatted = formatted.replace(/^### (.*$)/gim, '<h4>$1</h4>');
    formatted = formatted.replace(/^## (.*$)/gim, '<h3>$1</h3>');
    formatted = formatted.replace(/^# (.*$)/gim, '<h2>$1</h2>');

    // Bold & Code
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="chat-code">$1</code>');

    // Lists
    formatted = formatted.replace(/^\s*[-*+]\s+(.*$)/gim, '<li>$1</li>');
    formatted = formatted.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');

    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');
    return formatted;
}
