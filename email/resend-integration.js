/**
 * MLOps.dev — Resend email integration
 * Add this to your Flask backend (backend/email_service.py)
 * or call directly from Node.js
 *
 * Setup:
 * 1. npm install resend   (or pip install resend for Python)
 * 2. Set RESEND_API_KEY environment variable
 * 3. Verify hello@mlops.dev in Resend dashboard → Domains
 * 4. Call sendWaitlistConfirmation() after successful waitlist signup
 *
 * Resend docs: https://resend.com/docs
 */

// ── NODE.JS VERSION ──────────────────────────────────────────────
import { Resend } from 'resend';
import fs from 'fs';

const resend = new Resend(process.env.RESEND_API_KEY);

// Read the HTML template
const emailTemplate = fs.readFileSync('./waitlist-confirmation-email.html', 'utf8');

export async function sendWaitlistConfirmation({ email, name, position }) {
  // Replace template variables
  const html = emailTemplate
    .replace('{{POSITION}}', `#${position}`)
    .replace('{{NAME}}', name || 'there');

  const { data, error } = await resend.emails.send({
    from: 'Raghunathareddy GR <hello@mlops.dev>',
    to: [email],
    subject: `You're #${position} on the MLOps.dev waitlist`,
    html: html,
    // Plain text fallback
    text: `Hi ${name || 'there'},\n\nYou're #${position} on the MLOps.dev waitlist.\n\nI'll be in touch within 24 hours with onboarding details.\n\nIn the meantime, watch the demo: https://www.mlops.dev/demo\nStar on GitHub: https://github.com/Raghunath2604/Raghunath2604-mlops-dev\n\n— Raghunathareddy GR\nCEO & Founder · MLOps.dev\nhello@mlops.dev`,
    tags: [
      { name: 'category', value: 'waitlist_confirmation' },
      { name: 'position', value: String(position) },
    ],
  });

  if (error) {
    console.error('Resend error:', error);
    throw error;
  }

  return data;
}

// ── PYTHON VERSION (add to backend/email_service.py) ────────────
/*
import resend
import os
from pathlib import Path

resend.api_key = os.environ["RESEND_API_KEY"]

def send_waitlist_confirmation(email: str, name: str, position: int):
    template = Path("waitlist-confirmation-email.html").read_text()
    html = template.replace("{{POSITION}}", f"#{position}").replace("{{NAME}}", name or "there")

    params = {
        "from": "Raghunathareddy GR <hello@mlops.dev>",
        "to": [email],
        "subject": f"You're #{position} on the MLOps.dev waitlist",
        "html": html,
    }
    return resend.Emails.send(params)
*/

// ── FLASK INTEGRATION (add to backend/app.py) ───────────────────
/*
# In your /api/waitlist POST handler, after inserting to DB:

from email_service import send_waitlist_confirmation

@app.route('/api/waitlist', methods=['POST'])
def join_waitlist():
    data = request.get_json()
    email = data.get('email', '').strip()
    name  = data.get('name', '').strip()

    # ... your existing DB insert code ...
    # position = result of INSERT ... RETURNING position

    # Send confirmation email (non-blocking)
    try:
        send_waitlist_confirmation(email=email, name=name, position=position)
    except Exception as e:
        app.logger.error(f"Email send failed: {e}")
        # Don't fail the signup if email fails

    return jsonify({'success': True, 'data': {'position': position}})
*/
