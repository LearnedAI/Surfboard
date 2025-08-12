#!/usr/bin/env python3
"""
Test Chrome launch with immediate screenshot and error dialog analysis
"""

import asyncio
import logging
import subprocess
import time
from pathlib import Path

from surfboard.automation.browser_manager import BrowserManager

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def take_full_screen_screenshot(filename="chrome_launch_screenshot.png"):
    """Take a full screen screenshot using PowerShell"""
    try:
        powershell_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save('{filename}', [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()
$graphics.Dispose()

Write-Host "Screenshot saved: {filename}"
Write-Host "Resolution: $($screen.Width)x$($screen.Height)"
"""

        # Execute PowerShell command
        result = subprocess.run(
            ["powershell.exe", "-Command", powershell_script],
            capture_output=True,
            text=True,
            cwd="/mnt/c/Users/Learn/Surfboard",
        )

        if result.returncode == 0:
            logger.info(f"✅ Screenshot captured: {filename}")
            logger.info(f"PowerShell output: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"❌ Screenshot failed: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"❌ Screenshot error: {e}")
        return False


async def test_chrome_launch_with_screenshot():
    """Launch Chrome with Surfboard and immediately take screenshot"""

    logger.info("🚀 Starting Chrome launch test with screenshot analysis...")

    # Clean up any existing Chrome processes first
    logger.info("🧹 Cleaning up existing Chrome processes...")
    try:
        subprocess.run(
            [
                "powershell.exe",
                "-Command",
                "Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force",
            ],
            capture_output=True,
        )
        await asyncio.sleep(2)  # Wait for cleanup
    except:
        pass

    manager = None
    browser = None

    try:
        # Take pre-launch screenshot
        logger.info("📸 Taking pre-launch screenshot...")
        await take_full_screen_screenshot("pre_launch_screenshot.png")

        # Create browser manager
        manager = BrowserManager(max_instances=1)
        logger.info("✅ BrowserManager created")

        # Launch Chrome with Windows profile - visible window
        logger.info("🌐 Launching Chrome with Windows profile...")
        browser = await manager.create_instance(
            instance_id="test-chrome-screenshot",
            headless=False,  # Visible window for screenshot analysis
            window_size=(1200, 800),
            additional_args=[
                "--user-data-dir=/mnt/c/Users/Learn/AppData/Local/Google/Chrome/User Data",
                "--profile-directory=Default",
                "--new-window",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )

        logger.info(f"✅ Chrome launched successfully!")
        logger.info(f"   Process PID: {browser.chrome_manager.process.pid}")
        logger.info(f"   Debug Port: {browser.chrome_manager.debug_port}")

        # Wait a moment for Chrome to fully initialize
        logger.info("⏳ Waiting for Chrome to fully initialize...")
        await asyncio.sleep(5)

        # Take screenshot immediately after launch
        logger.info("📸 Taking post-launch screenshot for analysis...")
        screenshot_success = await take_full_screen_screenshot(
            "post_launch_screenshot.png"
        )

        if screenshot_success:
            logger.info("✅ Screenshot captured successfully!")

            # Try to get CDP session to verify Chrome is responsive
            try:
                session = await browser.get_cdp_session()
                logger.info("✅ CDP session established - Chrome is responsive")

                # Get basic page info
                title_result = await session.runtime.evaluate("document.title")
                logger.info(
                    f"📄 Page title: {title_result.get('result', {}).get('value', 'Unknown')}"
                )

                await session.close()

            except Exception as cdp_error:
                logger.warning(f"⚠️ CDP connection issue: {cdp_error}")

        # Keep Chrome open for a few more seconds for observation
        logger.info("👀 Keeping Chrome open for 10 seconds for visual inspection...")
        await asyncio.sleep(10)

        # Take final screenshot
        await take_full_screen_screenshot("final_screenshot.png")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        # Take error screenshot
        await take_full_screen_screenshot("error_screenshot.png")

    finally:
        # Cleanup
        if browser and manager:
            try:
                logger.info("🧹 Cleaning up browser instances...")
                await manager.close_all_instances()
                logger.info("✅ Cleanup completed")
            except Exception as cleanup_error:
                logger.error(f"❌ Cleanup error: {cleanup_error}")


def analyze_screenshot_for_dialogs(screenshot_path):
    """Analyze screenshot for potential error dialogs or popups"""
    logger.info(f"🔍 Analyzing screenshot: {screenshot_path}")

    # Check if screenshot file exists
    if not Path(screenshot_path).exists():
        logger.error(f"❌ Screenshot not found: {screenshot_path}")
        return False

    file_size = Path(screenshot_path).stat().st_size
    logger.info(f"📊 Screenshot file size: {file_size:,} bytes")

    # Basic file validation
    if file_size < 1000:  # Very small file, likely failed
        logger.warning(
            "⚠️ Screenshot file is very small - may indicate capture failure"
        )
        return False
    elif file_size > 50_000_000:  # Very large file
        logger.warning(
            "⚠️ Screenshot file is very large - may indicate unusual content"
        )

    logger.info("✅ Screenshot appears to be valid for analysis")
    logger.info("👁️ Manual visual inspection recommended to check for:")
    logger.info("   - Error dialog boxes")
    logger.info("   - Chrome crash messages")
    logger.info("   - Permission request popups")
    logger.info("   - Windows security warnings")
    logger.info("   - Browser unresponsive messages")

    return True


async def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("🏄 SURFBOARD CHROME SCREENSHOT TEST")
    logger.info("=" * 60)

    # Run the Chrome launch test
    await test_chrome_launch_with_screenshot()

    # Analyze the screenshots
    logger.info("\n" + "=" * 60)
    logger.info("📸 SCREENSHOT ANALYSIS")
    logger.info("=" * 60)

    screenshots = [
        "pre_launch_screenshot.png",
        "post_launch_screenshot.png",
        "final_screenshot.png",
    ]

    for screenshot in screenshots:
        if Path(screenshot).exists():
            analyze_screenshot_for_dialogs(screenshot)
        else:
            logger.warning(f"⚠️ Screenshot not found: {screenshot}")

    logger.info(
        "\n✅ Test completed! Check the generated screenshots for error dialogs."
    )


if __name__ == "__main__":
    asyncio.run(main())
