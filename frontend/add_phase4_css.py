with open("index.css", "a", encoding="utf-8") as f:
    f.write("""

/* --- MODAL --- */
.modal-overlay {
  display: none;
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(4px);
  z-index: 9999;
  justify-content: center;
  align-items: center;
}
.modal-content {
  background: #fff;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  padding: 20px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.2);
  transition: transform 0.3s ease;
}
body.dark-mode .modal-content {
  background: var(--bg-card);
  border: 1px solid var(--border);
  box-shadow: 0 10px 25px rgba(0,0,0,0.8);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 10px;
  margin-bottom: 15px;
}
body.dark-mode .modal-header {
  border-bottom: 1px solid var(--border);
}
.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
}
.mod-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}
.mod-card {
  background: #f8fafc;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}
body.dark-mode .mod-card {
  background: rgba(0,0,0,0.2);
  border: 1px solid var(--border);
}
.mod-lbl {
  font-size: 0.8rem;
  color: #64748b;
  text-transform: uppercase;
  font-weight: 600;
  margin-bottom: 5px;
}
body.dark-mode .mod-lbl {
  color: var(--muted);
}
.mod-val {
  font-size: 1.5rem;
  font-weight: 700;
  font-family: var(--fm);
}

/* Leaflet dark mode overrides */
body.dark-mode .leaflet-container {
  background: #0f172a;
}
""")
