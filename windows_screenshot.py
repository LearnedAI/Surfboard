"""
Windows native screenshot capabilities for visual feedback.
"""

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def take_screenshot(output_path="screenshot.png"):
    """Take a screenshot using Windows native tools."""
    
    logger.info(f"Taking screenshot: {output_path}")
    
    # Method 1: PowerShell with .NET System.Drawing
    powershell_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$Screen = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bitmap = New-Object System.Drawing.Bitmap $Screen.Width, $Screen.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($Screen.Left, $Screen.Top, 0, 0, $bitmap.Size)

$bitmap.Save("{output_path}", [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()

Write-Output "Screenshot saved to {output_path}"
"""
    
    try:
        result = subprocess.run([
            "powershell.exe", 
            "-Command", 
            powershell_script
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            logger.info(f"✅ Screenshot taken: {output_path}")
            return True
        else:
            logger.error(f"PowerShell screenshot failed: {result.stderr}")
    except Exception as e:
        logger.error(f"PowerShell screenshot error: {e}")
    
    # Method 2: Windows Snipping Tool (if PowerShell fails)
    try:
        subprocess.run([
            "cmd.exe", "/c", 
            f"powershell -command \"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('%{{PRTSC}}');\""
        ], timeout=5)
        logger.info("⚠️  Used Print Screen - image might be in clipboard")
        return True
    except:
        pass
    
    return False


def capture_window_screenshot(window_title_part="Chrome", output_path="chrome_window.png"):
    """Capture screenshot of a specific window."""
    
    logger.info(f"Capturing window containing '{window_title_part}'")
    
    powershell_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {{
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    public struct RECT {{
        public int Left;
        public int Top;  
        public int Right;
        public int Bottom;
    }}
}}
"@

# Find Chrome window
$processes = Get-Process | Where-Object {{$_.MainWindowTitle -like "*{window_title_part}*"}}
if ($processes) {{
    $process = $processes[0]
    $hwnd = $process.MainWindowHandle
    
    if ($hwnd -ne [IntPtr]::Zero) {{
        # Bring window to front
        [Win32]::SetForegroundWindow($hwnd)
        Start-Sleep -Milliseconds 500
        
        # Get window bounds
        $rect = New-Object Win32+RECT
        [Win32]::GetWindowRect($hwnd, [ref]$rect)
        
        $width = $rect.Right - $rect.Left
        $height = $rect.Bottom - $rect.Top
        
        if ($width -gt 0 -and $height -gt 0) {{
            $bitmap = New-Object System.Drawing.Bitmap $width, $height
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
            
            $bitmap.Save("{output_path}", [System.Drawing.Imaging.ImageFormat]::Png)
            $graphics.Dispose()
            $bitmap.Dispose()
            
            Write-Output "Window screenshot saved: {output_path} (${{width}}x${{height}})"
        }} else {{
            Write-Output "Invalid window dimensions"
        }}
    }} else {{
        Write-Output "Window handle not found"
    }}
}} else {{
    Write-Output "No window found containing '{window_title_part}'"
}}
"""
    
    try:
        result = subprocess.run([
            "powershell.exe", 
            "-Command", 
            powershell_script
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            logger.info(f"✅ Window screenshot result: {result.stdout.strip()}")
            return Path(output_path).exists()
        else:
            logger.error(f"Window screenshot failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Window screenshot error: {e}")
    
    return False


async def test_screenshot_capabilities():
    """Test both full screen and window screenshot capabilities."""
    
    logger.info("=== Testing Windows Screenshot Capabilities ===")
    
    # Test 1: Full screen screenshot
    logger.info("Test 1: Full screen screenshot")
    screenshot_path = "/mnt/c/Users/Learn/Desktop/surfboard_fullscreen.png"
    
    if take_screenshot(screenshot_path):
        logger.info(f"✅ Full screen screenshot should be at: {screenshot_path}")
    else:
        logger.error("❌ Full screen screenshot failed")
    
    await asyncio.sleep(2)
    
    # Test 2: Try to launch Chrome and capture it
    logger.info("Test 2: Launch Chrome and capture window")
    
    chrome_path = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    
    # Launch Chrome
    try:
        process = subprocess.Popen([
            chrome_path,
            "--new-window", 
            "--window-size=800,600",
            "data:text/html,<h1 style='color:blue;text-align:center;margin-top:100px;'>SURFBOARD SCREENSHOT TEST</h1><p style='text-align:center;font-size:24px;'>This Chrome window should be visible in screenshots!</p>"
        ])
        
        logger.info("Chrome launched for screenshot test")
        
        # Wait for Chrome to appear
        await asyncio.sleep(5)
        
        # Take full screenshot with Chrome visible
        full_with_chrome = "/mnt/c/Users/Learn/Desktop/surfboard_with_chrome.png"
        if take_screenshot(full_with_chrome):
            logger.info(f"✅ Screenshot with Chrome: {full_with_chrome}")
        
        # Try to capture just Chrome window
        chrome_window_path = "/mnt/c/Users/Learn/Desktop/surfboard_chrome_window.png"
        if capture_window_screenshot("Chrome", chrome_window_path):
            logger.info(f"✅ Chrome window screenshot: {chrome_window_path}")
        else:
            logger.warning("Chrome window capture failed, but full screenshot should show it")
        
        logger.info("Screenshots taken! Check your Desktop for:")
        logger.info(f"  - {screenshot_path}")
        logger.info(f"  - {full_with_chrome}")  
        logger.info(f"  - {chrome_window_path}")
        
        logger.info("Waiting 10 seconds for you to check the screenshots...")
        await asyncio.sleep(10)
        
    finally:
        if process.poll() is None:
            process.terminate()


async def test_chrome_automation_with_screenshots():
    """Test Chrome automation with visual feedback via screenshots."""
    
    logger.info("=== Chrome Automation with Screenshot Feedback ===")
    
    chrome_path = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    
    try:
        # Step 1: Take initial screenshot
        logger.info("Step 1: Initial desktop screenshot")
        take_screenshot("/mnt/c/Users/Learn/Desktop/step1_initial.png")
        
        # Step 2: Launch Chrome
        logger.info("Step 2: Launching Chrome...")
        process = subprocess.Popen([
            chrome_path,
            "--new-window",
            "--window-size=1000,700",
            "https://www.example.com"
        ])
        
        await asyncio.sleep(4)
        
        # Step 3: Screenshot with Chrome
        logger.info("Step 3: Screenshot after Chrome launch")
        take_screenshot("/mnt/c/Users/Learn/Desktop/step2_chrome_launched.png")
        capture_window_screenshot("Chrome", "/mnt/c/Users/Learn/Desktop/step2_chrome_window.png")
        
        await asyncio.sleep(3)
        
        # Step 4: Send navigation keys to Chrome
        logger.info("Step 4: Sending navigation to Google...")
        
        # Focus Chrome and navigate
        powershell_focus_and_navigate = """
Add-Type -AssemblyName System.Windows.Forms

# Find Chrome window and focus it
$chrome = Get-Process | Where-Object {$_.MainWindowTitle -like "*Chrome*"} | Select-Object -First 1
if ($chrome) {
    $hwnd = $chrome.MainWindowHandle
    [Windows.Forms.Application]::SetForegroundWindow($hwnd)
    Start-Sleep -Milliseconds 500
    
    # Send Ctrl+L to focus address bar
    [System.Windows.Forms.SendKeys]::SendWait("^l")
    Start-Sleep -Milliseconds 200
    
    # Type Google URL
    [System.Windows.Forms.SendKeys]::SendWait("https://www.google.com")
    Start-Sleep -Milliseconds 200
    
    # Press Enter
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    
    Write-Output "Navigation sent to Chrome"
}
"""
        
        subprocess.run([
            "powershell.exe", "-Command", powershell_focus_and_navigate
        ], timeout=10)
        
        # Wait for navigation
        await asyncio.sleep(5)
        
        # Step 5: Final screenshot
        logger.info("Step 5: Final screenshot after navigation")
        take_screenshot("/mnt/c/Users/Learn/Desktop/step3_after_navigation.png")
        capture_window_screenshot("Chrome", "/mnt/c/Users/Learn/Desktop/step3_chrome_final.png")
        
        logger.info("🎉 Chrome automation with screenshots complete!")
        logger.info("Check your Desktop for the screenshot sequence:")
        logger.info("  step1_initial.png - Before Chrome")
        logger.info("  step2_chrome_launched.png - Chrome started") 
        logger.info("  step2_chrome_window.png - Chrome window only")
        logger.info("  step3_after_navigation.png - After navigation")
        logger.info("  step3_chrome_final.png - Final Chrome window")
        
    finally:
        if process.poll() is None:
            process.terminate()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--automation":
        asyncio.run(test_chrome_automation_with_screenshots())
    else:
        asyncio.run(test_screenshot_capabilities())