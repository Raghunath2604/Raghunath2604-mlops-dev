import re

with open("dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. HTML Replacements
html = html.replace('onclick="switchTab(\'login\')">Sign in</button>', 'onclick="switchTab(\'login\')">Admin Access</button>')
html = html.replace('onclick="switchTab(\'register\')">Create account</button>', 'onclick="switchTab(\'register\')">Request Access</button>')

html = html.replace(
    '<div class="fg"><label>Email</label><input id="li-email" type="email" placeholder="demo@nodepilot.dev" autocomplete="email"/></div>',
    '<div class="fg"><label>Admin Email</label><input id="li-email" type="email" placeholder="admin@mlops.dev" autocomplete="email"/></div>'
)

html = html.replace(
    '<div class="fg"><label>Password</label><input id="li-pw" type="password" placeholder="Password" autocomplete="current-password"/></div>',
    '<div class="fg"><label>API Key</label><input id="li-pw" type="password" placeholder="Enter your API Key" autocomplete="current-password"/></div>'
)

html = html.replace('onclick="doLogin()">Sign in to dashboard', 'onclick="doLogin()">Access Dashboard')

html = html.replace(
    '<p class="auth-hint">Demo: <strong>demo@nodepilot.dev</strong> / <strong>demo1234</strong></p>',
    '<p class="auth-hint">Only approved admins can access the dashboard. Demo key: <strong>demo</strong></p>'
)

html = html.replace(
    '<div class="fg"><label>Password * (min 8 chars)</label><input id="ri-pw" type="password" placeholder="Choose a password" autocomplete="new-password"/></div>',
    '<div class="fg"><label>Company / Project (Optional)</label><input id="ri-pw" type="text" placeholder="Where will you use MLOps.dev?" autocomplete="off"/></div>'
)

html = html.replace('onclick="doRegister()">Create account', 'onclick="doRegister()">Request Access')


# 2. JS Replace Login
old_login = """async function doLogin() {
    clearErr('login-err');
    const email=document.getElementById('li-email').value.trim();
    const pw=document.getElementById('li-pw').value;
    if(!email||!pw){showErr('login-err','Email and password required');return;}
    const btn=document.getElementById('li-btn');
    btn.disabled=true;btn.textContent='Signing in…';
    try {
      await new Promise(r=>setTimeout(r,600)); const res = {data: {token: "demo", user: {name: "Raghunath", email: "demo@mlops.dev", role: "admin"}}};
      localStorage.setItem('np_token',res.data.token);
      localStorage.setItem('np_user',JSON.stringify(res.data.user));
      bootApp(res.data.user);
    } catch(e){showErr('login-err',e.message||'Invalid credentials');btn.disabled=false;btn.textContent='Sign in to dashboard →';}
  }"""
  
# Wait, the ellipsis and arrow in the file might be encoded weirdly. 
# Let's extract the actual string from the file first
login_start = "async function doLogin() {"
login_end = "document.getElementById('li-pw').addEventListener('keypress'"
start_idx = html.find(login_start)
end_idx = html.find(login_end, start_idx)
if start_idx != -1 and end_idx != -1:
    old_login_actual = html[start_idx:end_idx]
    new_login = """async function doLogin() {
    clearErr('login-err');
    const pw=document.getElementById('li-pw').value.trim();
    if(!pw){showErr('login-err','API Key required');return;}
    const btn=document.getElementById('li-btn');
    btn.disabled=true;btn.textContent='Verifying...';
    try {
      localStorage.setItem('np_token', pw);
      await apiFetch('/status');
      const email = document.getElementById('li-email').value.trim() || "admin@mlops.dev";
      const user = {name: "Admin", email: email, role: "admin"};
      localStorage.setItem('np_user', JSON.stringify(user));
      bootApp(user);
    } catch(e){
      localStorage.removeItem('np_token');
      showErr('login-err','Invalid API Key or Not Approved');
      btn.disabled=false;btn.textContent='Access Dashboard';
    }
  }
  """
    html = html.replace(old_login_actual, new_login)


# 3. JS Replace Register
reg_start = "async function doRegister() {"
reg_end = "function switchTab(t)"
start_idx = html.find(reg_start)
end_idx = html.find(reg_end, start_idx)
if start_idx != -1 and end_idx != -1:
    old_reg_actual = html[start_idx:end_idx]
    new_reg = """async function doRegister() {
    clearErr('reg-err');
    const name=document.getElementById('ri-name').value.trim();
    const email=document.getElementById('ri-email').value.trim();
    const source=document.getElementById('ri-pw').value.trim();
    if(!name||!email){showErr('reg-err','Name and Email required');return;}
    const btn=document.getElementById('ri-btn');btn.disabled=true;btn.textContent='Submitting...';
    try {
      const waitlistApiUrl = API.replace(/\\/v1\\/?$/, '/api/waitlist');
      const res = await fetch(waitlistApiUrl, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({name, email, source})
      });
      const data = await res.json().catch(()=>({}));
      if (!res.ok) throw new Error(data.error || 'Failed to request access');
      
      showErr('reg-err', 'Success! Your request is pending admin approval.');
      document.getElementById('reg-err').style.color = '#00FFB3';
      document.getElementById('reg-err').style.background = 'rgba(0, 255, 179, 0.1)';
      document.getElementById('reg-err').style.borderColor = 'rgba(0, 255, 179, 0.2)';
    } catch(e) {
      showErr('reg-err', e.message || 'Failed');
      btn.disabled=false;btn.textContent='Request Access';
    }
  }
  """
    html = html.replace(old_reg_actual, new_reg)

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
