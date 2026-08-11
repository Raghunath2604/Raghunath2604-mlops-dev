import sys
import os

# Render's default start command is 'gunicorn app:app'
# This file routes that command to our actual backend inside sdk/server

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'sdk', 'server')))

from sdk.server.api import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
