# MLOps.dev — Phase 1 Complete (FINAL)
Raghunathareddy GR · hello@mlops.dev · www.mlops.dev

GitHub:   https://github.com/Raghunath2604/Raghunath2604-mlops-dev
PyPI:     https://pypi.org/project/mlops-dev
Discord:  https://discord.gg/Tb47N9NaPk
Roadmap:  https://roadmap.mlops.dev
GA4:      G-T4N00SB1DN

## DEPLOY WEBSITE
  cd mlops-dev
  npx vercel ./frontend --name mlops-dev

## RUN THE SDK
  cd mlops-dev/sdk
  pip install flask flask-cors requests
  python server/api.py          # Terminal 1 — real API
  export MLOPS_API_KEY=demo
  export MLOPS_API_URL=http://localhost:8000/v1
  python demo.py                # Terminal 2 — 16 real ops

## CLI
  pip install -e .
  mlops status
  mlops devices list
  mlops deploy defect-detector:v1.0 --target jetson-prod-01
  mlops drift report
  mlops rollback --to defect-detector:v1.0

## PUBLISH TO PYPI
  cd mlops-dev/sdk
  pip install build twine && python -m build && twine upload dist/*
