"""
Test Chrome with complete process isolation.
"""

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_isolated_chrome():
    """Launch Chrome with complete isolation to avoid existing sessions."""
    
    logger.info("=== Testing Isolated Chrome Launch ===")
    
    chrome_path = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    
    # Create a completely unique user data directory
    temp_profile = Path(tempfile.mkdtemp(prefix="surfboard_isolated_"))
    logger.info(f"Using isolated profile: {temp_profile}")
    
    try:
        # Chrome args for complete isolation
        chrome_args = [
            chrome_path,
            "--remote-debugging-port=9555",
            f"--user-data-dir={temp_profile}",
            "--no-first-run",
            "--disable-default-browser-check",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-sync", 
            "--disable-translate",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--enable-automation",
            "--password-store=basic",
            "--use-mock-keychain",
            "--window-size=1200,800",
            "--new-window",
            "https://www.example.com"
        ]
        
        logger.info("Starting isolated Chrome process...")
        process = subprocess.Popen(
            chrome_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True  # This helps with process isolation
        )
        
        logger.info(f"Chrome started with PID: {process.pid}")
        
        # Wait for Chrome to start
        await asyncio.sleep(8)
        
        # Check if process is running
        if process.poll() is None:
            logger.info("✅ Chrome process is running")
            
            # Test debugging port
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:9555/json/version", timeout=10) as response:
                        version_info = await response.json()
                        logger.info(f"✅ Chrome debugging accessible: {version_info['Browser']}")
                        
                    async with session.get("http://localhost:9555/json", timeout=10) as response:
                        tabs = await response.json()
                        logger.info(f"✅ Found {len(tabs)} tabs")
                        
                        if tabs:
                            tab_url = tabs[0].get('url', 'unknown')
                            tab_title = tabs[0].get('title', 'unknown')
                            logger.info(f"   First tab: '{tab_title}' at {tab_url}")
                            
                            # Test navigation via CDP
                            websocket_url = tabs[0].get('webSocketDebuggerUrl')
                            if websocket_url:
                                logger.info("✅ WebSocket debugging URL available")
                                
                                # Quick CDP test
                                import websockets
                                import json
                                
                                try:
                                    async with websockets.connect(websocket_url, timeout=10) as ws:
                                        # Test navigation
                                        command = {
                                            "id": 1,
                                            "method": "Page.navigate", 
                                            "params": {"url": "https://www.google.com"}
                                        }
                                        
                                        await ws.send(json.dumps(command))
                                        response = await asyncio.wait_for(ws.recv(), timeout=10)
                                        result = json.loads(response)
                                        
                                        if result.get('id') == 1:
                                            logger.info("✅ CDP navigation command sent successfully")
                                            await asyncio.sleep(3)
                                            
                                            # Get page title
                                            title_command = {
                                                "id": 2,
                                                "method": "Runtime.evaluate",
                                                "params": {"expression": "document.title"}
                                            }
                                            
                                            await ws.send(json.dumps(title_command))
                                            title_response = await asyncio.wait_for(ws.recv(), timeout=10)
                                            title_result = json.loads(title_response)
                                            
                                            if title_result.get('result', {}).get('result', {}).get('value'):
                                                page_title = title_result['result']['result']['value']
                                                logger.info(f"✅ Page title retrieved: '{page_title}'")
                                            
                                except Exception as cdp_error:
                                    logger.error(f"CDP test failed: {cdp_error}")
                        
            except Exception as debug_error:
                logger.error(f"❌ Debug port connection failed: {debug_error}")
                
        else:
            logger.error(f"❌ Chrome exited with code: {process.poll()}")
            stdout, stderr = process.communicate()
            if stdout.strip():
                logger.error(f"STDOUT: {stdout}")
            if stderr.strip():
                logger.error(f"STDERR: {stderr}")
        
        # Wait for observation
        logger.info("Chrome should be visible now. Waiting 15 seconds...")
        await asyncio.sleep(15)
        
    finally:
        # Cleanup
        if process.poll() is None:
            logger.info("Terminating Chrome process...")
            process.terminate()
            try:
                await asyncio.wait_for(
                    asyncio.create_task(asyncio.to_thread(process.wait)), 
                    timeout=5
                )
            except asyncio.TimeoutError:
                process.kill()
        
        # Clean up temp profile
        try:
            import shutil
            shutil.rmtree(temp_profile)
            logger.info("✅ Cleaned up temporary profile")
        except Exception as e:
            logger.warning(f"Profile cleanup warning: {e}")
        
        logger.info("✅ Isolated Chrome test complete")


if __name__ == "__main__":
    asyncio.run(test_isolated_chrome())