with open("index.css", "a", encoding="utf-8") as f:
    f.write("""

/* --- RESPONSIVE OVERRIDES --- */
@media(max-width: 820px) {
  .ph {
    flex-wrap: wrap;
    gap: 10px;
  }
  .panel > div {
    overflow-x: auto;
  }
  .ftable th, .ftable td {
    white-space: nowrap;
  }
}

@media(max-width: 500px) {
  .kpi-row {
    grid-template-columns: 1fr !important;
  }
  #fleet-map {
    height: 250px !important;
  }
  .theme-switch-wrapper em {
    display: none; /* Hide 'Dark Mode' text on very small screens to save space */
  }
  .mod-grid {
    grid-template-columns: 1fr !important;
  }
  .modal-content {
    padding: 15px;
  }
}
""")

with open("dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace('href="index.css?v=5"', 'href="index.css?v=6"')

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
