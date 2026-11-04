import os
import json
import base64
import hashlib
import uuid
import requests
from flask import Blueprint, request, jsonify, redirect

billing_bp = Blueprint('billing', __name__)

PHONEPE_ENV = os.environ.get("PHONEPE_ENV", "UAT") # UAT or PROD
PHONEPE_MERCHANT_ID = os.environ.get("PHONEPE_MERCHANT_ID", "PGTESTPAYUAT")
PHONEPE_SALT_KEY = os.environ.get("PHONEPE_SALT_KEY", "099eb0cd-02cf-4e2a-8aca-3e6c6aff0399")
PHONEPE_SALT_INDEX = os.environ.get("PHONEPE_SALT_INDEX", "1")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://www.mlopsde.me")
API_URL = os.environ.get("MLOPS_API_URL", "https://api.mlopsde.me/v1") # Or wherever /v1 is routed on Vercel

if PHONEPE_ENV == "PROD":
    PHONEPE_API_URL = "https://api.phonepe.com/apis/hermes/pg/v1/pay"
else:
    PHONEPE_API_URL = "https://api-preprod.phonepe.com/apis/pg-sandbox/pg/v1/pay"

@billing_bp.route("/checkout", methods=["POST"])
def phonepe_checkout():
    key = None
    if 'np_token' in request.cookies:
        key = request.cookies.get('np_token')
    else:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth.split(" ", 1)[1].strip()
            
    if not key:
        return jsonify({"error": "Missing Authentication"}), 401
    
    from index import get_db
    db = get_db()
    user = db.execute("SELECT id, name FROM api_keys WHERE key_hash = ?", (key,)).fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    data = request.get_json(silent=True) or {}
    plan = data.get("plan", "team")
    
    if PHONEPE_MERCHANT_ID == "PGTESTPAYUAT" and os.environ.get("MOCK_PHONEPE_DIRECT"):
        # Mock successful checkout session directly (testing flow)
        device_limit = 500 if plan == 'team' else (99999 if plan == 'enterprise' else 10)
        db.execute(
            "UPDATE api_keys SET subscription_tier=?, subscription_status='active', device_limit=? WHERE id=?", 
            (plan, device_limit, user["id"])
        )
        if hasattr(db, 'commit'): db.commit()
        return jsonify({"url": f"{FRONTEND_URL}/dashboard?mock_checkout=success&plan={plan}"})
        
    try:
        # Amount in paise (1 INR = 100 paise)
        amounts = {
            "team": 42000 * 100,      # Approx $499 USD
            "enterprise": 100000 * 100 # Custom pricing placeholder
        }
        amount = amounts.get(plan)
        if not amount:
            return jsonify({"error": "Invalid plan selected"}), 400
            
        txn_id = f"MTX{uuid.uuid4().hex[:16].upper()}"
        
        # We'll encode the plan inside merchantUserId for easy retrieval in the callback!
        safe_user_id = user["id"].replace('-', '')
        m_user_id = f"{safe_user_id}_{plan}"
        
        payload = {
            "merchantId": PHONEPE_MERCHANT_ID,
            "merchantTransactionId": txn_id,
            "merchantUserId": m_user_id,
            "amount": amount,
            "redirectUrl": f"{FRONTEND_URL}/api/index/v1/billing/redirect/phonepe",
            "redirectMode": "POST",
            "callbackUrl": f"{FRONTEND_URL}/api/index/v1/billing/webhook/phonepe",
            "mobileNumber": "8660735943",
            "paymentInstrument": {
                "type": "PAY_PAGE"
            }
        }
        
        payload_json = json.dumps(payload)
        base64_payload = base64.b64encode(payload_json.encode()).decode()
        
        # X-VERIFY generation
        string_to_hash = base64_payload + "/pg/v1/pay" + PHONEPE_SALT_KEY
        hashed_str = hashlib.sha256(string_to_hash.encode()).hexdigest()
        x_verify = hashed_str + "###" + PHONEPE_SALT_INDEX
        
        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": x_verify
        }
        
        req_body = {"request": base64_payload}
        
        # Make the request to PhonePe
        response = requests.post(PHONEPE_API_URL, json=req_body, headers=headers)
        res_data = response.json()
        
        if res_data.get("success"):
            # Redirect to PhonePe payment page
            redirect_url = res_data["data"]["instrumentResponse"]["redirectInfo"]["url"]
            return jsonify({"url": redirect_url})
        else:
            return jsonify({"error": f"PhonePe Initiation Failed: {res_data.get('message')}"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@billing_bp.route("/redirect/phonepe", methods=["POST", "GET"])
def phonepe_redirect():
    # This is the page the user lands on after interacting with PhonePe payment page.
    code = request.form.get("code") or request.args.get("code")
    if code == "PAYMENT_SUCCESS":
        return redirect(f"{FRONTEND_URL}/dashboard?payment=success")
    else:
        return redirect(f"{FRONTEND_URL}/dashboard?payment=failed")

@billing_bp.route("/webhook/phonepe", methods=["POST"])
def phonepe_webhook():
    # Server-to-server callback
    req_data = request.get_json(silent=True) or {}
    b64_response = req_data.get("response")
    if not b64_response:
        return "Invalid payload", 400
        
    x_verify = request.headers.get("X-VERIFY", "")
    string_to_hash = b64_response + PHONEPE_SALT_KEY
    expected_hash = hashlib.sha256(string_to_hash.encode()).hexdigest() + "###" + PHONEPE_SALT_INDEX
    
    if x_verify != expected_hash:
        return "Invalid Signature", 400
        
    try:
        decoded_str = base64.b64decode(b64_response).decode()
        data = json.loads(decoded_str)
        
        if data.get("success") and data.get("code") == "PAYMENT_SUCCESS":
            txn_data = data.get("data", {})
            m_user_id = txn_data.get("merchantUserId", "")
            
            parts = m_user_id.split('_')
            if len(parts) >= 2:
                plan = parts[-1]
                safe_id = parts[0]
                device_limit = 500 if plan == 'team' else (99999 if plan == 'enterprise' else 10)
                
                from index import get_db
                db = get_db()
                user_row = db.execute("SELECT id FROM api_keys WHERE REPLACE(id, '-', '') = ?", (safe_id,)).fetchone()
                
                if user_row:
                    db.execute(
                        "UPDATE api_keys SET subscription_tier=?, subscription_status='active', device_limit=? WHERE id=?", 
                        (plan, device_limit, user_row["id"])
                    )
                    if hasattr(db, 'commit'): db.commit()
    except Exception as e:
        print(f"Webhook processing error: {e}")
        return "Server Error", 500
        
    return jsonify({"status": "success"}), 200

# Endpoint to downgrade/cancel since PhonePe has no drop-in portal
@billing_bp.route("/cancel", methods=["POST"])
def cancel_subscription():
    key = None
    if 'np_token' in request.cookies:
        key = request.cookies.get('np_token')
    else:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth.split(" ", 1)[1].strip()
            
    if not key:
        return jsonify({"error": "Missing Authentication"}), 401
    
    from index import get_db
    db = get_db()
    db.execute(
        "UPDATE api_keys SET subscription_tier='free', subscription_status='canceled', device_limit=10 WHERE key_hash=?",
        (key,)
    )
    if hasattr(db, 'commit'): db.commit()
    return jsonify({"success": True, "message": "Subscription canceled."})
