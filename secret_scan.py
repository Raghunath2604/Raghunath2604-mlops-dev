import os
import re
import subprocess

def scan_secrets():
    print("Starting secret scan...")
    # Get all tracked files
    result = subprocess.run(['git', 'ls-files'], stdout=subprocess.PIPE, text=True)
    files = result.stdout.split()

    patterns = {
        'password': re.compile(r'(?i)password\s*=\s*[\'"]([^\'"]+)[\'"]'),
        'secret': re.compile(r'(?i)secret\s*=\s*[\'"]([^\'"]+)[\'"]'),
        'api_key': re.compile(r'(?i)api_key\s*=\s*[\'"]([^\'"]+)[\'"]'),
        'stripe_key': re.compile(r'sk_(test|live)_[a-zA-Z0-9]+'),
        'turnstile_key': re.compile(r'0x4AAAA[a-zA-Z0-9_-]+'),
        'postgres_uri': re.compile(r'postgres://[^:]+:[^@]+@[^\s]+'),
        'resend_key': re.compile(r're_[a-zA-Z0-9]{20,}'),
        'bearer_token': re.compile(r'Bearer\s+[a-zA-Z0-9_\-\.]{20,}'),
    }

    leaks_found = 0
    for file_path in files:
        if not os.path.isfile(file_path):
            continue
            
        # Skip some safe/binary files
        if file_path.endswith(('.png', '.svg', '.pdf', '.jpg', '.jpeg', '.lock')):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    for secret_type, pattern in patterns.items():
                        match = pattern.search(line)
                        if match:
                            # If it's just getting from environ or it's a known mock, ignore
                            matched_str = match.group(0)
                            if 'os.environ.get' in line or 'process.env' in line:
                                continue
                            if 'sk_test_mock' in line or 'dummy' in line.lower() or 'test' in line.lower():
                                continue
                                
                            print(f"[{secret_type} LEAK] {file_path}:{line_num} -> {line.strip()}")
                            leaks_found += 1
        except Exception as e:
            print(f"Could not read {file_path}: {e}")

    if leaks_found == 0:
        print("NO LEAKS FOUND IN TRACKED FILES!")
    else:
        print(f"Total possible leaks found: {leaks_found}")

if __name__ == '__main__':
    scan_secrets()
