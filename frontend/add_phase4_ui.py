import re

path = "c:/Users/raghu/Downloads/mlopsdev-phase1-launch/mlops-dev/frontend/dashboard.html"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update navigation to support Admin Panel conditionally
nav_old = """
            <nav id="sidebar-nav">
                <div class="nav-item active" onclick="switchPage('overview')" id="nav-overview">Overview</div>
                <div class="nav-item" onclick="switchPage('devices')" id="nav-devices">Devices</div>
                <div class="nav-item" onclick="switchPage('events')" id="nav-events">Events</div>
                <div class="nav-item" onclick="switchPage('billing')" id="nav-billing">Billing</div>
            </nav>
"""
nav_new = """
            <nav id="sidebar-nav">
                <div class="nav-item active" onclick="switchPage('overview')" id="nav-overview">Overview</div>
                <div class="nav-item" onclick="switchPage('devices')" id="nav-devices">Devices</div>
                <div class="nav-item" onclick="switchPage('events')" id="nav-events">Events</div>
                <div class="nav-item" onclick="switchPage('billing')" id="nav-billing" style="display:none;">Billing</div>
                <div class="nav-item" onclick="switchPage('admin')" id="nav-admin" style="display:none; color: var(--accent);">Admin Panel</div>
            </nav>
"""
content = content.replace(nav_old, nav_new)

# 2. Add admin page HTML
admin_page = """
            <div id="page-admin" class="page" style="display:none;">
                <h2>Admin Panel - User Management</h2>
                <div class="card">
                    <h3>Pending Requests</h3>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Email</th>
                                <th>Request Date</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="pending-users-list">
                            <tr><td colspan="3">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="card" style="margin-top: 2rem;">
                    <h3>All Users</h3>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Email</th>
                                <th>Role</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="all-users-list">
                            <tr><td colspan="4">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
"""
# insert before </main>
content = re.sub(r'(\s*)</main>', "\n" + admin_page + r'\1</main>', content)

# 3. Add JS functions for admin
admin_js = """
// Admin JS Functions
async function loadAdminData() {
    try {
        const resp = await apiFetch('/admin/users');
        if(!resp.success) return;
        
        const pending = resp.users.filter(u => u.approval_status === 'pending');
        const all = resp.users;
        
        const pendingHtml = pending.map(u => `
            <tr>
                <td>${escapeHTML(u.name)}</td>
                <td>${new Date(u.created_at).toLocaleString()}</td>
                <td>
                    <button class="btn btn-sm" onclick="approveUser('${u.id}')">Approve</button>
                    <button class="btn btn-sm btn-outline" style="margin-left: 0.5rem;" onclick="rejectUser('${u.id}')">Reject</button>
                </td>
            </tr>
        `).join('');
        document.getElementById('pending-users-list').innerHTML = pending.length ? pendingHtml : '<tr><td colspan="3">No pending requests</td></tr>';
        
        const allHtml = all.map(u => `
            <tr>
                <td>${u.id}</td>
                <td>${escapeHTML(u.name)}</td>
                <td><span class="badge ${u.role === 'admin' ? 'badge-err' : 'badge-ok'}">${u.role}</span></td>
                <td><span class="badge ${u.approval_status === 'approved' ? 'badge-ok' : (u.approval_status === 'pending' ? 'badge-warn' : 'badge-err')}">${u.approval_status}</span></td>
            </tr>
        `).join('');
        document.getElementById('all-users-list').innerHTML = allHtml;
        
    } catch (e) {
        console.error(e);
    }
}

async function approveUser(id) {
    if(confirm('Approve this user?')) {
        await apiFetch(`/admin/users/${id}/approve`, {method: 'POST'});
        loadAdminData();
    }
}

async function rejectUser(id) {
    if(confirm('Reject this user request?')) {
        await apiFetch(`/admin/users/${id}/reject`, {method: 'POST'});
        loadAdminData();
    }
}
"""
content = re.sub(r'async function initApp\(\) \{', admin_js + "\nasync function initApp() {", content)

# 4. Modify switchPage to load admin data
content = re.sub(
    r'if\(page===\'events\'\) renderEvents\(\);',
    "if(page==='events') renderEvents();\n    if(page==='admin') loadAdminData();",
    content
)

# 5. Modify initApp to respect roles
init_app_old = """
        document.getElementById('user-email').textContent = resp.user.email || resp.user.id;
        document.getElementById('auth-screen').style.display = 'none';
"""
init_app_new = """
        document.getElementById('user-email').textContent = resp.user.email || resp.user.id;
        document.getElementById('auth-screen').style.display = 'none';
        
        // RBAC logic
        if (resp.user.role === 'admin') {
            document.getElementById('nav-admin').style.display = 'block';
            document.getElementById('nav-billing').style.display = 'block'; // Only admins can see billing
        } else {
            document.getElementById('nav-admin').style.display = 'none';
            document.getElementById('nav-billing').style.display = 'none';
        }
"""
content = content.replace(init_app_old, init_app_new)

# 6. Update login UI to include Request Access mode
login_ui_old = """
        <div class="tabs">
            <div class="tab active">Admin Access</div>
            <div class="tab">Request Access</div>
        </div>
"""
login_ui_new = """
        <div class="tabs">
            <div class="tab active" id="tab-login" onclick="toggleAuthMode('login')">Admin / User Login</div>
            <div class="tab" id="tab-register" onclick="toggleAuthMode('register')">Request Access</div>
        </div>
"""
content = content.replace(login_ui_old, login_ui_new)

# 7. Add JS to handle register
auth_mode_js = """
let authMode = 'login';
function toggleAuthMode(mode) {
    authMode = mode;
    clearErr('login-err');
    if(mode === 'login') {
        document.getElementById('tab-login').classList.add('active');
        document.getElementById('tab-register').classList.remove('active');
        document.getElementById('li-btn').textContent = 'Access Dashboard →';
    } else {
        document.getElementById('tab-register').classList.add('active');
        document.getElementById('tab-login').classList.remove('active');
        document.getElementById('li-btn').textContent = 'Request Approval';
    }
}
"""
content = re.sub(r'async function doLogin\(\) \{', auth_mode_js + "\nasync function doLogin() {", content)

# 8. Update doLogin to support registration flow
login_logic_old = """
        const resp = await fetch(`${API}/auth/login`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({key: pw}),
            credentials: 'include'
        });
        const data = await resp.json();
        if(!resp.ok) throw new Error(data.error || 'Login failed');
        initApp();
"""
login_logic_new = """
        if (authMode === 'login') {
            const resp = await fetch(`${API}/auth/login`, {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({key: pw}),
                credentials: 'include'
            });
            const data = await resp.json();
            if(!resp.ok) throw new Error(data.error || 'Login failed');
            initApp();
        } else {
            const resp = await fetch(`${API}/auth/register`, {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({email: email, password: pw}),
            });
            const data = await resp.json();
            if(!resp.ok) throw new Error(data.error || 'Registration failed');
            
            // Show success message
            const errDiv = document.getElementById('login-err');
            errDiv.style.display = 'block';
            errDiv.style.background = 'rgba(16, 185, 129, 0.1)';
            errDiv.style.border = '1px solid var(--ok)';
            errDiv.style.color = 'var(--ok)';
            errDiv.textContent = 'Success! Your request has been sent to the Admin for approval.';
        }
"""
content = content.replace(login_logic_old, login_logic_new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated dashboard.html successfully for Phase 4 UI")
