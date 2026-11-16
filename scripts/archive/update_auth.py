import re

with open("dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Update Tabs
html = html.replace('switchTab(\'login\')">Sign in</button>', 'switchTab(\'login\')">Admin Access</button>')
html = html.replace('switchTab(\'register\')">Create account</button>', 'switchTab(\'register\')">Request Access</button>')

# 2. Update Login Form
html = html.replace('<div class="fg"><label>Password</label><input id="li-pw" type="password" placeholder="Password" autocomplete="current-password"/></div>',
                    '<div class="fg"><label>Admin API Key</label><input id="li-pw" type="password" placeholder="Enter API Key" autocomplete="current-password"/></div>')

html = html.replace('onclick="doLogin()">Sign in to dashboard', 'onclick="doLogin()">Access Dashboard')
html = html.replace('<p class="auth-hint">Demo: <strong>demo@nodepilot.dev</strong> / <strong>demo1234</strong></p>',
                    '<p class="auth-hint">Only approved admins can access the dashboard. Demo key: <strong>demo</strong></p>')

# 3. Update Register Form
# Replace the whole form-row2 + password field
old_reg = """<div class="form-row2">
          <div class="fg"><label>Name *</label><input id="ri-name" type="text" placeholder="Your name" autocomplete="name"/></div>
          <div class="fg"><label>Email *</label><input id="ri-email" type="email" placeholder="you@co.com" autocomplete="email"/></div>
        </div>
        <div class="fg"><label>Password * (min 8 chars)</label><input id="ri-pw" type="password" placeholder="Choose a password" autocomplete="new-password"/></div>
        <button class="btn-full" id="ri-btn" onclick="doRegister()">Create account"""

new_reg = """<div class="form-row2">
          <div class="fg"><label>Name *</label><input id="ri-name" type="text" placeholder="Your name" autocomplete="name"/></div>
          <div class="fg"><label>Email *</label><input id="ri-email" type="email" placeholder="you@co.com" autocomplete="email"/></div>
        </div>
        <div class="fg"><label>Company / Project (Optional)</label><input id="ri-pw" type="text" placeholder="Where will you use MLOps.dev?" autocomplete="off"/></div>
        <button class="btn-full" id="ri-btn" onclick="doRegister()">Request Access"""

# Remove invisible space characters to ensure match
def clean_html(h): return re.sub(r'>\s+<', '><', h)
if "ri-name" in html:
    # Just do a targeted regex replace for the register form area
    html = re.sub(
        r'<div class="form-row2">[\s\S]*?id="ri-btn" onclick="doRegister\(\)">Create account',
        new_reg,
        html
    )

# 4. Update JS logic
login_js_old = """async function doLogin() {
    clearErr('login-err');
    const email=document.getElementById('li-email').value.trim();
    const pw=document.getElementById('li-pw').value;
    if(!email||!pw){showErr('login-err','Email and password required');return;}
    const btn=document.getElementById('li-btn');
    btn.disabled=true;btn.textContent='Signing in...';
    try {
      await new Promise(r=>setTimeout(r,600)); const res = {data: {token: "demo", user: {name: "Raghunath", email: "demo@mlops.dev", role: "admin"}}};
      localStorage.setItem('np_token',res.data.token);
      localStorage.setItem('np_user',JSON.stringify(res.data.user));
      bootApp(res.data.user);
    } catch(e){showErr('login-err',e.message||'Invalid credentials');btn.disabled=false;btn.textContent='Sign in to dashboard →';}
  }"""
  
# wait, the original JS had 'Signing in\u2026' and 'Sign in to dashboard \u2192'
# Let's just regex replace the body of doLogin
login_js_new = """async function doLogin() {
    clearErr('login-err');
    const pw=document.getElementById('li-pw').value.trim();
    if(!pw){showErr('login-err','API Key is required');return;}
    const btn=document.getElementById('li-btn');
    btn.disabled=true;btn.textContent='Verifying...';
    try {
      localStorage.setItem('np_token', pw);
      await apiFetch('/status'); // Test the key
      const user = {name: "Admin", email: document.getElementById('li-email').value.trim(), role: "admin"};
      localStorage.setItem('np_user', JSON.stringify(user));
      bootApp(user);
    } catch(e){
      localStorage.removeItem('np_token');
      showErr('login-err', e.message||'Invalid API Key or Not Approved');
      btn.disabled=false;btn.textContent='Access Dashboard →';
    }
  }"""

html = re.sub(r'async function doLogin\(\) \{[\s\S]*?catch\(e\)\{[\s\S]*?\}\n  \}', login_js_new, html)

reg_js_new = """async function doRegister() {
    clearErr('reg-err');
    const name=document.getElementById('ri-name').value.trim();
    const email=document.getElementById('ri-email').value.trim();
    const source=document.getElementById('ri-pw').value.trim();
    if(!name||!email){showErr('reg-err','Name and Email required');return;}
    const btn=document.getElementById('ri-btn');btn.disabled=true;btn.textContent='Submitting...';
    try {
      // Fetch directly to the waitlist API, replace /v1/ with /api/
      const waitlistApiUrl = API.replace(/\/v1\/?$/, '/api/waitlist');
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
      btn.disabled=false;btn.textContent='Request Access →';
    }
  }"""
  
html = re.sub(r'async function doRegister\(\) \{[\s\S]*?catch\(e\)\{[\s\S]*?\}\n  \}', reg_js_new, html)

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
