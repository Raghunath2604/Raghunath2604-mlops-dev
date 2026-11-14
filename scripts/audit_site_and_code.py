import os, glob, re
from urllib.parse import urlparse

html_files = glob.glob('frontend/*.html')
print(f"Total HTML files found: {len(html_files)}")

# 1. Check all internal links and references
all_html_basenames = {os.path.basename(f) for f in html_files}
broken_links = []
href_pattern = re.compile(r'href=["\']([^"\']+)["\']')
src_pattern = re.compile(r'src=["\']([^"\']+)["\']')

for f in html_files:
    fname = os.path.basename(f)
    with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
        content = fh.read()
    
    # Check hrefs
    for href in href_pattern.findall(content):
        href_clean = href.split('#')[0].split('?')[0].strip()
        if not href_clean or href.startswith(('http://', 'https://', 'mailto:', 'tel:', 'javascript:', '#', 'data:')):
            continue
        # internal page link
        target = href_clean.lstrip('/')
        if target.endswith('.html'):
            if target not in all_html_basenames and not os.path.exists(os.path.join('frontend', target)):
                broken_links.append((fname, 'href', href, f"Target '{target}' does not exist"))
        elif target and not target.startswith(('api', 'v1', 'static', 'assets', 'brand')):
            # might be extensionless link like /dashboard -> dashboard.html
            target_html = f"{target}.html"
            if target_html not in all_html_basenames and not os.path.exists(os.path.join('frontend', target)):
                broken_links.append((fname, 'href', href, f"Target '{target}' / '{target_html}' does not exist"))

    # Check src
    for src in src_pattern.findall(content):
        src_clean = src.split('?')[0].strip()
        if not src_clean or src.startswith(('http://', 'https://', 'data:', '//')):
            continue
        src_path = os.path.join('frontend', src_clean.lstrip('/'))
        if not os.path.exists(src_path) and not os.path.exists(src_clean):
            broken_links.append((fname, 'src', src, f"Resource '{src}' not found on disk"))

print(f"\n--- Broken Links / Missing Assets ({len(broken_links)}) ---")
for b in broken_links[:30]:
    print(f"  [{b[0]}] {b[1]}=\"{b[2]}\" -> {b[3]}")

# 2. Check Colors for Strict 3-Color compliance
# Allowed: #0B0B0C, #FFFFFF, #C6F432 (and rgba variations of 11,11,12 / 255,255,255 / 198,244,50)
hex_pattern = re.compile(r'#([A-Fa-f0-9]{3,8})\b')
allowed_hex = {
    '0b0b0c', 'ffffff', 'fff', '000', '000000', 'c6f432',
    # transparent/none
}
color_violations = []

for f in html_files:
    fname = os.path.basename(f)
    with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
        lines = fh.readlines()
    for idx, line in enumerate(lines):
        # Skip SVG paths or encoded IDs if not style/color
        for match in hex_pattern.findall(line):
            m_lower = match.lower()
            if m_lower not in allowed_hex:
                color_violations.append((fname, idx+1, f"#{match}", line.strip()[:80]))

print(f"\n--- Color Violations Outside Strict Palette ({len(color_violations)}) ---")
for c in color_violations[:30]:
    print(f"  {c[0]}:{c[1]} Found {c[2]} in: {c[3]}")
