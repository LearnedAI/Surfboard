"""
Test basic Chrome opening without Windows profile first.
"""

import asyncio
import logging

from surfboard.automation.browser_manager import BrowserManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_basic_chrome():
    """Test basic Chrome launch without Windows profile."""
    
    logger.info("=== Testing Basic Chrome Launch ===")
    
    manager = BrowserManager(max_instances=1)
    
    try:
        # Launch Chrome WITHOUT Windows profile first
        logger.info("Launching Chrome with temporary profile...")
        browser = await manager.create_instance(
            instance_id="basic-test",
            headless=False,
            window_size=(1200, 800),
            # No additional_args for Windows profile
        )
        
        logger.info(f"✅ Basic Chrome launched!")
        logger.info(f"   Process PID: {browser.chrome_manager.process.pid}")
        logger.info(f"   CDP Port: {browser.debugging_port}")
        
        # Get CDP session
        session = await browser.get_cdp_session()
        logger.info("✅ CDP session established")
        
        # Navigate to a simple page
        logger.info("Navigating to example.com...")
        await session.page.navigate("https://www.example.com")
        await asyncio.sleep(3)
        
        # Get page info
        title = await session.runtime.evaluate("document.title")
        url = await session.runtime.evaluate("window.location.href")
        logger.info(f"✅ Navigation successful!")
        logger.info(f"   Page title: '{title}'")
        logger.info(f"   URL: {url}")
        
        # Wait to observe
        logger.info("Waiting 8 seconds for you to see the page...")
        await asyncio.sleep(8)
        
        await session.close()
        
    finally:
        await manager.close_all_instances()
        logger.info("✅ Test complete")


async def test_with_profile():
    """Test Chrome launch WITH Windows profile."""
    
    logger.info("=== Testing Chrome with Windows Profile ===")
    
    manager = BrowserManager(max_instances=1)
    
    try:
        # Try with a different approach for Windows profile
        logger.info("Launching Chrome with Windows profile...")
        browser = await manager.create_instance(
            instance_id="profile-test",
            headless=False,
            window_size=(1200, 800),
            additional_args=[
                "--user-data-dir=/mnt/c/Users/Learn/AppData/Local/Google/Chrome/User Data",
                "--no-first-run",
                "--disable-default-browser-check",
                "--disable-extensions-file-access-check",
                "--disable-logging",
                "--disable-gpu-logging",
            ]
        )
        
        logger.info(f"✅ Profile Chrome launched!")
        logger.info(f"   Process PID: {browser.chrome_manager.process.pid}")
        
        session = await browser.get_cdp_session()
        logger.info("✅ CDP session with profile established")
        
        # Navigate to Google (should show your bookmarks/settings)
        logger.info("Navigating to Google...")
        await session.page.navigate("https://www.google.com")
        await asyncio.sleep(4)
        
        title = await session.runtime.evaluate("document.title")
        logger.info(f"✅ Google loaded: '{title}'")
        logger.info("You should see your Chrome bookmarks and settings!")
        
        # Wait longer to observe profile features
        logger.info("Waiting 10 seconds to observe your Chrome profile...")
        await asyncio.sleep(10)
        
        await session.close()
        
    finally:
        await manager.close_all_instances()
        logger.info("✅ Profile test complete")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--profile":
        asyncio.run(test_with_profile())
    else:
        asyncio.run(test_basic_chrome())