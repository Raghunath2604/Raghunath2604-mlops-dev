import re

path = "c:/Users/raghu/Downloads/mlopsdev-phase1-launch/mlops-dev/frontend/dashboard.html"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update navigation to support Admin Panel conditionally
nav_old = """
    <button class="sb-link" onclick="nav('settings',this)"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg><span>Settings</span></button>
"""
nav_new = """
    <button class="sb-link" onclick="nav('settings',this)"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg><span>Settings</span></button>
    <button class="sb-link" onclick="nav('admin',this)" id="nav-admin" style="display:none;"><svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg><span style="color:var(--lavender)">Admin Panel</span></button>
"""
content = content.replace(nav_old.strip(), nav_new.strip())

# 2. Add admin page HTML
admin_page = """
      <!-- ADMIN -->
      <div class="page" id="page-admin">
        <div class="panel" style="margin-bottom: 1.5rem;">
            <div class="ph"><h3>Pending User Requests</h3></div>
            <table class="ftable">
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Requested At</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="pending-users-list">
                    <tr><td colspan="3">Loading...</td></tr>
                </tbody>
            </table>
        </div>
        <div class="panel">
            <div class="ph"><h3>All Users</h3></div>
            <table class="ftable">
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
# insert before </div> <!-- END Pages -->
content = re.sub(r'(      <!-- SETTINGS -->)', admin_page + r'\n\1', content)

# 3. Add admin JS
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
                <td class="td-name">${escapeHTML(u.name)}</td>
                <td class="td-hw">${new Date(u.created_at).toLocaleString()}</td>
                <td>
                    <button class="tb-btn primary" onclick="approveUser('${u.id}')">Approve</button>
                    <button class="act-btn del" style="margin-left: 0.5rem;" onclick="rejectUser('${u.id}')">Reject</button>
                </td>
            </tr>
        `).join('');
        document.getElementById('pending-users-list').innerHTML = pending.length ? pendingHtml : '<tr><td colspan="3" class="td-hw">No pending requests</td></tr>';
        
        const allHtml = all.map(u => `
            <tr>
                <td class="td-hw">${u.id}</td>
                <td class="td-name">${escapeHTML(u.name)}</td>
                <td><span class="sbadge ${u.role === 'admin' ? 's-off' : 's-up'}">${u.role}</span></td>
                <td><span class="sbadge ${u.approval_status === 'approved' ? 's-on' : (u.approval_status === 'pending' ? 's-up' : 's-off')}">${u.approval_status}</span></td>
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
content = re.sub(r'async function doLogin\(\)', admin_js + "\n  async function doLogin()", content)

# 4. Modify switchPage/nav to load admin data
content = re.sub(
    r'if\(page===\'events\'\) renderEvents\(\);',
    "if(page==='events') renderEvents();\n    if(page==='admin') loadAdminData();",
    content
)

# 5. Modify bootApp to respect roles
boot_app_old = """
    document.getElementById('sb-urole').textContent=user.role||'member';
    document.getElementById('s-name').value=user.name||'';
    document.getElementById('s-email').value=user.email||'';
    document.getElementById('s-role').value=user.role||'';
"""
boot_app_new = """
    document.getElementById('sb-urole').textContent=user.role||'member';
    document.getElementById('s-name').value=user.name||'';
    document.getElementById('s-email').value=user.email||'';
    document.getElementById('s-role').value=user.role||'';
    
    // RBAC UI Enforcement
    if (user.role === 'admin') {
        document.getElementById('nav-admin').style.display = 'flex';
    } else {
        document.getElementById('nav-admin').style.display = 'none';
        if(document.getElementById('page-admin').classList.contains('active')) nav('overview');
    }
"""
content = content.replace(boot_app_old, boot_app_new)

# 6. Update doLogin tier to role
content = content.replace("const user = {name: data.user.email, email: data.user.email, role: data.user.tier};", "const user = {name: data.user.email, email: data.user.email, role: data.user.role};")

# 7. Update checkAuth tier to role
content = content.replace("const user = {name: data.user.email, email: data.user.email, role: data.user.tier};\n      bootApp(user);", "const user = {name: data.user.email, email: data.user.email, role: data.user.role};\n      bootApp(user);")

# 8. Update checkAuth to check ok properly
content = re.sub(r'if\(!resp\.ok\) throw new Error\(\'Unauth\'\);', r'if(!resp.ok) throw new Error(\'Unauth\');', content)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated dashboard.html successfully for Phase 4 Admin UI")
