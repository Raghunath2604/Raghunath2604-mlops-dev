# MLOps.dev JavaScript SDK

The official JavaScript/TypeScript SDK for MLOps.dev. Use this to integrate the MLOps edge deployment control plane into your Node.js automation scripts, or embed the Edge Agent into your JavaScript-based IoT devices (e.g. Raspberry Pi running Node.js).

## Installation

```bash
npm install mlops-dev-sdk
```

## Usage: API Client (Control Plane)
Use `MLOpsClient` to deploy models, check fleet status, and download audit logs.

```javascript
import { MLOpsClient } from 'mlops-dev-sdk';

const client = new MLOpsClient('your-api-key');

// Get Fleet Status
const status = await client.status();
console.log(status);

// Deploy a model
await client.deploy('defect-detector', 'v2.0', 'jetson-prod-01');

// Fetch audit logs
const logs = await client.audit({ event_type: 'deployment', limit: 10 });
console.log(logs);
```

## Usage: Edge Agent (Device telemetry)
Use `MLOpsAgent` on the physical IoT device to handle heartbeats, silent drift calculation, and model deployments.

```javascript
import { MLOpsAgent } from 'mlops-dev-sdk';

const agent = new MLOpsAgent('your-api-key', 'Raspberry Pi Line 4', 'rpi4');

// Start background heartbeat loop
await agent.start();

// In your inference loop:
const output = await myModel.predict(image);
agent.logInference(image, output); // Automatically calculates drift locally
```
