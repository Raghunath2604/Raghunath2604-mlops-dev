import resend
import os
import hmac
import hashlib
from pathlib import Path
from urllib.parse import quote

resend.api_key = os.environ.get("RESEND_API_KEY", "")
# Use RESEND_API_KEY as the secret for HMAC if available, else a fallback
HMAC_SECRET = resend.api_key.encode('utf-8') if resend.api_key else b"dev_secret_key"

def generate_approval_token(email: str) -> str:
    return hmac.new(HMAC_SECRET, email.encode('utf-8'), hashlib.sha256).hexdigest()

def verify_approval_token(email: str, token: str) -> bool:
    expected = generate_approval_token(email)
    return hmac.compare_digest(expected, token)

def send_waitlist_confirmation(email: str, name: str, position: int):
    if not resend.api_key:
        print(f"Skipping email to {email} - RESEND_API_KEY not set")
        return
        
    try:
        template_path = Path(__file__).parent.parent.parent / "email" / "waitlist-confirmation.html"
        if template_path.exists():
            template = template_path.read_text(encoding='utf-8')
        else:
            template = "Hi {{NAME}}, you're #{{POSITION}} on the waitlist!"
            
        html = template.replace("{{POSITION}}", f"{position}").replace("{{NAME}}", name or "there")

        params = {
            "from": "Raghunathareddy GR <hello@mlopsde.me>",
            "to": [email],
            "subject": f"You're #{position} on the MLOps.dev waitlist",
            "html": html,
        }
        return resend.Emails.send(params)
    except Exception as e:
        print(f"Failed to send email to {email}: {e}")

def send_admin_approval_email(email: str, name: str, source: str, admin_email: str = "hello@mlopsde.me"):
    token = generate_approval_token(email)
    
    # We will point to the backend API endpoint
    # Depending on where the backend is deployed, we construct the URL
    base_url = "https://api.mlopsde.me"
    
    approve_url = f"{base_url}/v1/admin/approve?email={quote(email)}&token={token}"
    
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
        <h2 style="color: #333;">New Dashboard Access Request</h2>
        <p><strong>Name:</strong> {name}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Company/Source:</strong> {source or 'N/A'}</p>
        
        <div style="margin-top: 30px;">
            <a href="{approve_url}" style="background-color: #5B8AF0; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Approve & Grant API Key</a>
        </div>
        <p style="margin-top: 20px; font-size: 12px; color: #888;">If you do not want to approve this request, simply ignore this email.</p>
    </div>
    """
    
    if not resend.api_key:
        print(f"Mock Admin Approval Email -> {admin_email}\nLink: {approve_url}")
        return
        
    try:
        params = {
            "from": "MLOps.dev Admin <hello@mlopsde.me>",
            "to": [admin_email],
            "subject": f"Access Request: {name} ({email})",
            "html": html,
        }
        return resend.Emails.send(params)
    except Exception as e:
        print(f"Failed to send admin approval email for {email}: {e}")

def send_approval_success_email(email: str, name: str, new_api_key: str):
    dashboard_url = "https://www.mlopsde.me/dashboard"
    
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
        <h2 style="color: #333;">You're Approved!</h2>
        <p>Hi {name or 'there'},</p>
        <p>Your request to access the MLOps.dev dashboard has been approved by our admin team.</p>
        
        <div style="background-color: #f5f7fa; padding: 15px; border-radius: 6px; margin: 20px 0; border: 1px solid #e1e4e8;">
            <p style="margin: 0 0 10px 0; font-size: 14px; color: #555;">Your Admin API Key:</p>
            <code style="font-size: 18px; font-weight: bold; color: #1a202c; word-break: break-all;">{new_api_key}</code>
        </div>
        
        <p>You can use this key to log into the dashboard:</p>
        <a href="{dashboard_url}" style="background-color: #10D9A0; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Go to Dashboard</a>
        
        <p style="margin-top: 30px; font-size: 12px; color: #888;">Keep this key secure and do not share it.</p>
    </div>
    """
    
    if not resend.api_key:
        print(f"Mock Success Email -> {email}\nKey: {new_api_key}")
        return
        
    try:
        params = {
            "from": "MLOps.dev Team <hello@mlopsde.me>",
            "to": [email],
            "subject": "Your MLOps.dev Dashboard Access is Approved!",
            "html": html,
        }
        return resend.Emails.send(params)
    except Exception as e:
        print(f"Failed to send success email to {email}: {e}")
