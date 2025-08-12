"""
Debug Chrome window visibility issues in WSL
"""

import asyncio
import logging
import subprocess
from pathlib import Path

from surfboard.automation.browser_manager import BrowserManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_direct_chrome_launch():
    """Test launching Windows Chrome directly from WSL."""

    logger.info("=== Testing Direct Windows Chrome Launch ===")

    chrome_path = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"

    if not Path(chrome_path).exists():
        logger.error(f"Chrome not found at: {chrome_path}")
        return

    logger.info(f"Found Chrome at: {chrome_path}")

    # Test 1: Simple Chrome launch (no arguments)
    logger.info("\n--- Test 1: Basic Chrome launch ---")
    try:
        result = subprocess.run(
            [chrome_path, "--new-window", "https://google.com"],
            timeout=5,
            capture_output=True,
            text=True,
        )

        logger.info(f"Return code: {result.returncode}")
        if result.stdout:
            logger.info(f"STDOUT: {result.stdout}")
        if result.stderr:
            logger.info(f"STDERR: {result.stderr}")

    except subprocess.TimeoutExpired:
        logger.info("Chrome launched (timed out waiting - this is expected)")
    except Exception as e:
        logger.error(f"Failed to launch Chrome: {e}")

    # Give time to see if window appears
    logger.info("Waiting 10 seconds to see if Chrome window appears...")
    await asyncio.sleep(10)

    # Kill any Chrome processes we may have started
    try:
        subprocess.run(
            ["taskkill", "/f", "/im", "chrome.exe"], capture_output=True, check=False
        )
    except:
        pass


async def test_surfboard_chrome_args():
    """Test what arguments Surfboard is passing to Chrome."""

    logger.info("\n=== Testing Surfboard Chrome Arguments ===")

    manager = BrowserManager(max_instances=1)

    # Let's manually inspect what arguments would be generated
    from surfboard.automation.browser import ChromeManager

    chrome_manager = ChromeManager(debugging_port=9223, headless=False)
    chrome_manager.user_data_dir = Path("/tmp/test-chrome")

    # Get the args that would be used
    args = chrome_manager._build_chrome_args([])
    logger.info(f"Surfboard Chrome arguments: {args}")

    # Check if headless is being forced somewhere
    if "--headless" in " ".join(args) or "--headless=new" in " ".join(args):
        logger.warning("⚠️  HEADLESS MODE DETECTED in arguments!")
    else:
        logger.info("✅ No headless mode detected in arguments")


async def test_surfboard_visible_chrome():
    """Test Surfboard Chrome with explicit visibility settings."""

    logger.info("\n=== Testing Surfboard Visible Chrome ===")

    manager = BrowserManager(max_instances=1)

    try:
        # Force non-headless mode with explicit arguments
        browser = await manager.create_instance(
            instance_id="debug-visible-chrome",
            headless=False,  # Explicitly non-headless
            window_size=(1200, 800),
            additional_args=[
                "--new-window",
                "--force-device-scale-factor=1",
                "--disable-gpu-sandbox",
                "--no-sandbox",  # Sometimes needed for WSL
                # Remove any potential headless forcing
                "--disable-headless",
            ],
        )

        logger.info("✅ Surfboard Chrome instance created")
        logger.info(f"   Instance ID: {browser.instance_id}")
        logger.info(
            f"   Process PID: {browser.chrome_manager.process.pid if browser.chrome_manager.process else 'Unknown'}"
        )

        # Check if process is actually running
        if browser.chrome_manager.process:
            poll_result = browser.chrome_manager.process.poll()
            if poll_result is None:
                logger.info("✅ Chrome process is running")
            else:
                logger.warning(f"⚠️  Chrome process exited with code: {poll_result}")

        logger.info("Waiting 15 seconds to see if Chrome window appears...")
        await asyncio.sleep(15)

        # Try to get session and navigate
        try:
            session = await browser.get_cdp_session()
            logger.info("✅ CDP session established")

            await session.page.navigate("https://example.com")
            await asyncio.sleep(3)

            title = await session.runtime.evaluate("document.title")
            logger.info(f"Page title: {title}")

            await session.close()

        except Exception as cdp_error:
            logger.error(f"CDP error: {cdp_error}")

        await manager.close_instance("debug-visible-chrome")

    except Exception as e:
        logger.error(f"Surfboard test failed: {e}")
        await manager.close_all_instances()


async def test_wsl_display_settings():
    """Check WSL display environment."""

    logger.info("\n=== Checking WSL Display Environment ===")

    import os

    display = os.environ.get("DISPLAY", "Not set")
    logger.info(f"DISPLAY environment variable: {display}")

    wayland_display = os.environ.get("WAYLAND_DISPLAY", "Not set")
    logger.info(f"WAYLAND_DISPLAY: {wayland_display}")

    # Check if we're in WSL
    try:
        with open("/proc/version", "r") as f:
            version_info = f.read()
            if "microsoft" in version_info.lower() or "wsl" in version_info.lower():
                logger.info("✅ Running in WSL environment")
                logger.info(f"Kernel info: {version_info.strip()}")
            else:
                logger.info("Running in native Linux")
    except:
        logger.info("Could not determine environment")


async def main():
    """Run all debug tests."""

    await test_wsl_display_settings()
    await test_direct_chrome_launch()
    await test_surfboard_chrome_args()
    await test_surfboard_visible_chrome()

    logger.info("\n=== Debug Tests Complete ===")
    logger.info("If no Chrome windows appeared, the issue might be:")
    logger.info("1. WSL display forwarding not configured")
    logger.info("2. Chrome defaulting to headless mode")
    logger.info("3. Windows firewall blocking Chrome")
    logger.info("4. Chrome process starting but window not visible")


if __name__ == "__main__":
    asyncio.run(main())
