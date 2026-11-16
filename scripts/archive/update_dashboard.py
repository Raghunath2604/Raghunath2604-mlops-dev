import re
import os

path = "c:/Users/raghu/Downloads/mlopsdev-phase1-launch/mlops-dev/frontend/dashboard.html"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add Billing Tab to STNAV
stnav_billing = """            <div class="stnav-item active" onclick="showSTab('profile',this)"><svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>Profile</div>
            <div class="stnav-item" onclick="showSTab('api',this)"><svg viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>API & SDK</div>
            <div class="stnav-item" onclick="showSTab('billing',this)"><svg viewBox="0 0 24 24"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>Billing</div>"""
content = re.sub(
    r'<div class="stnav-item active" onclick="showSTab\(\'profile\',this\)">.*?</div>\s*<div class="stnav-item" onclick="showSTab\(\'api\',this\)">.*?</div>',
    stnav_billing,
    content,
    flags=re.DOTALL
)

# 2. Add Billing panel next to stab-api
stab_billing = """            <div id="stab-api" style="display:none">
              <h3>API & SDK</h3>
              <div class="setting-row"><div><div class="stlabel">API base URL</div><div class="stdesc">Use in your SDK config</div></div></div>
              <input class="st-inp" style="width:100%;margin-bottom:1rem" value="https://api.mlopsde.me/api" readonly/>
              <div class="setting-row"><div><div class="stlabel">API Key</div><div class="stdesc">Keep this secret</div></div><button class="tb-btn primary" onclick="generateApiKey()">Regenerate Key</button></div>
              <input id="api-key-display" class="st-inp" style="width:100%;margin-bottom:1rem;background:#0d1117" value="••••••••••••••••" readonly/>
              <div class="setting-row"><div><div class="stlabel">Agent install (Linux ARM)</div><div class="stdesc">Run on your edge device</div></div></div>
              <input class="st-inp" style="width:100%;font-size:.72rem;margin-bottom:1rem" value="curl -fsSL https://get.mlops.dev | sh" readonly/>
              <div class="setting-row"><div><div class="stlabel">Python SDK</div><div class="stdesc">pip install mlops-dev-sdk</div></div><button class="tb-btn primary" onclick="navigator.clipboard.writeText('pip install mlops-dev-sdk').then(()=>showToast('Copied!'))">Copy</button></div>
            </div>
            
            <div id="stab-billing" style="display:none">
              <h3>Billing & Usage</h3>
              <div class="setting-row" style="margin-bottom:1rem;"><div><div class="stlabel">Current Plan</div><div class="stdesc" id="b-plan">Free Tier</div></div></div>
              <div class="kpi-row" style="grid-template-columns:1fr; margin-bottom: 2rem;">
                <div class="kpi" style="padding:1rem;">
                  <div class="kpi-lbl">Device Usage</div>
                  <div class="kpi-val" id="b-usage" style="font-size:1.5rem;">0 / 10</div>
                  <div class="kpi-sub">Active devices this month</div>
                </div>
              </div>
              <div style="display:flex; gap:1rem;">
                <button class="btn-full" style="background:#5B8AF0; width:auto; padding:.5rem 1.3rem;" onclick="upgradePlan()">Upgrade to Team</button>
                <button class="btn-full" style="background:#2d333b; border:1px solid #444c56; width:auto; padding:.5rem 1.3rem;" onclick="openCustomerPortal()">Manage Billing (Stripe)</button>
              </div>
            </div>"""
content = re.sub(
    r'<div id="stab-api" style="display:none">.*?</div>\s*<div id="stab-notifs"',
    stab_billing + '\n            <div id="stab-notifs"',
    content,
    flags=re.DOTALL
)

# 3. Add Onboarding Checklist
onboarding_html = """        <div class="page active" id="page-overview">
        <div class="kpi-row">
          <div class="kpi"><div class="kpi-lbl"><svg viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/></svg>Total Devices</div><div class="kpi-val violet" id="k-total">—</div><div class="kpi-sub">in fleet</div></div>
          <div class="kpi"><div class="kpi-lbl"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M8 12l3 3 5-5"/></svg>Online</div><div class="kpi-val teal" id="k-online">—</div><div class="kpi-sub kpi-trend-up" id="k-hp">—% fleet health</div></div>
          <div class="kpi"><div class="kpi-lbl"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>Offline</div><div class="kpi-val red" id="k-offline">—</div><div class="kpi-sub" id="k-updating">— updating</div></div>
          <div class="kpi"><div class="kpi-lbl"><svg viewBox="0 0 24 24"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>High Drift</div><div class="kpi-val amber" id="k-drift">—</div><div class="kpi-sub">devices &gt;50% threshold</div></div>
        </div>
        
        <!-- ONBOARDING CHECKLIST -->
        <div class="panel" id="onboarding-panel" style="margin-bottom: 1.5rem; background: rgba(91, 138, 240, 0.1); border: 1px solid rgba(91, 138, 240, 0.3);">
          <div class="ph">
            <h3>🚀 Welcome to MLOps.dev! Get started here:</h3>
          </div>
          <div style="padding: 1rem 1.5rem;">
            <label style="display:flex; align-items:center; gap: 10px; margin-bottom: 8px;">
              <input type="checkbox" id="chk-api-key" disabled /> <span>1. Generate your API Key (Settings > API)</span>
            </label>
            <label style="display:flex; align-items:center; gap: 10px; margin-bottom: 8px;">
              <input type="checkbox" id="chk-register" disabled /> <span>2. Register your first device (<code>curl -fsSL https://get.mlops.dev | sh</code>)</span>
            </label>
            <label style="display:flex; align-items:center; gap: 10px;">
              <input type="checkbox" id="chk-deploy" disabled /> <span>3. Deploy your first model</span>
            </label>
          </div>
        </div>"""
content = re.sub(
    r'<div class="page active" id="page-overview">\s*<div class="kpi-row">.*?</div>',
    onboarding_html,
    content,
    flags=re.DOTALL
)

# 4. Modify apiFetch to use credentials and remove token
apiFetch_new = """async function apiFetch(path, opts={}) {
  const h = {'Content-Type':'application/json',...(opts.headers||{})};
  const res = await fetch(API+path, {...opts, headers:h, credentials: 'include'});
  const d = await res.json().catch(()=>({}));
  if (!res.ok) throw Object.assign(new Error(d.error||'Failed'),{status:res.status});
  return d;
}"""
content = re.sub(
    r'async function apiFetch\(path, opts=\{\}\) \{.*?\n\}',
    apiFetch_new,
    content,
    flags=re.DOTALL
)

# 5. Modify doLogin
doLogin_new = """async function doLogin() {
  clearErr('login-err');
  const pw=document.getElementById('li-pw').value.trim();
  if(!pw){showErr('login-err','API Key required');return;}
  const btn=document.getElementById('li-btn');
  btn.disabled=true;btn.textContent='Verifying...';
  try {
    const resp = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({key: pw}),
      credentials: 'include'
    });
    const data = await resp.json();
    if(!resp.ok) throw new Error(data.error);
    
    const user = {name: data.user.email, email: data.user.email, role: data.user.tier};
    localStorage.setItem('np_user', JSON.stringify(user));
    bootApp(user);
  } catch(e){
    showErr('login-err','Invalid API Key or Not Approved');
    btn.disabled=false;btn.textContent='Access Dashboard →';
  }
}"""
content = re.sub(
    r'async function doLogin\(\) \{.*?\}\n\}',
    doLogin_new,
    content,
    flags=re.DOTALL
)

# 6. Modify doLogout
doLogout_new = """async function doLogout() {
  await fetch(`${API}/auth/logout`, {method: 'POST', credentials: 'include'});
  localStorage.removeItem('np_user');
  if(sseSource){sseSource.close();sseSource=null;}
  document.getElementById('app').classList.remove('on');
  document.getElementById('auth-screen').style.display='flex';
}"""
content = re.sub(
    r'function doLogout\(\) \{.*?\n\}',
    doLogout_new,
    content,
    flags=re.DOTALL
)

# 7. Modify startSSE
startSSE_new = """function startSSE() {
  if(sseSource)return;
  sseSource=new EventSource(`${API}/fleet/stream`, {withCredentials: true});
  sseSource.onmessage=e=>{
    try{
      const d=JSON.parse(e.data);
      if(d.type==='fleet_update'){
        document.querySelectorAll('.live-chip-dot').forEach(dot=>{dot.style.opacity='.2';setTimeout(()=>dot.style.opacity='1',150);});
      }
    } catch{}
  };
  sseSource.onerror=()=>{if(sseSource){sseSource.close();sseSource=null;}};
  setInterval(refreshAll, 30000);
}"""
content = re.sub(
    r'function startSSE\(\) \{.*?\n\}',
    startSSE_new,
    content,
    flags=re.DOTALL
)

# 8. Add JS for billing and API generation, checkAuth at bottom
billing_js = """
async function upgradePlan() {
  try {
    const res = await fetch(`${API.replace('/v1','')}/v1/billing/checkout`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({plan: 'team'}),
      credentials: 'include'
    });
    const data = await res.json();
    if(data.url) window.location.href = data.url;
    else showToast(data.error || 'Failed to start checkout', 'err');
  } catch(e) { showToast('Network error', 'err'); }
}

async function openCustomerPortal() {
  try {
    const res = await fetch(`${API.replace('/v1','')}/v1/billing/portal`, {
      method: 'POST',
      credentials: 'include'
    });
    const data = await res.json();
    if(data.url) window.location.href = data.url;
    else showToast(data.error || 'Failed to open portal', 'err');
  } catch(e) { showToast('Network error', 'err'); }
}

async function generateApiKey() {
  if(!confirm('Are you sure? Your old API key will be invalidated.')) return;
  try {
    const res = await fetch(`${API}/keys/generate`, {
      method: 'POST',
      credentials: 'include'
    });
    const data = await res.json();
    if(data.key) {
      document.getElementById('api-key-display').value = data.key;
      showToast('API Key generated successfully! Please save it.');
    } else {
      showToast(data.error || 'Failed to generate key', 'err');
    }
  } catch(e) { showToast('Network error', 'err'); }
}

async function checkAuth() {
  try {
    const resp = await fetch(`${API}/auth/me`, {credentials: 'include'});
    if(!resp.ok) throw new Error('Unauth');
    const data = await resp.json();
    const user = {name: data.user.email, email: data.user.email, role: data.user.tier};
    localStorage.setItem('np_user', JSON.stringify(user));
    bootApp(user);
  } catch(e) {
    document.getElementById('app').classList.remove('on');
    document.getElementById('auth-screen').style.display='flex';
  }
}
checkAuth();
"""
# Replace boot loading section
content = re.sub(
    r'const _token=localStorage\.getItem\(\'np_token\'\);\nconst _user.*?bootApp\(_user\);\n\} else \{.*?\n\}',
    billing_js,
    content,
    flags=re.DOTALL
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated successfully")
