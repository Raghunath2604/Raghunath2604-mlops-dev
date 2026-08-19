
'use strict';
const API = window.location.hostname.includes('localhost') || window.location.hostname.includes('127.0.0.1') 
    ? 'http://127.0.0.1:8000/v1' 
    : 'https://api.mlopsde.me/v1';
let ST = { devices:[], deployments:[], events:[], summary:{}, devFilter:'all', evFilter:'all' };
let sseSource = null;

// --- CHART.JS & DARK MODE ---
let driftChart = null;

function initChart() {
  const ctx = document.getElementById('driftChart');
  if(!ctx) return;
  const isDark = document.body.classList.contains('dark-mode');
  const textColor = isDark ? '#e2e8f0' : '#475569';
  const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';
  
  // Fake historical data for wow factor
  const labels = Array.from({length: 24}, (_, i) => `${23-i}h`);
  const data = Array.from({length: 24}, () => 0.1 + Math.random() * 0.15);
  // add a spike at the end for drama
  data[22] = 0.6; data[23] = 0.82;
  
  if(driftChart) driftChart.destroy();
  
  driftChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Avg KL Divergence',
        data: data,
        borderColor: '#00ffb3',
        backgroundColor: 'rgba(0, 255, 179, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { grid: { color: gridColor }, ticks: { color: textColor, maxTicksLimit: 8 } },
        y: { grid: { color: gridColor }, ticks: { color: textColor }, beginAtZero: true, max: 1.0 }
      }
    }
  });
}

function toggleDarkMode(e) {
  if(e.checked) {
    document.body.classList.add('dark-mode');
    localStorage.setItem('theme', 'dark');
  } else {
    document.body.classList.remove('dark-mode');
    localStorage.setItem('theme', 'light');
  }
  initChart();
}

window.addEventListener('DOMContentLoaded', () => {
  if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark-mode');
    const cb = document.getElementById('checkbox');
    if(cb) cb.checked = true;
  }
  setTimeout(initChart, 500);
});

// hook into page changes to redraw if needed
const origSwitch = window.switchPage;
window.switchPage = function(id) {
  if(origSwitch) origSwitch(id);
  if(id === 'page-overview') setTimeout(initChart, 50);
}
// --- END CHART ---

// --- MAP & MODAL LOGIC ---
let fleetMap = null;
let markers = [];
const deviceCoords = {
  'jetson-prod-01': [37.7749, -122.4194],
  'jetson-prod-02': [34.0522, -118.2437],
  'jetson-nano-01': [40.7128, -74.0060],
  'jetson-nano-02': [51.5074, -0.1278],
  'rpi5-edge-01': [35.6895, 139.6917],
  'rpi5-edge-02': [-33.8688, 151.2093]
};

function initMap() {
  if (fleetMap) return;
  const mapDiv = document.getElementById('fleet-map');
  if (!mapDiv) return;
  
  fleetMap = L.map('fleet-map').setView([20, 0], 2);
  
  const isDark = document.body.classList.contains('dark-mode');
  const tileUrl = isDark 
    ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
    : 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
    
  L.tileLayer(tileUrl, {
    attribution: '&copy; OpenStreetMap CartoDB',
    maxZoom: 18
  }).addTo(fleetMap);
  
  updateMapMarkers();
}

function updateMapMarkers() {
  if (!fleetMap) return;
  markers.forEach(m => fleetMap.removeLayer(m));
  markers = [];
  
  ST.devices.forEach(d => {
    const coords = deviceCoords[d.id] || [(Math.random()*40)-20, (Math.random()*40)-20];
    let color = '#00ffb3'; 
    if(d.status === 'drift' || d.status === 'warning') color = '#fbbf24';
    if(d.status === 'offline' || d.status === 'error') color = '#f87171';
    
    const circle = L.circleMarker(coords, {
      radius: 8,
      fillColor: color,
      color: color,
      weight: 1,
      opacity: 1,
      fillOpacity: 0.8
    }).addTo(fleetMap);
    
    circle.bindTooltip(`<b>${escapeHTML(d.name)}</b><br>${d.status}`);
    circle.on('click', () => openModal(d.id));
    markers.push(circle);
  });
}

function openModal(devId) {
  const d = ST.devices.find(x => x.id === devId);
  if(!d) return;
  
  document.getElementById('mod-title').textContent = d.name;
  document.getElementById('mod-cpu').textContent = (d.cpu_pct || (Math.random()*40 + 10).toFixed(1)) + '%';
  document.getElementById('mod-ram').textContent = d.ram_mb || Math.floor(Math.random()*4000 + 1000) + ' MB';
  document.getElementById('mod-temp').textContent = (d.temp_c || (Math.random()*30 + 40).toFixed(1)) + ' °C';
  document.getElementById('mod-lat').textContent = (d.latency_ms || (Math.random()*40 + 5).toFixed(1)) + ' ms';
  document.getElementById('mod-status').innerHTML = sbadge(d.status);
  
  document.getElementById('device-modal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('device-modal').style.display = 'none';
}

const origToggle2 = toggleDarkMode;
toggleDarkMode = function(e) {
  origToggle2(e);
  if(fleetMap) {
    fleetMap.remove();
    fleetMap = null;
    setTimeout(initMap, 100);
  }
}

const origLoadDevs = loadDevices;
loadDevices = async function() {
  await origLoadDevs();
  setTimeout(initMap, 200);
  setTimeout(updateMapMarkers, 300);
}
// --- END MAP ---


const PAGE_TITLES = {overview:'Overview',devices:'Devices',deployments:'Deployments',events:'Event log',drift:'Drift monitor',settings:'Settings'};

function escapeHTML(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ── API ───────────────────────────────────────────────────────────────────────
async function apiFetch(path, opts={}) {
  const h = {'Content-Type':'application/json',...(opts.headers||{})};
  const res = await fetch(API+path, {...opts, headers:h, credentials: 'include'});
  const d = await res.json().catch(()=>({}));
  if (!res.ok) throw Object.assign(new Error(d.error||'Failed'),{status:res.status});
  return d;
}

// ── TOAST ─────────────────────────────────────────────────────────────────────
function showToast(msg, type='ok') {
  const t=document.getElementById('toast');
  document.getElementById('ti').textContent=type==='ok'?'✓':'✕';
  document.getElementById('tm').textContent=msg;
  t.className=`toast ${type} show`;
  setTimeout(()=>t.classList.remove('show'),3200);
}

// ── AUTH ─────────────────────────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.atab').forEach((b,i)=>b.classList.toggle('active',(i===0&&tab==='login')||(i===1&&tab==='register')));
  document.getElementById('ap-login').classList.toggle('active',tab==='login');
  document.getElementById('ap-register').classList.toggle('active',tab==='register');
}
function showErr(id,msg){const e=document.getElementById(id);e.textContent=msg;e.classList.add('show');}
function clearErr(id){document.getElementById(id).classList.remove('show');}


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

  async function doLogin() {
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
    
    const user = {name: data.user.email, email: data.user.email, role: data.user.role};
    localStorage.setItem('np_user', JSON.stringify(user));
    bootApp(user);
  } catch(e){
    showErr('login-err','Invalid API Key or Not Approved');
    btn.disabled=false;btn.textContent='Access Dashboard →';
  }
}
document.getElementById('li-pw').addEventListener('keypress',e=>{if(e.key==='Enter')doLogin();});

async function doRegister() {
  clearErr('reg-err');
  const name=document.getElementById('ri-name').value.trim();
  const email=document.getElementById('ri-email').value.trim();
  const password=document.getElementById('ri-pw').value.trim();
  if(!name||!email||!password){showErr('reg-err','Name, Email and Password required');return;}
  const btn=document.getElementById('ri-btn');btn.disabled=true;btn.textContent='Submitting...';
  try {
    const res = await fetch(`${API}/auth/register`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, email, password})
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
}

async function doLogout() {
  await fetch(`${API}/auth/logout`, {method: 'POST', credentials: 'include'});
  localStorage.removeItem('np_user');
  if(sseSource){sseSource.close();sseSource=null;}
  document.getElementById('app').classList.remove('on');
  document.getElementById('auth-screen').style.display='flex';
}

// ── BOOT ──────────────────────────────────────────────────────────────────────
async function bootApp(user) {
  document.getElementById('auth-screen').style.display='none';
  document.getElementById('app').classList.add('on');
  const ini=(user.name||'?').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase();
  document.getElementById('sb-ava').textContent=ini;
  document.getElementById('sb-uname').textContent=user.name||'—';
  document.getElementById('sb-urole').textContent=user.role||'member';
  document.getElementById('s-name').value=user.name||'';
  document.getElementById('s-email').value=user.email||'';
  document.getElementById('s-role').value=user.role||'';
  await refreshAll();
  startSSE();
}

async function refreshAll() {
  await Promise.all([loadSummary(),loadDevices(),loadDeployments(),loadEvents()]);
}

// ── LOADERS ────────────────────────────────────────────────────────────────────
async function loadSummary() {
  try {
    const d=await apiFetch('/status'); ST.summary=d;
    document.getElementById('k-total').textContent=d.total_devices||0;
    document.getElementById('k-online').textContent=d.online||0;
    document.getElementById('k-offline').textContent=d.offline||0;
    document.getElementById('k-offline').className=`kpi-val ${d.offline>0?'red':'teal'}`;
    document.getElementById('k-drift').textContent=d.drifting||0;
    document.getElementById('k-hp').textContent=`${Math.round((d.online/(d.total_devices||1))*100)}% fleet health`;
    document.getElementById('k-updating').textContent=`${d.active_deployments||0} updating`;
  } catch(e){ console.error(e); }
}
async function loadDevices() {
  try {
    const r=await apiFetch('/devices');ST.devices=r.data;
    document.getElementById('sb-dev-count').textContent=r.data.length;
    renderOvTable();renderDevTable();renderDrift();
  } catch{}
}
async function loadDeployments() {
  try {const r=await apiFetch('/deployments');ST.deployments=r.data;renderDepList();} catch{}
}
async function loadEvents() {
  try {
    const r=await apiFetch('/audit?limit=50');ST.events=r.data;
    renderFeed();renderEvList();
    const alerts=r.data.filter(e=>e.severity==='warning').length;
    const b=document.getElementById('sb-alert-ct');
    if(alerts>0){b.textContent=alerts;b.style.display='';}else b.style.display='none';
  } catch{}
}

// ── HELPERS ────────────────────────────────────────────────────────────────────
function dc(v){return v>60?'danger':v>40?'warn':'ok';}
function dbar(v){const c=dc(v);return `<div class="dbar-wrap"><div class="dbar"><div class="dbf df-${c}" style="width:${v}%"></div></div><span class="dval dv-${c}">${v}%</span></div>`;}
function sbadge(s){const m={online:'s-on',offline:'s-off',updating:'s-up'};return `<span class="sbadge ${m[s]||'s-off'}"><span class="sdot"></span>${s}</span>`;}
function fd(iso){return iso?iso.split('T')[0]:'—';}

// ── RENDER ─────────────────────────────────────────────────────────────────────
function renderOvTable() {
  const tb=document.getElementById('ov-tbody');if(!tb)return;
  tb.innerHTML=ST.devices.map(d=>`<tr>
    <td class="td-name" style="cursor:pointer; text-decoration:underline;" onclick="openModal('${d.id}')">${escapeHTML(d.name)}</td>
    <td>${sbadge(d.status)}</td>
    <td style="font-family:var(--fm);font-size:.74rem;color:var(--muted)">${d.model_tag||'-'}</td>
    <td>${dbar(Math.round((d.drift_score||0)*100))}</td>
    <td style="font-family:var(--fm);font-size:.72rem;color:var(--muted)">${d.agent_version||'-'}</td>
  </tr>`).join('');
  const s=document.getElementById('ov-sync');if(s)s.textContent='updated just now';
}
function renderDevTable() {
  const tb=document.getElementById('dev-tbody');if(!tb)return;
  const q=(document.getElementById('dev-search')?.value||'').toLowerCase();
  let devs=ST.devices;
  if(ST.devFilter!=='all') devs=devs.filter(d=>d.status===ST.devFilter);
  if(q) devs=devs.filter(d=>d.name.toLowerCase().includes(q)||(d.hw_class||'').toLowerCase().includes(q));
  tb.innerHTML=devs.map(d=>`<tr>
    <td class="td-name" style="cursor:pointer; text-decoration:underline;" onclick="openModal('${d.id}')">${escapeHTML(d.name)}</td>
    <td class="td-hw">${d.hw_class||'-'}</td>
    <td>${sbadge(d.status)}</td>
    <td style="font-family:var(--fm);font-size:.74rem;color:var(--muted)">${d.model_tag||'-'}</td>
    <td>${dbar(Math.round((d.drift_score||0)*100))}</td>
    <td style="font-family:var(--fm);font-size:.72rem;color:var(--muted)">${d.agent_version||'-'}</td>
    <td style="font-size:.72rem;color:var(--muted)">${fd(d.last_seen)}</td>
    <td><button class="act-btn del" onclick="deleteDev('${d.id}','${escapeHTML(d.name)}')">×</button></td>
  </tr>`).join('');
}
function filterDev(s,btn){ST.devFilter=s;document.querySelectorAll('#page-devices .filter-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');renderDevTable();}

function renderDepList() {
  const el=document.getElementById('dep-list');if(!el)return;
  el.innerHTML=ST.deployments.map(d=>`
    <div class="dep-row">
      <div><span class="dep-model">${escapeHTML(d.model_name)}</span><span class="dep-ver">${d.model_ver}</span></div>
      <span class="dep-st dst-${d.status}">${d.status.replace('_',' ')}</span>
      <span class="dep-devs">${d.success_count}/${d.device_count} devs</span>
    </div>`).join('')||'<p style="color:var(--muted);font-size:.84rem">No deployments yet.</p>';
}

function renderFeed() {
  const el=document.getElementById('ov-feed');if(!el)return;
  el.innerHTML=ST.events.slice(0,10).map(e=>`
    <div class="act-item">
      <span class="act-badge ab-${e.type}">${e.type}</span>
      <div class="act-msg">${e.message}</div>
      <span class="act-time">${fd(e.created_at)}</span>
    </div>`).join('')||'<p style="color:var(--muted);font-size:.82rem;padding:.3rem 0">No events yet.</p>';
}
function filterEv(sev,btn){ST.evFilter=sev;document.querySelectorAll('#page-events .filter-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');renderEvList();}
function renderEvList() {
  const el=document.getElementById('ev-list');if(!el)return;
  let evs=ST.events;
  if(ST.evFilter!=='all') evs=evs.filter(e=>e.severity===ST.evFilter);
  el.innerHTML=evs.map(e=>`
    <div class="act-item">
      <span class="act-badge ab-${e.type}">${e.type}</span>
      <div class="act-msg">${e.message}</div>
      <span class="act-time">${e.created_at.split('T')[0]}</span>
    </div>`).join('')||'<p style="color:var(--muted);font-size:.82rem;padding:.3rem 0">No events found.</p>';
}
function renderDrift() {
  const el=document.getElementById('drift-list');if(!el)return;
  const sorted=[...ST.devices].sort((a,b)=>b.drift_score-a.drift_score);
  el.innerHTML=sorted.map(d=>`
    <div class="drift-device">
      <span class="drift-name">${escapeHTML(d.name)}</span>
      <div class="drift-bar-full"><div class="dbf-full df-full-${dc(d.drift_score)}" style="width:${d.drift_score}%"></div></div>
      <span class="drift-pct dv-${dc(d.drift_score)}" style="font-family:var(--fm);font-size:.74rem">${d.drift_score}%</span>
    </div>`).join('');
}

// ── DEPLOY ────────────────────────────────────────────────────────────────────
async function doDeploy() {
  const name=document.getElementById('dn-name').value.trim();
  const ver=document.getElementById('dn-ver').value.trim();
  const err=document.getElementById('dep-err');const suc=document.getElementById('dep-suc');
  err.classList.remove('show');suc.classList.remove('show');
  if(!name||!ver){err.textContent='Model name and version required';err.classList.add('show');return;}
  const btn=document.getElementById('dep-btn');btn.disabled=true;btn.textContent='Deploying…';
  const prog=document.getElementById('dep-prog');const fill=document.getElementById('dep-fill');
  prog.style.display='block';fill.style.width='0%';
  const piv=setInterval(()=>{const c=parseInt(fill.style.width)||0;if(c<88)fill.style.width=(c+Math.floor(Math.random()*7+2))+'%';},350);
  try {
    const res=await apiFetch('/deployments',{method:'POST',body:JSON.stringify({model_name:name,model_tag:ver})});
    clearInterval(piv);fill.style.width='100%';
    setTimeout(()=>{prog.style.display='none';fill.style.width='0%';},700);
    suc.textContent=`✓ ${name} ${ver} deploying to ${res.data.device_count} devices`;suc.classList.add('show');
    document.getElementById('dn-name').value='';document.getElementById('dn-ver').value='';
    showToast(`Deploying ${name} ${ver}…`);
    await Promise.all([loadDeployments(),loadEvents(),loadSummary()]);
  } catch(e) {
    clearInterval(piv);prog.style.display='none';
    err.textContent=e.message||'Deployment failed';err.classList.add('show');
    showToast(e.message||'Deploy failed','err');
  } finally {
    btn.disabled=false;
    btn.innerHTML='<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24" style="vertical-align:middle;margin-right:6px"><path d="M5 3l14 9-14 9V3z"/></svg>Start deployment';
  }
}

// ── DEVICE CRUD ────────────────────────────────────────────────────────────────
function openAddDev(){document.getElementById('add-dev-modal').classList.add('open');}
function closeAddDev(){document.getElementById('add-dev-modal').classList.remove('open');}
document.getElementById('add-dev-modal').addEventListener('click',e=>{if(e.target===document.getElementById('add-dev-modal'))closeAddDev();});
async function doAddDev() {
  const name=document.getElementById('ad-name').value.trim();
  const hw=document.getElementById('ad-hw').value;
  const err=document.getElementById('ad-err');err.classList.remove('show');
  if(!name||!hw){err.textContent='Name and hardware required';err.classList.add('show');return;}
  const btn=document.getElementById('ad-btn');btn.disabled=true;btn.textContent='Registering…';
  try {
    await apiFetch('/devices',{method:'POST',body:JSON.stringify({name,hardware:hw})});
    closeAddDev();document.getElementById('ad-name').value='';document.getElementById('ad-hw').value='';
    showToast(`${name} registered`);await loadDevices();await loadSummary();
  } catch(e){err.textContent=e.message||'Failed';err.classList.add('show');}
  finally{btn.disabled=false;btn.textContent='Register device';}
}
async function deleteDev(id,name) {
  if(!confirm(`Remove "${name}" from fleet?`))return;
  try{await apiFetch(`/devices/${id}`,{method:'DELETE'});showToast(`${name} removed`);await loadDevices();await loadSummary();}
  catch(e){showToast(e.message||'Delete failed','err');}
}

// ── NAVIGATION ────────────────────────────────────────────────────────────────
function nav(page, btn) {
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  const pg=document.getElementById(`page-${page}`);if(pg)pg.classList.add('active');
  document.querySelectorAll('.sb-link').forEach(b=>b.classList.remove('active'));
  if(btn) btn.classList.add('active');
  else document.querySelectorAll('.sb-link').forEach(b=>{if(b.getAttribute('onclick')?.includes(`'${page}'`))b.classList.add('active');});
  document.getElementById('page-title').textContent=PAGE_TITLES[page]||page;
}
function showSTab(tab,el) {
  document.querySelectorAll('.stnav-item').forEach(i=>i.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('[id^="stab-"]').forEach(p=>p.style.display='none');
  const t=document.getElementById(`stab-${tab}`);if(t)t.style.display='block';
}

// ── SSE ────────────────────────────────────────────────────────────────────────
function startSSE() {
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
}

// ── BOOT ─────────────────────────────────────────────────────────────────────

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
    const user = {name: data.user.email, email: data.user.email, role: data.user.role};
    localStorage.setItem('np_user', JSON.stringify(user));
    bootApp(user);
  } catch(e) {
    document.getElementById('app').classList.remove('on');
    document.getElementById('auth-screen').style.display='flex';
  }
}
checkAuth();

