"""
Simple test to demonstrate Chrome launching visibly.

This will launch Chrome with a visible window to prove it actually works.
"""

import asyncio
import logging
from surfboard.automation.browser_manager import BrowserManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_visible_chrome_launch():
    """Launch Chrome with visible window."""
    
    logger.info("=== Testing Visible Chrome Launch ===")
    
    # Create browser manager
    manager = BrowserManager(max_instances=1)
    
    try:
        # Create browser instance - NOT HEADLESS so you can see it
        logger.info("Launching Chrome with visible window...")
        
        browser = await manager.create_instance(
            instance_id="visible-chrome",
            headless=False,  # <-- This makes Chrome visible!
            window_size=(1024, 768)
        )
        
        logger.info(f"✅ Chrome launched successfully!")
        logger.info(f"   Browser ID: {browser.instance_id}")
        logger.info(f"   CDP Port: {browser.debugging_port}")
        logger.info(f"   Process PID: {browser.chrome_manager.process.pid if browser.chrome_manager.process else 'Unknown'}")
        
        # Get CDP session to prove it's working
        session = await browser.get_cdp_session()
        
        # Navigate to a simple page
        logger.info("Navigating to test page...")
        await session.page.navigate("https://httpbin.org/html")
        
        # Wait so you can see the Chrome window
        logger.info("Chrome window should be visible now!")
        logger.info("Waiting 10 seconds so you can see it...")
        await asyncio.sleep(10)
        
        # Get page title to prove navigation worked
        title = await session.runtime.evaluate("document.title")
        logger.info(f"✅ Page title: {title}")
        
        # Close session
        await session.close()
        
    except Exception as e:
        logger.error(f"❌ Chrome launch failed: {e}")
        raise
        
    finally:
        # Clean up
        logger.info("Cleaning up browser instances...")
        await manager.close_all_instances()
        logger.info("✅ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(test_visible_chrome_launch())