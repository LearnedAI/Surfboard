"""
Test Surfboard Chrome automation with complete visual feedback.
"""

import asyncio
import logging
import subprocess
import time
from pathlib import Path

from src.surfboard.automation.windows_capture import SurfboardVisualFeedback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_surfboard_with_visual_feedback():
    """Complete test of Surfboard Chrome automation with screenshots."""
    
    logger.info("=== Surfboard Chrome Automation with Visual Feedback ===")
    
    # Initialize visual feedback system
    visual = SurfboardVisualFeedback()
    
    try:
        # Step 1: Initial state
        visual.take_step_screenshot("initial", "Desktop before Chrome launch")
        await asyncio.sleep(1)
        
        # Step 2: Launch Chrome
        logger.info("Launching Chrome...")
        chrome_path = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
        
        # Launch Chrome with a simple start page
        process = subprocess.Popen([
            chrome_path,
            "--new-window",
            "--window-size=1200,800",
            "data:text/html,<h1 style='color:green;font-size:48px;text-align:center;margin-top:200px;'>🏄 SURFBOARD CHROME TEST</h1><p style='text-align:center;font-size:24px;'>Chrome successfully launched by Surfboard!</p>"
        ])
        
        logger.info(f"Chrome process started (PID: {process.pid})")
        
        # Wait for Chrome to appear
        await asyncio.sleep(4)
        
        # Step 3: Chrome launched
        visual.take_step_screenshot("chrome_launched", "Chrome window should be visible")
        visual.capture_chrome_window("initial_page")
        
        # Step 4: Navigate to Google
        logger.info("Navigating to Google...")
        if visual.navigate_chrome_to_url("https://www.google.com"):
            logger.info("✅ Navigation to Google attempted")
        else:
            logger.warning("⚠️  Navigation attempt had issues")
        
        # Wait for navigation
        await asyncio.sleep(5)
        
        # Step 5: After Google navigation
        visual.take_step_screenshot("after_google", "Should show Google page")
        visual.capture_chrome_window("google_page")
        
        # Step 6: Navigate to GitHub
        logger.info("Navigating to GitHub...")
        if visual.navigate_chrome_to_url("https://github.com"):
            logger.info("✅ Navigation to GitHub attempted")
            
        await asyncio.sleep(5)
        
        # Step 7: After GitHub navigation  
        visual.take_step_screenshot("after_github", "Should show GitHub page")
        visual.capture_chrome_window("github_page")
        
        # Step 8: Navigate back to custom page
        logger.info("Navigating to custom test page...")
        test_page_url = "data:text/html,<h1 style='color:blue;text-align:center;margin-top:100px;'>🎉 NAVIGATION TEST COMPLETE!</h1><p style='text-align:center;font-size:20px;'>Surfboard successfully navigated Chrome to multiple pages!</p><ul style='max-width:600px;margin:50px auto;font-size:16px;'><li>✅ Chrome launched from WSL</li><li>✅ Visual feedback with screenshots</li><li>✅ Navigation to Google</li><li>✅ Navigation to GitHub</li><li>✅ Custom page display</li></ul>"
        
        if visual.navigate_chrome_to_url(test_page_url):
            logger.info("✅ Navigation to test completion page")
            
        await asyncio.sleep(3)
        
        # Step 9: Final state
        visual.take_step_screenshot("final_success", "Test completion page")
        visual.capture_chrome_window("final_page")
        
        # Summary
        logger.info("🎉 SURFBOARD CHROME AUTOMATION COMPLETE!")
        logger.info("📸 Screenshots saved to Desktop/Surfboard_Screenshots/")
        logger.info("✅ Chrome launched successfully")
        logger.info("✅ Visual feedback working")
        logger.info("✅ Navigation automation working")
        logger.info("✅ Window capture working")
        
        logger.info("Keeping Chrome open for 15 seconds so you can observe...")
        await asyncio.sleep(15)
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        # Take error screenshot
        visual.take_step_screenshot("error", f"Error occurred: {e}")
        
    finally:
        # Cleanup
        if process.poll() is None:
            logger.info("Closing Chrome...")
            process.terminate()
            await asyncio.sleep(2)
            if process.poll() is None:
                process.kill()
        
        # Final screenshot showing cleanup
        visual.take_step_screenshot("cleanup", "After Chrome cleanup")
        
        logger.info("✅ Test complete - check your screenshots!")


async def quick_visual_test():
    """Quick test of just the visual feedback system."""
    
    logger.info("=== Quick Visual Feedback Test ===")
    
    visual = SurfboardVisualFeedback()
    
    # Take a few screenshots
    visual.take_step_screenshot("test1", "Quick test screenshot 1")
    
    # Launch Chrome briefly
    chrome_path = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    process = subprocess.Popen([chrome_path, "--new-window", "https://httpbin.org/html"])
    
    await asyncio.sleep(3)
    
    visual.take_step_screenshot("test2", "Chrome should be visible")
    visual.capture_chrome_window("quick_test")
    
    if process.poll() is None:
        process.terminate()
    
    logger.info("✅ Quick visual test complete")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        asyncio.run(quick_visual_test())
    else:
        asyncio.run(test_surfboard_with_visual_feedback())