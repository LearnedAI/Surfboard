"""
Fixed Chrome test using Windows-accessible paths for data directory.
"""

import asyncio
import logging
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_chrome_with_windows_path():
    """Test Chrome using Windows-accessible paths."""
    
    logger.info("=== Fixed Chrome Test with Windows Paths ===")
    logger.info("Issue identified: Chrome can't access /tmp/ from Windows")
    logger.info("Solution: Use Windows temp directory")
    
    chrome_path = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    
    # Use Windows temp directory that Chrome can access
    import tempfile
    import os
    
    # Create temp dir in Windows temp space
    windows_temp = "/mnt/c/Users/Learn/AppData/Local/Temp"
    chrome_data_dir = f"{windows_temp}/SurfboardChromeTest_{os.getpid()}"
    
    logger.info(f"Using Chrome data directory: {chrome_data_dir}")
    
    # Ensure directory exists
    Path(chrome_data_dir).mkdir(parents=True, exist_ok=True)
    
    debug_port = 5555
    
    chrome_args = [
        chrome_path,
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={chrome_data_dir}",
        "--no-first-run",
        "--disable-default-browser-check",
        "--window-size=1200,800",
        "data:text/html,<h1 style='color: green;'>🎉 Surfboard Chrome Working!</h1><p>This Chrome window was launched by Surfboard from WSL!</p><p>Time: <span id='time'></span></p><script>document.getElementById('time').textContent = new Date().toLocaleString();</script>"
    ]
    
    logger.info(f"Starting Chrome with debug port {debug_port}...")
    
    try:
        process = subprocess.Popen(
            chrome_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"Chrome process started (PID: {process.pid})")
        
        # Wait for Chrome to start
        await asyncio.sleep(8)
        
        if process.poll() is None:
            logger.info("✅ Chrome process is running")
            
            # Test debugging port
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://localhost:{debug_port}/json/version", timeout=5) as response:
                        version_info = await response.json()
                        logger.info(f"✅ Debug port working! Chrome: {version_info['Browser']}")
                        
                    async with session.get(f"http://localhost:{debug_port}/json", timeout=5) as response:
                        tabs = await response.json()
                        logger.info(f"✅ Found {len(tabs)} Chrome tabs")
                        
                        if tabs:
                            tab = tabs[0]
                            logger.info(f"   Tab title: {tab.get('title', 'No title')}")
                            logger.info(f"   Tab URL: {tab.get('url', 'No URL')}")
                            
                            # Test automation via WebSocket
                            ws_url = tab.get('webSocketDebuggerUrl')
                            if ws_url:
                                logger.info("✅ WebSocket debugging available")
                                
                                import websockets
                                import json
                                
                                async with websockets.connect(ws_url, timeout=10) as ws:
                                    logger.info("✅ Connected to Chrome via WebSocket!")
                                    
                                    # Test navigation
                                    nav_command = {
                                        "id": 1,
                                        "method": "Page.navigate",
                                        "params": {"url": "https://www.google.com"}
                                    }
                                    
                                    await ws.send(json.dumps(nav_command))
                                    nav_response = await ws.recv()
                                    nav_result = json.loads(nav_response)
                                    
                                    if nav_result.get('id') == 1:
                                        logger.info("✅ Navigation to Google initiated!")
                                        
                                        # Wait for page load
                                        await asyncio.sleep(4)
                                        
                                        # Get page title
                                        title_command = {
                                            "id": 2,
                                            "method": "Runtime.evaluate",
                                            "params": {"expression": "document.title", "returnByValue": True}
                                        }
                                        
                                        await ws.send(json.dumps(title_command))
                                        title_response = await ws.recv()
                                        title_result = json.loads(title_response)
                                        
                                        page_title = title_result.get('result', {}).get('result', {}).get('value', 'Unknown')
                                        logger.info(f"✅ Google page title: '{page_title}'")
                                        
                                        # Success!
                                        logger.info("🎉 COMPLETE SUCCESS: Chrome automation working!")
                                        logger.info("   - Chrome launches from WSL ✅")
                                        logger.info("   - Debug port accessible ✅") 
                                        logger.info("   - WebSocket CDP connection ✅")
                                        logger.info("   - Page navigation working ✅")
                                        logger.info("   - JavaScript evaluation working ✅")
                        
            except Exception as debug_error:
                logger.error(f"❌ Debug port connection failed: {debug_error}")
                
        else:
            logger.error(f"❌ Chrome process exited with code: {process.poll()}")
            stdout, stderr = process.communicate()
            if stdout.strip():
                logger.error(f"STDOUT: {stdout}")
            if stderr.strip():
                logger.error(f"STDERR: {stderr}")
        
        logger.info("Chrome window should be visible. Waiting 15 seconds...")
        await asyncio.sleep(15)
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        
    finally:
        # Cleanup
        if process.poll() is None:
            logger.info("Terminating Chrome...")
            process.terminate()
            await asyncio.sleep(3)
            if process.poll() is None:
                process.kill()
        
        # Clean up temp directory
        try:
            import shutil
            shutil.rmtree(chrome_data_dir)
            logger.info("✅ Cleaned up temp directory")
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")
        
        logger.info("✅ Test complete")


async def test_with_profile():
    """Test with Windows Chrome profile after confirming basic functionality."""
    
    logger.info("=== Testing with Windows Profile ===")
    
    chrome_path = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    profile_path = "/mnt/c/Users/Learn/AppData/Local/Google/Chrome/User Data"
    debug_port = 4444
    
    chrome_args = [
        chrome_path,
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={profile_path}",
        "--disable-web-security",  # Sometimes needed with profiles
        "--window-size=1200,800",
    ]
    
    logger.info("Launching Chrome with your Windows profile...")
    
    try:
        process = subprocess.Popen(chrome_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        await asyncio.sleep(10)
        
        if process.poll() is None:
            logger.info("✅ Chrome with profile is running")
            
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://localhost:{debug_port}/json", timeout=5) as response:
                        tabs = await response.json()
                        logger.info(f"✅ Profile Chrome accessible: {len(tabs)} tabs")
                        logger.info("Your bookmarks and settings should be visible!")
                        
            except Exception as e:
                logger.error(f"Profile debug connection failed: {e}")
        
        logger.info("Profile Chrome should be visible. Waiting 15 seconds...")
        await asyncio.sleep(15)
        
    finally:
        if process.poll() is None:
            process.terminate()
            await asyncio.sleep(2)
            if process.poll() is None:
                process.kill()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--profile":
        asyncio.run(test_with_profile())
    else:
        asyncio.run(test_chrome_with_windows_path())