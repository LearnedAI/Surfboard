"""
Force a completely new Chrome instance by using different approaches.
"""

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_new_chrome_session():
    """Try to force a new Chrome session with various techniques."""
    
    logger.info("=== Forcing New Chrome Session ===")
    logger.info("Issue: Existing Chrome is intercepting our launches")
    
    chrome_path = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    
    # Try multiple approaches
    
    # Approach 1: Use --user-data-dir with unique path and --new-instance
    temp_profile = Path(tempfile.mkdtemp(prefix="surfboard_force_"))
    logger.info(f"Approach 1: Using temp profile {temp_profile}")
    
    try:
        chrome_args = [
            chrome_path,
            "--new-instance",  # Force new instance
            "--no-startup-window",  # Don't use startup window
            "--remote-debugging-port=9777",
            f"--user-data-dir={temp_profile}",
            "--no-first-run",
            "--disable-default-browser-check",
            "--disable-background-networking",
            "--disable-sync",
            "--no-service-autorun",
            "--window-size=1000,700",
            "https://httpbin.org/html"
        ]
        
        logger.info("Launching Chrome with --new-instance...")
        process = subprocess.Popen(
            chrome_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"Process started with PID: {process.pid}")
        
        # Wait longer for startup
        await asyncio.sleep(10)
        
        if process.poll() is None:
            logger.info("✅ Process is running")
            
            # Test debugging port
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:9777/json", timeout=5) as response:
                        tabs = await response.json()
                        logger.info(f"✅ Connected to debugging port! {len(tabs)} tabs found")
                        
                        if tabs:
                            logger.info(f"   Tab URL: {tabs[0].get('url', 'unknown')}")
                            
                            # Try navigation via Surfboard
                            from surfboard.protocols.cdp import CDPClient
                            
                            cdp_client = CDPClient(port=9777)
                            await cdp_client.connect()
                            
                            # Navigate to Google
                            result = await cdp_client.send_command("Page.navigate", {"url": "https://www.google.com"})
                            logger.info("✅ Navigation command sent via CDP")
                            
                            await asyncio.sleep(4)
                            
                            # Get title
                            title_result = await cdp_client.send_command(
                                "Runtime.evaluate", 
                                {"expression": "document.title", "returnByValue": True}
                            )
                            
                            if title_result.get('result', {}).get('value'):
                                logger.info(f"✅ Page title: '{title_result['result']['value']}'")
                            
                            await cdp_client.close()
                            
                            logger.info("SUCCESS: Chrome automation is working!")
                        
            except Exception as debug_error:
                logger.error(f"❌ Debug connection failed: {debug_error}")
                
        else:
            logger.error(f"❌ Process exited with code: {process.poll()}")
            stdout, stderr = process.communicate()
            if stdout.strip():
                logger.info(f"STDOUT: {stdout}")
            if stderr.strip():  
                logger.info(f"STDERR: {stderr}")
        
        logger.info("Waiting 15 seconds for you to observe...")
        await asyncio.sleep(15)
        
    finally:
        # Cleanup
        if process.poll() is None:
            logger.info("Terminating process...")
            process.terminate()
            await asyncio.sleep(2)
            if process.poll() is None:
                process.kill()
        
        # Clean temp profile
        try:
            import shutil
            shutil.rmtree(temp_profile)
        except:
            pass


async def test_with_surfboard():
    """Test the fixed approach with Surfboard."""
    
    logger.info("=== Testing with Surfboard (Fixed) ===")
    
    from surfboard.automation.browser_manager import BrowserManager
    
    manager = BrowserManager(max_instances=1)
    
    try:
        # Use the insights from our testing
        browser = await manager.create_instance(
            instance_id="working-browser",
            headless=False,
            window_size=(1200, 800),
            additional_args=[
                "--new-instance",  # This should help with existing Chrome
                "--no-startup-window",
                "--disable-background-networking",
                "--disable-sync",
                "--no-service-autorun",
            ]
        )
        
        logger.info("✅ Surfboard Chrome launched!")
        
        session = await browser.get_cdp_session()
        logger.info("✅ CDP session established")
        
        # Navigate to test page
        await session.page.navigate("https://httpbin.org/html")
        await asyncio.sleep(3)
        
        title = await session.runtime.evaluate("document.title")
        logger.info(f"✅ Page loaded: '{title}'")
        
        # Navigate to Google
        await session.page.navigate("https://www.google.com")
        await asyncio.sleep(3)
        
        google_title = await session.runtime.evaluate("document.title")
        logger.info(f"✅ Google loaded: '{google_title}'")
        
        await session.close()
        
        logger.info("SUCCESS: Surfboard automation is working!")
        
    except Exception as e:
        logger.error(f"❌ Surfboard test failed: {e}")
        
    finally:
        await manager.close_all_instances()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--surfboard":
        asyncio.run(test_with_surfboard())
    else:
        asyncio.run(test_new_chrome_session())