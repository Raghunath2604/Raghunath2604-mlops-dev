with open('frontend/demo.html', 'r', encoding='utf-8') as f:
    for idx, l in enumerate(f):
        if 'api(' in l:
            print(f"{idx+1}: {l.strip()}")
