import re

with open("dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Add Leaflet CSS and JS to head
html = html.replace('</head>', 
    '  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />\n'
    '  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>\n</head>')

# 2. Add Modal HTML to the body (right after <body>)
modal_html = """
<!-- DEVICE MODAL -->
<div id="device-modal" class="modal-overlay" onclick="if(event.target===this)closeModal()">
  <div class="modal-content glass">
    <div class="modal-header">
      <h2 id="mod-title">Device Name</h2>
      <button class="act-btn del" onclick="closeModal()">×</button>
    </div>
    <div class="modal-body">
      <div class="mod-grid">
        <div class="mod-card">
          <div class="mod-lbl">CPU Usage</div>
          <div class="mod-val" id="mod-cpu">--%</div>
        </div>
        <div class="mod-card">
          <div class="mod-lbl">RAM Usage</div>
          <div class="mod-val" id="mod-ram">-- MB</div>
        </div>
        <div class="mod-card">
          <div class="mod-lbl">Temperature</div>
          <div class="mod-val" id="mod-temp">-- °C</div>
        </div>
        <div class="mod-card">
          <div class="mod-lbl">Latency</div>
          <div class="mod-val" id="mod-lat">-- ms</div>
        </div>
      </div>
      <div style="margin-top: 1rem;">
        <div class="mod-lbl">Status</div>
        <div id="mod-status" style="margin-top:0.3rem;">--</div>
      </div>
    </div>
  </div>
</div>
"""
html = html.replace('<body>', f'<body>\n{modal_html}')

# 3. Add Map container next to the Chart
map_html = """
          </div>
          <!-- MAP PANEL -->
          <div class="panel" style="margin-bottom: 1.5rem; position: relative;">
            <div class="ph"><h3>Global Edge Fleet</h3></div>
            <div id="fleet-map" style="height: 300px; width: 100%; border-radius: 8px; z-index: 1;"></div>
          </div>
          <div class="two-col">
"""
html = html.replace("          </div>\n          <div class=\"two-col\">", map_html)

# 4. Modify table rows to have an onclick event to open modal
html = html.replace(
    "<td class=\"td-name\">${d.name}</td>",
    "<td class=\"td-name\" style=\"cursor:pointer; text-decoration:underline;\" onclick=\"openModal('${d.id}')\">${d.name}</td>"
)

# 5. Add Leaflet map logic and Modal JS
js_code = """
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
    
    circle.bindTooltip(`<b>${d.name}</b><br>${d.status}`);
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
"""
html = html.replace("// --- END CHART ---", "// --- END CHART ---\n" + js_code)

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
