import requests

url = "http://127.0.0.1:8000/v1/auth/login"
payload = {"key": "demo"}
response = requests.post(url, json=payload)
print(response.status_code)
print(response.headers)
print(response.json())
