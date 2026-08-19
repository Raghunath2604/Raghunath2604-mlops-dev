import os
import sys
import time
import random

# Add sdk path so we can import the agent
sys.path.append(os.path.join(os.path.dirname(__file__), "sdk"))

try:
    from mlops_dev.agent import MLOpsAgent
except ImportError:
    print("Error: Could not import MLOpsAgent. Make sure you are in the project root.")
    sys.exit(1)

API_KEY = os.environ.get("MLOPS_API_KEY", "demo")
API_URL = os.environ.get("MLOPS_API_URL", "https://mlopsde.me/api/index/v1") # Vercel URL
HW_CLASS = os.environ.get("HW_CLASS", "jetson_orin")

def run_mock_device():
    print("==================================================")
    print("   🚀 MLOps.dev Edge Agent Simulation            ")
    print("==================================================")
    
    agent = MLOpsAgent(
        api_key=API_KEY,
        device_name=f"Mock-Edge-{random.randint(100, 999)}",
        hw_class=HW_CLASS,
        api_url=API_URL
    )
    
    agent.start()
    
    try:
        while True:
            # Simulate inference loop
            if agent.active_model:
                print(f"[App] Running inference using {agent.active_model}:{agent.active_tag}...", end="\r")
                time.sleep(1.5)
                # Random confidence score
                confidence = random.uniform(0.3, 0.99)
                agent.log_inference(input_data={"image": "camera_frame_01.jpg"}, output_data={"confidence": confidence})
                print(f"[App] Inference done. Confidence: {confidence:.2f}")
            else:
                print(f"[App] Waiting for model deployment from cloud...")
                time.sleep(5)
    except KeyboardInterrupt:
        print("\nShutting down edge agent...")
        agent.stop()
        print("Done.")

if __name__ == "__main__":
    run_mock_device()
