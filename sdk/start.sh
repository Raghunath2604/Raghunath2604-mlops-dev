#!/bin/bash
# Start MLOps.dev local API server
pip install flask flask-cors requests -q
echo ''
echo 'Starting MLOps.dev API server...'
python server/api.py
