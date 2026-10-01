import requests
import os

API_URL = "http://localhost:8000/v1"

# Login to get a token
res = requests.post(f"{API_URL}/auth/login", json={
    "email": "admin@mlops.dev",
    "password": "admin"
})

if res.status_code == 200:
    token = res.json().get("token")
    print(f"export API_KEY={token}")
else:
    print("Login failed:", res.text)
