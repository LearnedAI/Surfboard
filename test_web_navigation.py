"""
Test Chrome opening and web page navigation with Windows profile.
"""

import asyncio
import logging

from surfboard.automation.browser_manager import BrowserManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_web_navigation():
    """Test opening Chrome and navigating to web pages."""
    
    logger.info("=== Testing Chrome Web Navigation ===")
    
    # Create browser manager
    manager = BrowserManager(max_instances=1)
    
    try:
        # Launch Chrome with Windows profile
        logger.info("Launching Chrome with Windows profile...")
        browser = await manager.create_instance(
            instance_id="nav-test-browser",
            headless=False,  # Visible window
            window_size=(1200, 800),
            additional_args=[
                "--user-data-dir=/mnt/c/Users/Learn/AppData/Local/Google/Chrome/User Data",
                "--disable-web-security",  # For easier testing
                "--disable-features=VizDisplayCompositor",  # Better compatibility
            ]
        )
        
        logger.info(f"✅ Chrome launched successfully!")
        logger.info(f"   Instance ID: {browser.instance_id}")
        logger.info(f"   Process PID: {browser.chrome_manager.process.pid}")
        logger.info(f"   CDP Port: {browser.debugging_port}")
        
        # Get CDP session
        session = await browser.get_cdp_session()
        logger.info("✅ CDP session established")
        
        # Test 1: Navigate to Google
        logger.info("\n--- Test 1: Navigate to Google ---")
        try:
            await session.page.navigate("https://www.google.com")
            logger.info("✅ Navigation to Google initiated")
            
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Get page info
            title = await session.runtime.evaluate("document.title")
            url = await session.runtime.evaluate("window.location.href")
            logger.info(f"Page title: '{title}'")
            logger.info(f"Current URL: {url}")
            
            # Check if page loaded properly
            body_text = await session.runtime.evaluate(
                "document.body ? document.body.innerText.substring(0, 100) : 'No body'"
            )
            logger.info(f"Page content preview: {body_text[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Google navigation failed: {e}")
        
        # Wait to observe
        logger.info("\nWaiting 5 seconds for you to observe Google page...")
        await asyncio.sleep(5)
        
        # Test 2: Navigate to GitHub
        logger.info("\n--- Test 2: Navigate to GitHub ---")
        try:
            await session.page.navigate("https://github.com")
            logger.info("✅ Navigation to GitHub initiated")
            
            # Wait for page to load
            await asyncio.sleep(4)
            
            # Get page info
            title = await session.runtime.evaluate("document.title")
            url = await session.runtime.evaluate("window.location.href")
            logger.info(f"Page title: '{title}'")
            logger.info(f"Current URL: {url}")
            
            # Check if you're logged in (if you have GitHub account saved)
            try:
                user_info = await session.runtime.evaluate(
                    "document.querySelector('.Header-link--profile') ? 'Logged in' : 'Not logged in'"
                )
                logger.info(f"GitHub login status: {user_info}")
            except:
                logger.info("GitHub login status: Could not determine")
            
        except Exception as e:
            logger.error(f"❌ GitHub navigation failed: {e}")
        
        # Wait to observe
        logger.info("\nWaiting 5 seconds for you to observe GitHub page...")
        await asyncio.sleep(5)
        
        # Test 3: Navigate to a simple test page
        logger.info("\n--- Test 3: Navigate to HTTPBin (test page) ---")
        try:
            await session.page.navigate("https://httpbin.org/html")
            logger.info("✅ Navigation to HTTPBin initiated")
            
            # Wait for page to load
            await asyncio.sleep(2)
            
            # Get page info
            title = await session.runtime.evaluate("document.title")
            url = await session.runtime.evaluate("window.location.href")
            logger.info(f"Page title: '{title}'")
            logger.info(f"Current URL: {url}")
            
            # Get page content
            content = await session.runtime.evaluate(
                "document.body ? document.body.innerText.substring(0, 200) : 'No body'"
            )
            logger.info(f"HTTPBin content: {content[:100]}...")
            
            # Try to find specific elements
            h1_text = await session.runtime.evaluate(
                "document.querySelector('h1') ? document.querySelector('h1').innerText : 'No H1 found'"
            )
            logger.info(f"H1 text: {h1_text}")
            
        except Exception as e:
            logger.error(f"❌ HTTPBin navigation failed: {e}")
        
        # Wait to observe final page
        logger.info("\nWaiting 5 seconds for you to observe final page...")
        await asyncio.sleep(5)
        
        # Test 4: Try going back in history
        logger.info("\n--- Test 4: Browser History Navigation ---")
        try:
            await session.runtime.evaluate("window.history.back()")
            logger.info("✅ Navigated back in history")
            await asyncio.sleep(2)
            
            current_url = await session.runtime.evaluate("window.location.href")
            logger.info(f"After going back, URL: {current_url}")
            
        except Exception as e:
            logger.error(f"❌ History navigation failed: {e}")
        
        # Close session
        await session.close()
        logger.info("✅ CDP session closed")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise
    
    finally:
        # Always clean up
        logger.info("\nCleaning up...")
        await manager.close_all_instances()
        logger.info("✅ Browser closed and cleanup complete")


async def quick_test():
    """Quick test for immediate verification."""
    
    logger.info("=== Quick Navigation Test ===")
    
    manager = BrowserManager(max_instances=1)
    
    try:
        browser = await manager.create_instance(
            instance_id="quick-test",
            headless=False,
            additional_args=[
                "--user-data-dir=/mnt/c/Users/Learn/AppData/Local/Google/Chrome/User Data"
            ]
        )
        
        logger.info("Chrome opened with your profile!")
        
        session = await browser.get_cdp_session()
        
        # Just go to one page
        await session.page.navigate("https://www.example.com")
        await asyncio.sleep(3)
        
        title = await session.runtime.evaluate("document.title")
        logger.info(f"✅ Successfully navigated to: {title}")
        
        await session.close()
        
    finally:
        await manager.close_all_instances()
        logger.info("✅ Quick test complete")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        asyncio.run(quick_test())
    else:
        asyncio.run(test_web_navigation())