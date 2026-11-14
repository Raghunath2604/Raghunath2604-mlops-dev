import sys
from pathlib import Path

# Add frontend/api to path
sys.path.insert(0, str(Path('.') / 'frontend' / 'api'))

from index import app, init_db

with app.app_context():
    init_db()

client = app.test_client()

html_pages = [
    '/', '/index.html', '/dashboard.html', '/login.html', '/admin.html',
    '/demo.html', '/docs.html', '/pricing.html', '/blog.html', '/about.html',
    '/careers.html', '/changelog.html', '/faq.html', '/benchmarks.html',
    '/compiler.html', '/vscode.html', '/status.html', '/roadmap.html',
    '/incidents.html', '/investors.html', '/playground.html', '/poster.html',
    '/privacy.html', '/terms.html', '/thankyou.html', '/api-reference.html',
    '/alerts.html'
]

print("=== Testing all static and rendered routes ===")
failed = []
for p in html_pages:
    resp = client.get(p)
    if resp.status_code not in (200, 302):
        print(f"FAILED [{resp.status_code}]: {p}")
        failed.append((p, resp.status_code))
    else:
        print(f"OK [{resp.status_code}]: {p} ({len(resp.data)} bytes)")

print(f"\nTotal tested: {len(html_pages)}, Failed: {len(failed)}")
