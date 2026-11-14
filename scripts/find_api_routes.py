with open('frontend/api/index.py', 'r', encoding='utf-8') as f:
    for idx, l in enumerate(f):
        if '@app.route("/api' in l or "@app.route('/api" in l:
            print(f"{idx+1}: {l.strip()}")
