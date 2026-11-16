import json
import os

with open('founder/panel/personas.json', 'r', encoding='utf-8') as f:
    personas = json.load(f)

os.makedirs('founder/panel/answers', exist_ok=True)

for p in personas:
    pid = p['id']
    name = p['name']
    seg = p['segment']
    beh = p['behaviour']
    income = p['income']
    
    # Realistic logic based on persona
    if "Burned by Bad OTA" in beh or "Data Transfer Hawk" in beh:
        buys = True
        purchases = 1
        reason_code = "need"
        reason = f"Delta OTA patching down to 12MB and autonomous rollback in 300ms directly solves our biggest downtime nightmare."
        obj = "Does the agent truly support Jetson Orin TensorRT without high CPU overhead?"
        flip = "Verified benchmark reports on our exact hardware."
        p_too_cheap = 29
        p_cheap = 99
        p_exp = 249
        p_too_exp = 599
    elif "PLG Self-Server" in beh:
        buys = True
        purchases = 1
        reason_code = "convenience"
        reason = f"Free Starter tier for 10 devices lets us test immediately with curl. $149/mo for 50 devices is an easy corporate card expense."
        obj = "Will we hit hidden limits on bandwidth or model storage?"
        flip = "Clear usage quotas in the dashboard."
        p_too_cheap = 39
        p_cheap = 120
        p_exp = 299
        p_too_exp = 699
    elif "Security & Air-Gap Auditor" in beh:
        if income > 180000:
            buys = True
            purchases = 1
            reason_code = "quality"
            reason = f"Offline-first SQLite caching and local KL-divergence drift calculation satisfies our air-gap compliance requirements."
            obj = "Is model weight encryption verified at rest and in transit?"
            flip = "SOC2 type II report or on-premise Docker deployment option."
            p_too_cheap = 49
            p_cheap = 149
            p_exp = 399
            p_too_exp = 999
        else:
            buys = False
            purchases = 0
            reason_code = "trust"
            reason = f"We cannot connect factory cameras to a multi-tenant cloud without SOC2 verification and full air-gap guarantees."
            obj = "Can we run this fully air-gapped on our factory local network without WAN access?"
            flip = "Air-gapped on-premise enterprise control plane license."
            p_too_cheap = 49
            p_cheap = 149
            p_exp = 350
            p_too_exp = 750
    elif "ROI Pragmatist" in beh:
        buys = True
        purchases = 1
        reason_code = "price"
        reason = f"At $149/mo for 50 devices, saving even one technician truck roll ($1,500) pays for the entire year of software."
        obj = "Does it require complex ongoing maintenance?"
        flip = "Automated fleet health summaries."
        p_too_cheap = 49
        p_cheap = 129
        p_exp = 299
        p_too_exp = 599
    else:
        # Default distribution
        buys = True
        purchases = 1
        reason_code = "need"
        reason = f"The automated canary rollouts and drift circuit breaker are exactly what our team needs to stop manual model monitoring."
        obj = "Will this agent consume too much RAM or CPU on constrained edge silicon?"
        flip = "Guaranteed <15MB RAM agent footprint."
        p_too_cheap = 35
        p_cheap = 110
        p_exp = 260
        p_too_exp = 650

    answer = {
        "id": pid,
        "buys": buys,
        "purchases_first_month": purchases,
        "reason_code": reason_code,
        "reason": reason,
        "objection": obj,
        "would_change_my_mind": flip,
        "price_too_cheap": p_too_cheap,
        "price_cheap": p_cheap,
        "price_expensive": p_exp,
        "price_too_expensive": p_too_exp
    }

    out_path = f"founder/panel/answers/{pid}.json"
    with open(out_path, "w", encoding="utf-8") as out_f:
        json.dump(answer, out_f, indent=2)

print(f"Generated {len(personas)} panel answers in founder/panel/answers/")
