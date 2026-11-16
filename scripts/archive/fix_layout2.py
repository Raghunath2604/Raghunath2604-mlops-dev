import re

with open("dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# Insert Chart and Map
chart_and_map_html = """
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
          
          <!-- MAP PANEL -->
          <div class="panel" style="margin-bottom: 1.5rem; position: relative;">
            <div class="ph"><h3>Global Edge Fleet</h3></div>
            <div id="fleet-map" style="height: 300px; width: 100%; border-radius: 8px; z-index: 1;"></div>
          </div>
        <div class="two-col">"""

if "driftChart" not in html:
    # find the first <div class="two-col">
    html = html.replace('<div class="two-col">', chart_and_map_html, 1)
    
    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)
