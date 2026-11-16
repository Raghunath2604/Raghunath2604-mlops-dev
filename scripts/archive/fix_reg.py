import re

with open("dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

reg_start = "async function doRegister() {"
reg_end = "async function doDeploy() {"
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
      btn.disabled=false;btn.textContent='Request Access';
    }
  }
  
  """
    html = html.replace(old_reg_actual, new_reg)

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
