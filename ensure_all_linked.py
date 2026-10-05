import glob
import os

files = glob.glob('frontend/*.html')
for f in sorted(files):
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        c = fp.read()
    
    modified = False
    
    # Check tokens.css
    if 'tokens.css' not in c and '</head>' in c:
        c = c.replace('</head>', '  <link rel="stylesheet" href="/tokens.css"/>\n</head>')
        modified = True

    # Check Motion CDN
    if 'cdn.jsdelivr.net/npm/motion' not in c and '</body>' in c:
        c = c.replace('</body>', '  <script src="https://cdn.jsdelivr.net/npm/motion@11.11.17/dist/motion.js"></script>\n</body>')
        modified = True

    # Check motion.js
    if 'motion.js' not in c and '</body>' in c:
        c = c.replace('</body>', '  <script src="/motion.js" defer></script>\n</body>')
        modified = True

    # Check canvas-ambient.js
    if 'canvas-ambient.js' not in c and '</body>' in c:
        c = c.replace('</body>', '  <script src="/canvas-ambient.js" defer></script>\n</body>')
        modified = True

    if modified:
        with open(f, 'w', encoding='utf-8') as fp:
            fp.write(c)
        print('Updated links for:', os.path.basename(f))
    else:
        print('Already complete:', os.path.basename(f))

print('All frontend files validated and synchronized!')
