import { MLOpsClient, MLOpsAgent } from './index.js';

// We need an API key. Let's use the local test key or assume one.
// Or we can just try without auth to see if it reaches the server.
const apiKey = process.env.API_KEY || "test_key_123";

async function run() {
  const client = new MLOpsClient(apiKey, 'http://localhost:8000/v1');
  
  try {
    console.log("Testing client.status()...");
    const status = await client.status();
    console.log("Status:", status);
  } catch(e) {
    console.error("Status failed:", e.message);
  }

  const agent = new MLOpsAgent(apiKey, "JS-Test-Device", "js-node", 'http://localhost:8000/v1');
  console.log("Testing agent.start()...");
  await agent.start();
  
  console.log("Agent started, device ID:", agent.deviceId);
  
  // Wait a few seconds to let heartbeat go through
  setTimeout(() => {
    agent.stop();
    console.log("Agent stopped.");
  }, 2000);
}

run();
