import asyncio
import aiohttp
import time
import argparse
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scale_test")

async def device_client(session, url, token, device_id):
    headers = {"Cookie": f"np_token={token}"}
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                logger.warning(f"Device {device_id} connection failed: {response.status}")
                return False
            
            # Read streaming SSE
            async for line in response.content:
                if line:
                    decoded = line.decode('utf-8').strip()
                    if decoded.startswith('data:'):
                        pass # Got SSE ping or data
            return True
    except Exception as e:
        # Expected to fail eventually if server is overloaded
        return False

async def main(target_devices, url, token):
    logger.info(f"Starting scale test with {target_devices} concurrent connections to {url}")
    
    # We use a custom connector to allow many connections
    connector = aiohttp.TCPConnector(limit=target_devices + 100)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i in range(target_devices):
            tasks.append(asyncio.create_task(device_client(session, url, token, f"device_{i}")))
            
            if i % 500 == 0 and i > 0:
                logger.info(f"Spawned {i} connections...")
                await asyncio.sleep(0.1) # Pace the connection bursts
                
        logger.info("All connections spawned. Waiting for completions/failures...")
        
        # We wait for 30 seconds to see how many hold
        await asyncio.sleep(30)
        
        # Count how many are still alive (not done)
        alive_count = sum(1 for t in tasks if not t.done())
        logger.info(f"RESULTS: {alive_count} out of {target_devices} connections sustained gracefully after 30 seconds.")
        
        # Cancel remaining
        for t in tasks:
            if not t.done():
                t.cancel()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--devices", type=int, default=10000, help="Number of concurrent device connections")
    parser.add_argument("--url", type=str, default="http://localhost:8000/v1/fleet/stream", help="SSE endpoint URL")
    parser.add_argument("--token", type=str, default="demo1234", help="API token for auth")
    
    args = parser.parse_args()
    
    asyncio.run(main(args.devices, args.url, args.token))
