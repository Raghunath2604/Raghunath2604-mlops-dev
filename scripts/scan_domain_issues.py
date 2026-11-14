import os, glob, re

for f in sorted(glob.glob('frontend/*.html')):
    fname = os.path.basename(f)
    with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
        c = fh.read()
    
    # Check for hardcoded old domain 'mlops.dev' instead of 'mlopsde.me'
    mlops_dev_links = re.findall(r'https?://(?:www\.)?mlops\.dev[^\s"\'<>]*', c)
    nodepilot_links = re.findall(r'https?://[^\s"\'<>]*nodepilot[^\s"\'<>]*', c)
    onrender_links = re.findall(r'https?://[^\s"\'<>]*onrender\.com[^\s"\'<>]*', c)
    
    issues = []
    if mlops_dev_links:
        issues.append(f"Contains {len(mlops_dev_links)} old domain links (mlops.dev): {mlops_dev_links[:3]}")
    if nodepilot_links:
        issues.append(f"Contains {len(nodepilot_links)} old branding links (nodepilot): {nodepilot_links[:3]}")
    if onrender_links:
        issues.append(f"Contains onrender.com links: {onrender_links[:3]}")
    
    if issues:
        print(f"[{fname}]")
        for iss in issues:
            print(f"   {iss}")
