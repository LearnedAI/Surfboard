"""
Debug Chrome launch process step by step.
"""

import asyncio
import logging
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_direct_chrome():
    """Test launching Chrome directly."""
    
    logger.info("=== Testing Direct Chrome Launch ===")
    
    chrome_path = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    
    if not Path(chrome_path).exists():
        logger.error(f"Chrome not found at: {chrome_path}")
        return
    
    logger.info(f"Chrome found at: {chrome_path}")
    
    # Try launching Chrome directly
    temp_dir = "/tmp/chrome-test"
    subprocess.run(["mkdir", "-p", temp_dir], check=True)
    
    chrome_args = [
        chrome_path,
        "--remote-debugging-port=9333",
        f"--user-data-dir={temp_dir}",
        "--no-first-run",
        "--disable-default-browser-check",
        "--no-sandbox",
        "--window-size=1200,800",
        "https://www.example.com"
    ]
    
    logger.info(f"Chrome command: {' '.join(chrome_args[:3])}...")
    
    try:
        # Start Chrome process
        process = subprocess.Popen(
            chrome_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"Chrome process started with PID: {process.pid}")
        
        # Wait a few seconds
        await asyncio.sleep(5)
        
        # Check if process is still running
        if process.poll() is None:
            logger.info("✅ Chrome process is running")
            
            # Try to connect to debugging port
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:9333/json/version", timeout=5) as response:
                        version_info = await response.json()
                        logger.info(f"✅ Chrome debugging port accessible: {version_info['Browser']}")
                        
                        # Get tabs
                    async with session.get("http://localhost:9333/json", timeout=5) as response:
                        tabs = await response.json()
                        logger.info(f"✅ Found {len(tabs)} Chrome tabs")
                        if tabs:
                            logger.info(f"   First tab URL: {tabs[0].get('url', 'unknown')}")
                
            except Exception as e:
                logger.error(f"❌ Could not connect to Chrome debugging port: {e}")
        else:
            logger.error(f"❌ Chrome process exited with code: {process.poll()}")
            stdout, stderr = process.communicate()
            logger.error(f"STDOUT: {stdout}")
            logger.error(f"STDERR: {stderr}")
        
        # Wait to observe
        logger.info("Waiting 10 seconds for you to observe Chrome...")
        await asyncio.sleep(10)
        
        # Clean up
        if process.poll() is None:
            logger.info("Terminating Chrome process...")
            process.terminate()
            try:
                await asyncio.wait_for(
                    asyncio.create_task(asyncio.to_thread(process.wait)), 
                    timeout=5
                )
            except asyncio.TimeoutError:
                logger.warning("Chrome didn't terminate gracefully, killing...")
                process.kill()
        
        logger.info("✅ Direct Chrome test complete")
        
    except Exception as e:
        logger.error(f"❌ Direct Chrome launch failed: {e}")


async def test_surfboard_debug():
    """Debug Surfboard's Chrome launch process."""
    
    logger.info("=== Debugging Surfboard Chrome Launch ===")
    
    from surfboard.automation.browser import ChromeManager
    
    chrome_manager = ChromeManager(debugging_port=9444, headless=False)
    
    try:
        # Try to launch with more debug info
        logger.info("Attempting Surfboard Chrome launch...")
        await chrome_manager.launch([])
        
        logger.info("✅ Surfboard Chrome launched successfully!")
        
        # Test CDP connection
        from surfboard.protocols.cdp import test_chrome_connection
        is_connected = await test_chrome_connection(port=9444)
        logger.info(f"CDP Connection test: {'✅ Connected' if is_connected else '❌ Failed'}")
        
        # Wait to observe
        await asyncio.sleep(10)
        
    except Exception as e:
        logger.error(f"❌ Surfboard Chrome launch failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            await chrome_manager.cleanup()
            logger.info("✅ Chrome cleanup complete")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--surfboard":
        asyncio.run(test_surfboard_debug())
    else:
        asyncio.run(test_direct_chrome())