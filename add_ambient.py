import glob
import os

files = glob.glob('frontend/*.html')
for f in files:
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        c = fp.read()
    if 'canvas-ambient.js' not in c and '</body>' in c:
        c = c.replace('</body>', '  <script src="/canvas-ambient.js" defer></script>\n</body>')
        with open(f, 'w', encoding='utf-8') as fp:
            fp.write(c)
        print('Linked canvas-ambient.js in:', os.path.basename(f))
print('Done!')
