import os
import glob
import re
import json

frontend_dir = 'frontend'
html_files = glob.glob(os.path.join(frontend_dir, '*.html'))
print(f"Total HTML files found: {len(html_files)}")

broken_links = set()
empty_links = []
onclick_handlers = []

# Map of existing files and routes
existing_files = set(os.listdir(frontend_dir))
if os.path.exists('frontend/use-cases'):
    for uc in os.listdir('frontend/use-cases'):
        existing_files.add(f"use-cases/{uc}")

# Load vercel.json if exists to know rewrites/routes
routes = {}
if os.path.exists(os.path.join(frontend_dir, 'vercel.json')):
    try:
        with open(os.path.join(frontend_dir, 'vercel.json'), 'r') as vf:
            vdata = json.load(vf)
            for rw in vdata.get('rewrites', []):
                src = rw.get('source', '')
                dest = rw.get('destination', '')
                routes[src] = dest
    except Exception as e:
        print("Vercel parse error:", e)

print(f"Vercel rewrites found: {len(routes)}")

for fpath in html_files:
    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    fname = os.path.basename(fpath)
    
    # 1. Check hrefs
    hrefs = re.findall(r'href=[\"\'](.*?)[\"\']', content)
    for h in hrefs:
        if h == '#' or h == '':
            empty_links.append((fname, h))
        elif h.startswith('/') and not h.startswith('//'):
            clean_h = h.split('?')[0].split('#')[0]
            if clean_h.endswith('/'):
                clean_h = clean_h[:-1]
            if clean_h and clean_h != '':
                target_html = clean_h.lstrip('/') + '.html'
                target_direct = clean_h.lstrip('/')
                
                # Check if matches any rewrite or direct file
                found = False
                if target_html in existing_files or target_direct in existing_files:
                    found = True
                elif clean_h.startswith('/v1') or clean_h.startswith('/api'):
                    found = True
                elif clean_h in routes or ('/' + target_direct) in routes:
                    found = True
                
                if not found:
                    broken_links.add((fname, h))

print(f"Empty/placeholder '#' links count: {len(empty_links)}")
for el in empty_links[:15]:
    print(f"  Placeholder link in {el[0]}: {el[1]}")

print(f"\nBroken internal links count: {len(broken_links)}")
for bl in sorted(broken_links):
    print(f"  BROKEN LINK in {bl[0]} -> {bl[1]}")
