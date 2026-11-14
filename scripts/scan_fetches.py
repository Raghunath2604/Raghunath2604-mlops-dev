import os, glob, re

html_files = glob.glob('frontend/*.html')

print("=== Scanning JavaScript fetch/endpoints in all HTML files ===")
all_endpoints = []
for f in html_files:
    fname = os.path.basename(f)
    with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
        lines = fh.readlines()
    for idx, line in enumerate(lines):
        if 'fetch(' in line or 'EventSource(' in line:
            # extract string
            all_endpoints.append((fname, idx+1, line.strip()))

print(f"Total fetch / EventSource lines found: {len(all_endpoints)}")
for ep in all_endpoints[:40]:
    print(f"  {ep[0]}:{ep[1]}  {ep[2][:100]}")
