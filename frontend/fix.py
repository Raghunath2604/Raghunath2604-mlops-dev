import re

with open("dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# Fix loadSummary
html = re.sub(
    r"async function loadSummary\(\) \{.*?\n\}",
    """async function loadSummary() {
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
}""",
    html,
    flags=re.DOTALL
)

# Fix renderOvTable
html = re.sub(
    r"function renderOvTable\(\) \{.*?\n\}",
    """function renderOvTable() {
  const tb=document.getElementById('ov-tbody');if(!tb)return;
  tb.innerHTML=ST.devices.map(d=>`<tr>
    <td class="td-name">${d.name}</td>
    <td>${sbadge(d.status)}</td>
    <td style="font-family:var(--fm);font-size:.74rem;color:var(--muted)">${d.model_tag||'-'}</td>
    <td>${dbar(Math.round((d.drift_score||0)*100))}</td>
    <td style="font-family:var(--fm);font-size:.72rem;color:var(--muted)">${d.agent_version||'-'}</td>
  </tr>`).join('');
  const s=document.getElementById('ov-sync');if(s)s.textContent='updated just now';
}""",
    html,
    flags=re.DOTALL
)

# Fix renderDevTable
html = re.sub(
    r"function renderDevTable\(\) \{.*?\n\}",
    """function renderDevTable() {
  const tb=document.getElementById('dev-tbody');if(!tb)return;
  const q=(document.getElementById('dev-search')?.value||'').toLowerCase();
  let devs=ST.devices;
  if(ST.devFilter!=='all') devs=devs.filter(d=>d.status===ST.devFilter);
  if(q) devs=devs.filter(d=>d.name.toLowerCase().includes(q)||(d.hw_class||'').toLowerCase().includes(q));
  tb.innerHTML=devs.map(d=>`<tr>
    <td class="td-name">${d.name}</td>
    <td class="td-hw">${d.hw_class||'-'}</td>
    <td>${sbadge(d.status)}</td>
    <td style="font-family:var(--fm);font-size:.74rem;color:var(--muted)">${d.model_tag||'-'}</td>
    <td>${dbar(Math.round((d.drift_score||0)*100))}</td>
    <td style="font-family:var(--fm);font-size:.72rem;color:var(--muted)">${d.agent_version||'-'}</td>
    <td style="font-size:.72rem;color:var(--muted)">${fd(d.last_seen)}</td>
    <td><button class="act-btn del" onclick="deleteDev('${d.id}','${d.name}')">×</button></td>
  </tr>`).join('');
}""",
    html,
    flags=re.DOTALL
)

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
