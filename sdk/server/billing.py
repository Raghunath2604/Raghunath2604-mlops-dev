import os
import stripe
from flask import Blueprint, request, jsonify, redirect
# from api import get_db, require_auth (Imported inside functions to avoid circular import)

billing_bp = Blueprint('billing', __name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "sk_test_mock")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://www.mlopsde.me")

@billing_bp.route("/checkout", methods=["POST"])
def create_checkout_session():
    from api import get_db, require_auth
    
    # We apply the logic manually or use the decorator if possible
    # Since we can't easily decorate with a locally imported function,
    # let's just get the token from cookies or header here.
    key = None
    if 'np_token' in request.cookies:
        key = request.cookies.get('np_token')
    else:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth.split(" ", 1)[1].strip()
            
    if not key:
        return jsonify({"error": "Missing Authentication"}), 401
    
    db = get_db()
    user = db.execute("SELECT id, name, stripe_customer_id FROM api_keys WHERE key_hash = ?", (key,)).fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    data = request.get_json(silent=True) or {}
    plan = data.get("plan", "team")
    
    if stripe.api_key == "sk_test_mock":
        # Mock successful checkout session
        return jsonify({"url": f"{FRONTEND_URL}/dashboard?mock_checkout=success"})
        
    try:
        # Define price IDs based on your Stripe dashboard setup
        # These are placeholders that would be replaced with real Stripe Price IDs
        prices = {
            "team": "price_team_monthly_mock",
            "enterprise": "price_enterprise_monthly_mock"
        }
        price_id = prices.get(plan)
        if not price_id:
            return jsonify({"error": "Invalid plan selected"}), 400
            
        session_params = {
            "payment_method_types": ["card"],
            "line_items": [{"price": price_id, "quantity": 1}],
            "mode": "subscription",
            "success_url": f"{FRONTEND_URL}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{FRONTEND_URL}/pricing.html",
            "client_reference_id": user["id"],
            "subscription_data": {
                "trial_period_days": 14,
            }
        }
        
        if user["stripe_customer_id"]:
            session_params["customer"] = user["stripe_customer_id"]
        else:
            session_params["customer_email"] = user["name"]  # Name usually stores the email right now
            
        checkout_session = stripe.checkout.Session.create(**session_params)
        return jsonify({"url": checkout_session.url})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@billing_bp.route("/portal", methods=["POST"])
def create_portal_session():
    from api import get_db
    
    key = None
    if 'np_token' in request.cookies:
        key = request.cookies.get('np_token')
    else:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth.split(" ", 1)[1].strip()
            
    if not key:
        return jsonify({"error": "Missing Authentication"}), 401
    
    db = get_db()
    user = db.execute("SELECT stripe_customer_id FROM api_keys WHERE key_hash = ?", (key,)).fetchone()
    
    if not user or not user["stripe_customer_id"]:
        return jsonify({"error": "No active billing profile found. Please subscribe first."}), 400
        
    if stripe.api_key == "sk_test_mock":
        return jsonify({"url": f"{FRONTEND_URL}/dashboard?mock_portal=success"})
        
    try:
        portalSession = stripe.billing_portal.Session.create(
            customer=user["stripe_customer_id"],
            return_url=f"{FRONTEND_URL}/dashboard"
        )
        return jsonify({"url": portalSession.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@billing_bp.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    
    if not endpoint_secret:
        return jsonify({"status": "ignored - no webhook secret"}), 200

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError as e:
        return "Invalid signature", 400

    db = get_db()
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_id = session.get('customer')
        client_reference_id = session.get('client_reference_id')
        
        if client_reference_id and customer_id:
            db.execute(
                "UPDATE api_keys SET stripe_customer_id=?, subscription_tier='team', subscription_status='active' WHERE id=?", 
                (customer_id, client_reference_id)
            )
            db.commit()
            
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        status = subscription.get('status')
        
        if customer_id:
            db.execute(
                "UPDATE api_keys SET subscription_status=? WHERE stripe_customer_id=?",
                (status, customer_id)
            )
            db.commit()
            
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        
        if customer_id:
            db.execute(
                "UPDATE api_keys SET subscription_tier='free', subscription_status='canceled' WHERE stripe_customer_id=?",
                (customer_id,)
            )
            db.commit()

    return jsonify({"status": "success"}), 200
