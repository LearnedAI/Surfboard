"""
Debug navigation issues and Chrome profile setup.
"""

import asyncio
import logging
from pathlib import Path

from surfboard.automation.browser_manager import BrowserManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_navigation():
    """Debug navigation and profile issues."""

    logger.info("=== Debugging Navigation and Profile Issues ===")

    # Create browser manager
    manager = BrowserManager(max_instances=1)

    try:
        # First, let's find Windows Chrome profile paths
        logger.info("Looking for Windows Chrome profile paths...")

        # Common Windows Chrome profile locations (WSL can access Windows files)
        possible_paths = [
            Path("/mnt/c/Users/Learn/AppData/Local/Google/Chrome/User Data"),
            Path("/mnt/c/Users/Learn/AppData/Local/Google/Chrome/User Data/Default"),
            Path("/mnt/c/Users/Learn/AppData/Roaming/Google/Chrome/User Data"),
        ]

        for path in possible_paths:
            if path.exists():
                logger.info(f"✅ Found Chrome profile path: {path}")
                # List contents
                try:
                    contents = list(path.iterdir())[:10]  # First 10 items
                    logger.info(f"   Contents: {[p.name for p in contents]}")
                except Exception as e:
                    logger.warning(f"   Could not list contents: {e}")
            else:
                logger.info(f"❌ Not found: {path}")

        # Test 1: Basic Chrome launch (no profile)
        logger.info("\n--- Test 1: Basic Chrome launch ---")
        browser = await manager.create_instance(
            instance_id="debug-browser",
            headless=False,
            window_size=(1200, 800),
        )

        logger.info(f"Browser launched: {browser.instance_id}")
        logger.info(f"CDP Port: {browser.debugging_port}")

        # Get CDP session
        session = await browser.get_cdp_session()
        logger.info("CDP session established")

        # Test navigation with better error handling
        try:
            logger.info("Attempting navigation to httpbin.org...")
            result = await session.page.navigate("https://httpbin.org/html")
            logger.info(f"Navigation result: {result}")

            # Wait a bit for page to load
            await asyncio.sleep(3)

            # Get page info
            title_result = await session.runtime.evaluate("document.title")
            logger.info(f"Page title: '{title_result}'")

            url_result = await session.runtime.evaluate("window.location.href")
            logger.info(f"Current URL: {url_result}")

            # Get page content preview
            content_result = await session.runtime.evaluate(
                "document.body ? document.body.innerText.substring(0, 200) : 'No body'"
            )
            logger.info(f"Page content preview: {content_result}")

        except Exception as nav_error:
            logger.error(f"Navigation failed: {nav_error}")

            # Try to get current page info anyway
            try:
                current_url = await session.runtime.evaluate("window.location.href")
                logger.info(f"Current URL after failed navigation: {current_url}")
            except Exception as e:
                logger.error(f"Could not get current URL: {e}")

        await session.close()
        await manager.close_instance("debug-browser")

        logger.info("Waiting 5 seconds before profile test...")
        await asyncio.sleep(5)

        # Test 2: Try with Windows profile if found
        chrome_profile_path = None
        for path in possible_paths:
            if path.exists():
                chrome_profile_path = path
                break

        if chrome_profile_path:
            logger.info(
                f"\n--- Test 2: Using Windows Chrome profile: {chrome_profile_path} ---"
            )
            try:
                browser2 = await manager.create_instance(
                    instance_id="profile-browser",
                    headless=False,
                    window_size=(1200, 800),
                    # Note: We need to pass the parent directory, Chrome will use Default profile
                    additional_args=[f"--user-data-dir={chrome_profile_path.parent}"],
                )

                logger.info("✅ Chrome launched with Windows profile!")
                logger.info("You should see your bookmarks, extensions, etc.")

                # Wait to observe
                logger.info("Waiting 10 seconds so you can observe...")
                await asyncio.sleep(10)

                await manager.close_instance("profile-browser")

            except Exception as profile_error:
                logger.error(f"Failed to launch with profile: {profile_error}")
        else:
            logger.warning("No Windows Chrome profile found for testing")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

    finally:
        # Clean up
        logger.info("Cleaning up...")
        await manager.close_all_instances()
        logger.info("✅ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(debug_navigation())
