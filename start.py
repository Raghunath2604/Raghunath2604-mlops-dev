#!/usr/bin/env python3
import subprocess,sys,os
bd=os.path.join(os.path.dirname(os.path.abspath(__file__)),'sdk','server')
if os.path.exists(bd):
    print('[MLOps.dev] Starting API -> http://localhost:8000  |  key: demo')
    print('[MLOps.dev] Run demo: python sdk/demo.py')
    os.chdir(bd)
    try: subprocess.run([sys.executable,'api.py'])
    except KeyboardInterrupt: print('\n[MLOps.dev] Stopped.')
else:
    print('[MLOps.dev] Open frontend/index.html')
