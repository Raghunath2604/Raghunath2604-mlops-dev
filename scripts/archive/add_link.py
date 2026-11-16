with open("dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

if "index.css" not in html:
    html = html.replace('</head>', '  <link rel="stylesheet" href="index.css?v=5">\n</head>')
    
with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
