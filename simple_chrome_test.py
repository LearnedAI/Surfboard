"""
Simple Chrome test with focus on getting the debugging port working.
"""

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def simple_chrome_with_debug():
    """Launch Chrome with minimal args focused on debugging port."""
    
    logger.info("=== Simple Chrome with Debug Port ===")
    
    chrome_path = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    temp_profile = Path(tempfile.mkdtemp(prefix="simple_chrome_"))
    debug_port = 8888
    
    # Very minimal Chrome args
    chrome_args = [
        chrome_path,
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={temp_profile}",
        "--disable-web-security",  # Sometimes needed
        "--disable-features=VizDisplayCompositor",  # Compatibility
        "about:blank"  # Start with blank page
    ]
    
    logger.info(f"Chrome args: {' '.join(chrome_args[:4])}...")
    logger.info(f"Debug port: {debug_port}")
    logger.info(f"Profile: {temp_profile}")
    
    try:
        # Launch Chrome
        process = subprocess.Popen(
            chrome_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"Chrome process started (PID: {process.pid})")
        
        # Wait for Chrome to initialize
        await asyncio.sleep(8)
        
        # Check if process is running
        if process.poll() is None:
            logger.info("✅ Chrome process is still running")
            
            # Try debugging port connection
            import aiohttp
            
            for attempt in range(3):
                try:
                    logger.info(f"Attempt {attempt + 1}: Testing debug port...")
                    
                    async with aiohttp.ClientSession() as session:
                        # Test version endpoint
                        async with session.get(f"http://localhost:{debug_port}/json/version", timeout=5) as response:
                            if response.status == 200:
                                version_info = await response.json()
                                logger.info(f"✅ Debug port working! Chrome: {version_info.get('Browser', 'Unknown')}")
                                
                                # Get tabs
                                async with session.get(f"http://localhost:{debug_port}/json", timeout=5) as tab_response:
                                    tabs = await tab_response.json()
                                    logger.info(f"✅ Found {len(tabs)} Chrome tabs")
                                    
                                    if tabs:
                                        tab = tabs[0]
                                        logger.info(f"   Tab URL: {tab.get('url', 'unknown')}")
                                        
                                        # Try WebSocket connection for CDP
                                        ws_url = tab.get('webSocketDebuggerUrl')
                                        if ws_url:
                                            logger.info("✅ WebSocket URL available")
                                            
                                            # Quick CDP test
                                            import websockets
                                            import json
                                            
                                            try:
                                                async with websockets.connect(ws_url, timeout=10) as ws:
                                                    logger.info("✅ WebSocket connected!")
                                                    
                                                    # Navigate to a page
                                                    nav_command = {
                                                        "id": 1,
                                                        "method": "Page.navigate",
                                                        "params": {"url": "https://www.example.com"}
                                                    }
                                                    
                                                    await ws.send(json.dumps(nav_command))
                                                    response = await ws.recv()
                                                    result = json.loads(response)
                                                    
                                                    if result.get('id') == 1:
                                                        logger.info("✅ Navigation command accepted!")
                                                        
                                                        # Wait for navigation
                                                        await asyncio.sleep(3)
                                                        
                                                        # Get title
                                                        title_cmd = {
                                                            "id": 2,
                                                            "method": "Runtime.evaluate",
                                                            "params": {"expression": "document.title", "returnByValue": True}
                                                        }
                                                        
                                                        await ws.send(json.dumps(title_cmd))
                                                        title_response = await ws.recv()
                                                        title_result = json.loads(title_response)
                                                        
                                                        page_title = title_result.get('result', {}).get('result', {}).get('value', 'Unknown')
                                                        logger.info(f"✅ Page title: '{page_title}'")
                                                        
                                                        # SUCCESS!
                                                        logger.info("🎉 FULL SUCCESS: Chrome automation working!")
                                                        break
                                                        
                                            except Exception as ws_error:
                                                logger.error(f"WebSocket error: {ws_error}")
                                        
                                break  # Success, exit retry loop
                                
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < 2:
                        await asyncio.sleep(3)
                    
            else:
                logger.error("❌ All debugging port attempts failed")
                
        else:
            # Process exited
            return_code = process.poll()
            logger.error(f"❌ Chrome exited with code: {return_code}")
            stdout, stderr = process.communicate()
            if stdout.strip():
                logger.error(f"STDOUT: {stdout[:500]}")
            if stderr.strip():
                logger.error(f"STDERR: {stderr[:500]}")
        
        # Wait for observation
        logger.info("You should see a Chrome window. Waiting 10 seconds...")
        await asyncio.sleep(10)
        
    finally:
        # Cleanup
        if process.poll() is None:
            logger.info("Cleaning up Chrome process...")
            process.terminate()
            await asyncio.sleep(2)
            if process.poll() is None:
                process.kill()
        
        # Remove temp profile
        try:
            import shutil
            shutil.rmtree(temp_profile)
        except:
            pass
        
        logger.info("✅ Test complete")


if __name__ == "__main__":
    asyncio.run(simple_chrome_with_debug())