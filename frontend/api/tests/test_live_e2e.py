import socket
import threading
import time
import os
import sys
import requests
import pytest

BASE = "http://127.0.0.1:8000"

def is_server_running(host="127.0.0.1", port=8000):
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False

@pytest.fixture(scope="session", autouse=True)
def ensure_live_server():
    if not is_server_running():
        api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if api_dir not in sys.path:
            sys.path.insert(0, api_dir)
        os.environ["TESTING"] = "true"
        import index
        with index.app.app_context():
            index.init_db()
        server_thread = threading.Thread(
            target=lambda: index.app.run(host="127.0.0.1", port=8000, debug=False, use_reloader=False),
            daemon=True
        )
        server_thread.start()
        for _ in range(50):
            if is_server_running():
                break
            time.sleep(0.1)

@pytest.fixture(autouse=True)
def check_server():
    if not is_server_running():
        pytest.skip("Live server not running on http://127.0.0.1:8000")

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    return s

def test_static_pages(session):
    r_login = session.get(f"{BASE}/login")
    assert r_login.status_code == 200
    assert "Sign In" in r_login.text
    
    r_dash = session.get(f"{BASE}/dashboard")
    assert r_dash.status_code == 200
    assert "Fleet Dashboard" in r_dash.text

def test_otp_flow(session):
    # Send code
    r_send = session.post(f"{BASE}/v1/auth/send-code", json={"email": "pilot@mlops.dev"})
    assert r_send.status_code == 200
    data = r_send.json()
    assert data.get("success") is True
    code = data.get("code")
    assert code and len(code) == 6
    
    # Verify code
    r_ver = session.post(f"{BASE}/v1/auth/verify-code", json={"email": "pilot@mlops.dev", "code": code})
    assert r_ver.status_code == 200
    assert r_ver.json().get("success") is True
    assert "np_token" in session.cookies or "session" in r_ver.json()
    
    # Auth me
    r_me = session.get(f"{BASE}/v1/auth/me")
    assert r_me.status_code == 200
    assert r_me.json().get("user", {}).get("email") == "pilot@mlops.dev"

def test_oauth_providers(session):
    r_google = session.post(f"{BASE}/v1/auth/oauth/google", json={"name": "G Developer", "email": "gdev@mlops.dev"})
    assert r_google.status_code == 200
    assert r_google.json().get("success") is True
    
    r_github = session.post(f"{BASE}/v1/auth/oauth/github", json={"name": "GH Dev", "username": "gh_pilot"})
    assert r_github.status_code == 200
    assert r_github.json().get("success") is True

def test_simulation_lifecycle(session):
    # Start
    r_start = session.post(f"{BASE}/v1/simulation/start", json={"interval": 2.0})
    assert r_start.status_code == 200
    assert r_start.json().get("success") is True
    
    # Status
    r_stat = session.get(f"{BASE}/v1/simulation/status")
    assert r_stat.status_code == 200
    stat = r_stat.json()
    assert stat.get("running") is True
    assert stat.get("total_hardware_nodes", 0) >= 17
    
    # Inject Drift
    r_drift = session.post(f"{BASE}/v1/simulation/drift", json={"node": "jetson_nano", "score": 0.85})
    assert r_drift.status_code == 200
    assert r_drift.json().get("success") is True
    
    # Disconnect Node
    r_disc = session.post(f"{BASE}/v1/simulation/disconnect", json={"node": "rpi5", "offline": True})
    assert r_disc.status_code == 200
    assert r_disc.json().get("success") is True
    
    # Stop
    r_stop = session.post(f"{BASE}/v1/simulation/stop")
    assert r_stop.status_code == 200
    assert r_stop.json().get("success") is True
