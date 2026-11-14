import os, glob, re

html_files = glob.glob('frontend/*.html')

# Find all fetch/ajax endpoints called in frontend
fetch_pattern = re.compile(r'fetch\([`\'"]([^`\'"\$]+)[`\'"]')
ajax_pattern = re.compile(r'url:\s*[`\'"]([^`\'"\$]+)[`\'"]')

called_endpoints = set()
file_endpoint_map = {}

for f in html_files:
    fname = os.path.basename(f)
    with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
        c = fh.read()
    
    matches = fetch_pattern.findall(c) + ajax_pattern.findall(c)
    file_endpoint_map[fname] = matches
    for m in matches:
        if m.startswith(('/api', '/v1', 'http://localhost:8000', 'https://www.mlopsde.me', 'https://mlopsde.me')):
            called_endpoints.add((fname, m))

print(f"Total API calls found in HTML files: {len(called_endpoints)}")

# Now find all routes defined in frontend/api/index.py
with open('frontend/api/index.py', 'r', encoding='utf-8') as fh:
    api_code = fh.read()

route_pattern = re.compile(r'@app\.route\([\'"]([^\'"]+)[\'"]')
defined_routes = set(route_pattern.findall(api_code))

print(f"Total routes defined in index.py: {len(defined_routes)}")

# Check for mismatches
print("\n--- Route Availability Check ---")
for fname, endpoint in sorted(called_endpoints):
    # normalize endpoint
    clean_ep = endpoint.replace('http://localhost:8000', '').replace('https://www.mlopsde.me', '').replace('https://mlopsde.me', '')
    clean_ep = clean_ep.split('?')[0]
    
    # check if direct match or parameter match
    matched = False
    for r in defined_routes:
        r_regex = '^' + re.sub(r'<[^>]+>', '[^/]+', r) + '$'
        if re.match(r_regex, clean_ep):
            matched = True
            break
    if not matched:
        print(f"MISSING ENDPOINT: [{fname}] calls '{endpoint}' (clean: '{clean_ep}')")
