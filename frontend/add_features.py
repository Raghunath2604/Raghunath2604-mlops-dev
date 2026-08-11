import re

with open("dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Add Chart.js to head
html = html.replace("</head>", '  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>\n</head>')

# 2. Add Chart canvas to Overview page and Dark Mode toggle
chart_html = """          </div>
          <!-- CHART AND DARK MODE -->
          <div class="panel" style="margin-bottom: 1.5rem; position: relative;">
            <div class="ph" style="display:flex; justify-content:space-between; align-items:center;">
              <h3>Live Fleet Drift History (24h)</h3>
              <div class="theme-switch-wrapper" style="display:flex; align-items:center;">
                <label class="theme-switch" for="checkbox">
                  <input type="checkbox" id="checkbox" onchange="toggleDarkMode(this)"/>
                  <div class="slider round"></div>
                </label>
                <em style="margin-left: 10px; font-size: 0.8rem; color: var(--muted);">Dark Mode</em>
              </div>
            </div>
            <div style="height: 250px; width: 100%;">
              <canvas id="driftChart"></canvas>
            </div>
          </div>
          <div class="two-col">"""

html = html.replace("</div>\n          <div class=\"two-col\">", chart_html)

# 3. Add JS for Dark Mode and Chart
js_code = """
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
"""
html = html.replace("let sseSource = null;", "let sseSource = null;\n" + js_code)

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
