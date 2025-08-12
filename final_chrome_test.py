"""
Final approach: Kill existing Chrome and start fresh.
"""

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def kill_existing_chrome():
    """Try to kill existing Chrome processes."""
    
    logger.info("=== Killing Existing Chrome Processes ===")
    
    try:
        # Try Windows taskkill
        result = subprocess.run(
            ["powershell.exe", "-Command", "Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force"],
            capture_output=True,
            text=True,
            timeout=10
        )
        logger.info(f"Windows Chrome kill attempt: {result.returncode}")
        
        # Wait for processes to die
        await asyncio.sleep(3)
        
    except Exception as e:
        logger.warning(f"Chrome kill attempt failed: {e}")


async def fresh_chrome_test():
    """Test Chrome after killing existing processes."""
    
    logger.info("=== Fresh Chrome Test ===")
    
    await kill_existing_chrome()
    
    chrome_path = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    temp_profile = Path(tempfile.mkdtemp(prefix="fresh_chrome_"))
    debug_port = 6666
    
    chrome_args = [
        chrome_path,
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={temp_profile}",
        "--no-first-run",
        "--disable-default-browser-check", 
        "--window-size=1000,700",
        "data:text/html,<h1>Surfboard Chrome Test</h1><p>If you can see this, Chrome automation is working!</p>"
    ]
    
    logger.info(f"Starting fresh Chrome on port {debug_port}...")
    
    try:
        process = subprocess.Popen(
            chrome_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, 
            text=True
        )
        
        logger.info(f"Fresh Chrome started (PID: {process.pid})")
        
        # Wait longer for startup
        await asyncio.sleep(10)
        
        if process.poll() is None:
            logger.info("✅ Fresh Chrome is running")
            
            # Test debug port
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://localhost:{debug_port}/json", timeout=5) as response:
                        tabs = await response.json()
                        logger.info(f"🎉 SUCCESS: Debug port accessible! {len(tabs)} tabs")
                        
                        if tabs:
                            logger.info(f"   Tab: {tabs[0].get('title', 'No title')}")
                            logger.info("✅ Chrome automation is now working!")
                            
                            # Quick automation test
                            ws_url = tabs[0].get('webSocketDebuggerUrl')
                            if ws_url:
                                import websockets
                                import json
                                
                                async with websockets.connect(ws_url) as ws:
                                    # Change the page content
                                    script_cmd = {
                                        "id": 1,
                                        "method": "Runtime.evaluate",
                                        "params": {
                                            "expression": "document.body.innerHTML = '<h1>🎉 SUCCESS!</h1><p>Chrome automation with Surfboard is working!</p><p>Time: ' + new Date().toLocaleTimeString() + '</p>'"
                                        }
                                    }
                                    
                                    await ws.send(json.dumps(script_cmd))
                                    await ws.recv()
                                    
                                    logger.info("✅ Page content updated via automation!")
            
            except Exception as debug_error:
                logger.error(f"❌ Debug port test failed: {debug_error}")
                
        else:
            logger.error(f"❌ Fresh Chrome exited: {process.poll()}")
            stdout, stderr = process.communicate()
            if stdout:
                logger.error(f"STDOUT: {stdout[:200]}")
            if stderr:
                logger.error(f"STDERR: {stderr[:200]}")
        
        logger.info("Waiting 20 seconds for you to observe the Chrome window...")
        await asyncio.sleep(20)
        
    finally:
        if process.poll() is None:
            process.terminate()
            await asyncio.sleep(2)
            if process.poll() is None:
                process.kill()
        
        try:
            import shutil
            shutil.rmtree(temp_profile)
        except:
            pass
        
        logger.info("✅ Fresh Chrome test complete")


if __name__ == "__main__":
    asyncio.run(fresh_chrome_test())