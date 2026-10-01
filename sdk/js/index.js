/**
 * MLOps.dev JavaScript SDK
 */

export class MLOpsClient {
  constructor(apiKey, baseUrl = 'https://api.mlopsde.me/v1') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  async _request(method, endpoint, body = null, params = null) {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) url.searchParams.append(key, value);
      });
    }

    const headers = {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json'
    };

    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const res = await fetch(url.toString(), options);
    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`MLOps API Error ${res.status}: ${errorText}`);
    }
    return res.json();
  }

  async status() {
    return this._request('GET', '/status');
  }

  async audit(options = {}) {
    return this._request('GET', '/audit', null, options);
  }

  async deploy(modelName, tag, target, options = {}) {
    return this._request('POST', '/deployments', {
      model_name: modelName,
      model_tag: tag,
      target,
      ...options
    });
  }
}

export class MLOpsAgent {
  constructor(apiKey, deviceName, hwClass, baseUrl = 'http://localhost:8000/v1') {
    this.apiKey = apiKey;
    this.deviceName = deviceName;
    this.hwClass = hwClass;
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.deviceId = `dev_${Math.random().toString(16).slice(2, 14)}`;
    this.running = false;
    this.driftScore = 0;
    this.inferenceCount = 0;
  }

  async start() {
    console.log(`[MLOps] Starting Agent for ${this.deviceName} (${this.deviceId})...`);
    this.running = true;
    
    // Register the device first
    try {
      await fetch(`${this.baseUrl}/devices/register`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          device_id: this.deviceId,
          hw_class: this.hwClass
        })
      });
    } catch (e) {
      console.error(`[MLOps] Failed to register device: ${e}`);
    }

    this._heartbeatLoop();
  }

  stop() {
    this.running = false;
  }

  logInference(inputData, outputData) {
    this.inferenceCount++;
    // Simulate KL divergence check
    if (outputData && outputData.confidence !== undefined && outputData.confidence < 0.6) {
      this.driftScore = Math.min(1.0, this.driftScore + 0.05);
    } else {
      this.driftScore = Math.max(0.0, this.driftScore - 0.01);
    }
  }

  async _heartbeatLoop() {
    while (this.running) {
      try {
        const payload = {
          ram_mb: 120 + (this.inferenceCount % 50),
          cpu_pct: 15.5,
          temp_c: 45.0,
          drift_score: this.driftScore,
          inferences_since_last: this.inferenceCount,
          model_name: this.activeModel,
          model_tag: this.activeTag
        };

        const res = await fetch(`${this.baseUrl}/devices/${this.deviceId}/ping`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          const data = await res.json();
          this.inferenceCount = 0;
          // the ping endpoint doesn't currently return deployment in the response in the new API
        }
      } catch (e) {
        // Silent fail for offline-first resilience
      }
      // Wait 10 seconds (in real world, 60 seconds)
      await new Promise(r => setTimeout(r, 10000));
    }
  }
}
