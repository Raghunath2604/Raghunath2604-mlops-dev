import os
import sys
import time
import uuid
import platform
import threading
import json
import requests
from typing import Optional, Dict

class MLOpsAgent:
    """
    MLOps.dev Edge Agent.
    Runs on IoT/Edge devices to manage model syncing, heartbeats, and telemetry drift.
    """
    
    def __init__(self, api_key: str, device_name: str, hw_class: str, api_url: str = "https://api.mlopsde.me/v1"):
        self.api_key = api_key
        self.device_name = device_name
        self.hw_class = hw_class
        self.api_url = api_url.rstrip("/")
        
        # In a real environment, device_id is saved to a local file (e.g., ~/.mlops/device.json)
        # to ensure it stays the same across reboots. For now, we generate in memory.
        self.device_id = f"dev_{uuid.uuid4().hex[:12]}"
        
        self._running = False
        self._thread = None
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        
        self.active_model = None
        self.active_tag = None
        
        # Telemetry buffer
        self._telemetry_lock = threading.Lock()
        self._inference_count = 0
        self._drift_score = 0.0

    def start(self):
        """Register the device and start the background heartbeat daemon."""
        print(f"[MLOps] Starting Agent for {self.device_name} ({self.device_id})...")
        self._register()
        
        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        print(f"[MLOps] Agent daemon running in background.")
        
    def stop(self):
        """Stop the background daemon."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            
    def _register(self):
        """Register hardware specs with the cloud."""
        payload = {
            "device_id": self.device_id,
            "name": self.device_name,
            "hw_class": self.hw_class,
            "arch": platform.machine(),
            "os": platform.system().lower()
        }
        try:
            res = self._session.post(f"{self.api_url}/agent/register", json=payload)
            res.raise_for_status()
        except Exception as e:
            print(f"[MLOps] Failed to register device: {e}")

    def _heartbeat_loop(self):
        """Background loop to send heartbeats and sync deployments."""
        while self._running:
            try:
                # In a real agent, use psutil to get real metrics
                ram_mb = 120 + (self._inference_count % 50) 
                cpu_pct = 15.5
                temp_c = 45.0
                
                with self._telemetry_lock:
                    drift = self._drift_score
                    infs = self._inference_count
                    
                payload = {
                    "device_id": self.device_id,
                    "ram_mb": ram_mb,
                    "cpu_pct": cpu_pct,
                    "temp_c": temp_c,
                    "drift_score": drift,
                    "inferences_since_last": infs,
                    "model_name": self.active_model,
                    "model_tag": self.active_tag
                }
                
                res = self._session.post(f"{self.api_url}/agent/heartbeat", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    # Check for new deployment
                    deployment = data.get("deployment")
                    if deployment:
                        new_model = deployment.get("model_name")
                        new_tag = deployment.get("model_tag")
                        if new_model != self.active_model or new_tag != self.active_tag:
                            self._download_model(new_model, new_tag, deployment.get("url"))
                            
                with self._telemetry_lock:
                    self._inference_count = 0 # reset after successful sync
                    
            except Exception as e:
                # Silent fail for offline-first resilience
                pass
                
            time.sleep(10) # 10 seconds for demo purposes (usually 60s)

    def _download_model(self, model_name: str, tag: str, url: str):
        """Simulate downloading a new model."""
        print(f"\n[MLOps] ALERT: New deployment received: {model_name}:{tag}")
        print(f"[MLOps] Downloading artifacts...")
        time.sleep(2) # Simulate network transfer
        self.active_model = model_name
        self.active_tag = tag
        print(f"[MLOps] Model successfully loaded. Ready for inference.\n")

    def log_inference(self, input_data, output_data):
        """
        Log an inference event. 
        Calculates drift locally to save bandwidth.
        """
        with self._telemetry_lock:
            self._inference_count += 1
            # Simulate drift calculation (in reality, KL divergence on prob distributions)
            # We'll just randomly increment drift if output confidence is low
            if isinstance(output_data, dict) and output_data.get("confidence", 1.0) < 0.6:
                self._drift_score = min(1.0, self._drift_score + 0.05)
            else:
                self._drift_score = max(0.0, self._drift_score - 0.01)
