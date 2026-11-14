import os, glob, re

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    # Replace URLs
    content = content.replace('https://www.mlops.dev', 'https://www.mlopsde.me')
    content = content.replace('https://mlops.dev', 'https://www.mlopsde.me')
    content = content.replace('http://www.mlops.dev', 'https://www.mlopsde.me')
    content = content.replace('http://mlops.dev', 'https://www.mlopsde.me')
    
    # Specific footer / modal text domain tags
    content = content.replace('<span class="sf-domain-tag">www.mlops.dev</span>', '<span class="sf-domain-tag">www.mlopsde.me</span>')
    content = content.replace('Founder story · www.mlops.dev', 'Founder story · www.mlopsde.me')
    content = content.replace('Bengaluru, India · www.mlops.dev', 'Bengaluru, India · www.mlopsde.me')
    content = content.replace('Raghunathareddy GR · CEO &amp; Founder · MLOps.dev · www.mlops.dev', 'Raghunathareddy GR · CEO &amp; Founder · MLOps.dev · www.mlopsde.me')
    content = content.replace('This route is not at www.mlops.dev', 'This route is not at www.mlopsde.me')
    content = content.replace('>www.mlops.dev</a>', '>www.mlopsde.me</a>')

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, _, files in os.walk('frontend'):
    for file in files:
        if file.endswith('.html'):
            update_file(os.path.join(root, file))

print("All HTML files updated!")
