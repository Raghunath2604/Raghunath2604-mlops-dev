#!/usr/bin/env python3
import subprocess,sys,os
bd=os.path.join(os.path.dirname(os.path.abspath(__file__)),'sdk','server')
if os.path.exists(bd):
    print('[MLOps.dev] Starting Control Plane API -> http://localhost:8000')
    print('[MLOps.dev] Admin Access -> demo@nodepilot.dev / demo')
    print('[MLOps.dev] Run verification: python verify_6_pillars.py')
    os.chdir(bd)
    try: subprocess.run([sys.executable,'api.py'])
    except KeyboardInterrupt: print('\n[MLOps.dev] Stopped.')
else:
    print('[MLOps.dev] Open frontend/index.html')
