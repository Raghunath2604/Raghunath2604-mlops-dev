import re

with open("frontend/api/index.py", "r") as f:
    content = f.read()

smtp_code = """
def send_email(to_email, subject, body):
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    from_email = os.environ.get("SMTP_FROM_EMAIL", smtp_user)
    
    if not all([smtp_server, smtp_user, smtp_pass]):
        print(f"[EMAIL MOCK] Missing SMTP config. Would have sent: '{subject}' to {to_email}")
        return
        
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # Force IPv4 to avoid Vercel IPv6 routing issues
    import socket
    old_getaddrinfo = socket.getaddrinfo
    def new_getaddrinfo(*args, **kwargs):
        responses = old_getaddrinfo(*args, **kwargs)
        return [r for r in responses if r[0] == socket.AF_INET]
    socket.getaddrinfo = new_getaddrinfo
    
    try:
        try:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.starttls()
            server.login(smtp_user, smtp_pass)
        except Exception as e:
            print(f"SMTP 587 failed ({e}), trying 465 SSL...")
            server = smtplib.SMTP_SSL(smtp_server, 465, timeout=10)
            server.login(smtp_user, smtp_pass)
            
        server.send_message(msg)
        server.quit()
        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
    finally:
        socket.getaddrinfo = old_getaddrinfo
"""

content = re.sub(r'def send_email\(to_email, subject, body\):.*?(?=\napp = Flask\(__name__\))', smtp_code, content, flags=re.DOTALL)

with open("frontend/api/index.py", "w") as f:
    f.write(content)

with open("sdk/server/api.py", "r") as f:
    content2 = f.read()
content2 = re.sub(r'def send_email\(to_email, subject, body\):.*?(?=\napp = Flask\(__name__\))', smtp_code, content2, flags=re.DOTALL)
with open("sdk/server/api.py", "w") as f:
    f.write(content2)
