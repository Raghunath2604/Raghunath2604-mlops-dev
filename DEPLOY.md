# MLOps.dev — Complete Deploy Guide
Raghunathareddy GR · hello@mlops.dev

This guide makes EVERY link work: www.mlops.dev, docs.mlops.dev,
roadmap.mlops.dev, api.mlops.dev, discord, github, pypi.

═══════════════════════════════════════════════════════════════
  STEP 1 — Deploy website to Vercel (10 minutes)
═══════════════════════════════════════════════════════════════

1. Install Vercel CLI:
   npm i -g vercel

2. Deploy frontend:
   cd mlops-dev
   vercel ./frontend --name mlops-dev --prod

3. In Vercel dashboard → your project → Settings → Domains → Add:
   www.mlops.dev        (main site)
   mlops.dev            (redirect to www)

4. Point your DNS at Vercel (in your domain registrar):
   www   CNAME  cname.vercel-dns.com
   @     A      76.76.21.21

5. Verify: https://www.mlops.dev should load your site ✅

═══════════════════════════════════════════════════════════════
  STEP 2 — Set up subdomains (5 minutes in Vercel)
═══════════════════════════════════════════════════════════════

In Vercel → your project → Settings → Domains → Add each:

  docs.mlops.dev    → points to the same Vercel deployment
  roadmap.mlops.dev → points to the same Vercel deployment

The vercel.json in this zip handles all routing automatically.
When someone visits docs.mlops.dev they see api-reference.html.
When someone visits roadmap.mlops.dev they see roadmap.html.

DNS records to add:
  docs      CNAME  cname.vercel-dns.com
  roadmap   CNAME  cname.vercel-dns.com

═══════════════════════════════════════════════════════════════
  STEP 3 — Deploy the API server (api.mlops.dev)
═══════════════════════════════════════════════════════════════

The SDK server (sdk/server/api.py) is a real Flask app.
Deploy it to Railway, Render, or your own VPS:

  Option A — Railway (easiest, free tier):
  1. Go to railway.app → New Project → Deploy from GitHub
  2. Push sdk/server/ to a GitHub repo
  3. Add environment variable: PORT=8000
  4. Railway gives you a URL like xyz.railway.app
  5. Add custom domain: api.mlops.dev → xyz.railway.app

  Option B — Render (free tier):
  1. render.com → New Web Service → Connect GitHub
  2. Build: pip install flask flask-cors
  3. Start: python api.py
  4. Add custom domain: api.mlops.dev

  Option C — Your own VPS:
  pip install flask flask-cors gunicorn
  gunicorn -w 4 -b 0.0.0.0:8000 api:app

After deploying, update SDK env var:
  export MLOPS_API_URL=https://api.mlops.dev/v1
  export MLOPS_API_KEY=your-real-key

═══════════════════════════════════════════════════════════════
  STEP 4 — Publish SDK to PyPI
═══════════════════════════════════════════════════════════════

1. Create account at pypi.org
2. Generate API token at pypi.org/manage/account/token/

3. Build and publish:
   cd mlops-dev/sdk
   pip install build twine
   python -m build
   twine upload dist/*
   # Enter your PyPI token when prompted

4. Verify: https://pypi.org/project/mlops-dev ✅

Users can then: pip install mlops-dev

═══════════════════════════════════════════════════════════════
  STEP 5 — Submit to Google Search Console
═══════════════════════════════════════════════════════════════

1. Go to search.google.com/search-console
2. Add property: https://www.mlops.dev
3. Verify via DNS TXT record
4. Sitemaps → Add: https://www.mlops.dev/sitemap.xml
5. Google indexes within 24-48 hours

═══════════════════════════════════════════════════════════════
  STEP 6 — Wire the waitlist email (Resend)
═══════════════════════════════════════════════════════════════

1. Sign up at resend.com
2. Verify hello@mlops.dev domain
3. Create API key
4. Set environment variable: RESEND_API_KEY=re_xxxx
5. The code is in email/resend-integration.js

═══════════════════════════════════════════════════════════════
  WHAT WORKS RIGHT NOW (without any deployment)
═══════════════════════════════════════════════════════════════

Local SDK server:
  cd mlops-dev/sdk
  pip install flask flask-cors requests
  python server/api.py          # → http://localhost:8000
  python demo.py                # 16 real operations

CLI (after pip install -e .):
  mlops status
  mlops devices list
  mlops models push ./model.onnx --name mymodel --tag v1.0
  mlops deploy mymodel:v1.0 --target jetson-prod-01
  mlops drift report
  mlops rollback --to mymodel:v0.9
  mlops audit --format csv -o audit.csv

═══════════════════════════════════════════════════════════════
  AFTER ALL STEPS COMPLETE
═══════════════════════════════════════════════════════════════

URL                           STATUS
www.mlops.dev                 ✅ Live website
docs.mlops.dev                ✅ → api-reference.html
roadmap.mlops.dev             ✅ → roadmap.html
api.mlops.dev/v1              ✅ Flask API (Railway/Render)
pypi.org/project/mlops-dev   ✅ pip install mlops-dev
discord.gg/Tb47N9NaPk        ✅ Your Discord server
github.com/Raghunath2604      ✅ Push your code here

═══════════════════════════════════════════════════════════════
  ALL URLS IN THE CODEBASE
═══════════════════════════════════════════════════════════════

GitHub:   https://github.com/Raghunath2604/Raghunath2604-mlops-dev
PyPI:     https://pypi.org/project/mlops-dev
Discord:  https://discord.gg/Tb47N9NaPk
Roadmap:  https://roadmap.mlops.dev  (→ www.mlops.dev/roadmap.html)
Docs API: https://docs.mlops.dev/api (→ www.mlops.dev/api-reference.html)
GA4:      G-T4N00SB1DN
