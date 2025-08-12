"""
Windows native screen capture integration for Surfboard.

This module provides native Windows screenshot and window capture capabilities
for visual feedback during Chrome automation.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WindowsScreenCapture:
    """Windows native screen capture using PowerShell and .NET."""

    @staticmethod
    def take_screenshot(output_path: str) -> bool:
        """Take a full screen screenshot using Windows native tools.
        
        Args:
            output_path: Path where screenshot should be saved
            
        Returns:
            True if screenshot was successful, False otherwise
        """
        logger.info(f"Taking Windows screenshot: {output_path}")
        
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

Write-Output "Screenshot saved: {output_path}"
"""
        
        try:
            result = subprocess.run([
                "powershell.exe", 
                "-Command", 
                powershell_script
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and Path(output_path).exists():
                logger.info(f"✅ Screenshot saved: {output_path}")
                return True
            else:
                logger.error(f"Screenshot failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return False

    @staticmethod
    def capture_window(window_title_part: str, output_path: str) -> bool:
        """Capture screenshot of a specific window.
        
        Args:
            window_title_part: Part of window title to match
            output_path: Path where screenshot should be saved
            
        Returns:
            True if window capture was successful, False otherwise
        """
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

# Find window containing the title
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
            
            Write-Output "SUCCESS: Window captured (${{width}}x${{height}})"
        }} else {{
            Write-Output "ERROR: Invalid window dimensions"
        }}
    }} else {{
        Write-Output "ERROR: Window handle not found"
    }}
}} else {{
    Write-Output "ERROR: No window found containing '{window_title_part}'"
}}
"""
        
        try:
            result = subprocess.run([
                "powershell.exe", 
                "-Command", 
                powershell_script
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and "SUCCESS:" in result.stdout:
                logger.info(f"✅ Window captured: {result.stdout.strip()}")
                return Path(output_path).exists()
            else:
                logger.warning(f"Window capture result: {result.stdout.strip()}")
                return False
                
        except Exception as e:
            logger.error(f"Window capture error: {e}")
            return False

    @staticmethod
    def focus_window_and_send_keys(window_title_part: str, keys: str) -> bool:
        """Focus a window and send keystrokes to it.
        
        Args:
            window_title_part: Part of window title to match
            keys: Keys to send (SendKeys format)
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Focusing window '{window_title_part}' and sending keys")
        
        powershell_script = f"""
Add-Type -AssemblyName System.Windows.Forms

# Find and focus window
$processes = Get-Process | Where-Object {{$_.MainWindowTitle -like "*{window_title_part}*"}}
if ($processes) {{
    $process = $processes[0]
    $hwnd = $process.MainWindowHandle
    
    if ($hwnd -ne [IntPtr]::Zero) {{
        # Bring window to front - use proper Win32 API
        Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {{
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}}
"@
        
        [Win32]::ShowWindow($hwnd, 9)  # SW_RESTORE
        [Win32]::SetForegroundWindow($hwnd)
        Start-Sleep -Milliseconds 1000
        
        # Send keys
        [System.Windows.Forms.SendKeys]::SendWait("{keys}")
        
        Write-Output "SUCCESS: Keys sent to window"
    }} else {{
        Write-Output "ERROR: Window handle not found"
    }}
}} else {{
    Write-Output "ERROR: No window found containing '{window_title_part}'"
}}
"""
        
        try:
            result = subprocess.run([
                "powershell.exe", 
                "-Command", 
                powershell_script
            ], capture_output=True, text=True, timeout=10)
            
            success = result.returncode == 0 and "SUCCESS:" in result.stdout
            if success:
                logger.info(f"✅ Keys sent successfully: {result.stdout.strip()}")
            else:
                logger.warning(f"Key sending result: {result.stdout.strip()}")
            
            return success
            
        except Exception as e:
            logger.error(f"Key sending error: {e}")
            return False


class SurfboardVisualFeedback:
    """Visual feedback system for Surfboard Chrome automation."""
    
    def __init__(self, screenshots_dir: Optional[str] = None):
        """Initialize visual feedback system.
        
        Args:
            screenshots_dir: Directory to save screenshots. 
                           Defaults to user's Desktop.
        """
        if screenshots_dir is None:
            screenshots_dir = "./Surfboard_Screenshots"
        
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        self.capture = WindowsScreenCapture()
        self.step_counter = 0
        
        logger.info(f"Visual feedback initialized: {self.screenshots_dir}")
    
    def take_step_screenshot(self, step_name: str, description: str = "") -> str:
        """Take a screenshot for a specific automation step.
        
        Args:
            step_name: Name of the step (used in filename)
            description: Optional description for logging
            
        Returns:
            Path to the screenshot file
        """
        self.step_counter += 1
        filename = f"step_{self.step_counter:02d}_{step_name}.png"
        output_path = str(self.screenshots_dir / filename)
        
        log_msg = f"Step {self.step_counter}: {step_name}"
        if description:
            log_msg += f" - {description}"
        logger.info(log_msg)
        
        success = self.capture.take_screenshot(output_path)
        if success:
            logger.info(f"📸 Screenshot saved: {filename}")
        else:
            logger.error(f"❌ Screenshot failed: {filename}")
        
        return output_path
    
    def capture_chrome_window(self, step_name: str) -> str:
        """Capture just the Chrome window.
        
        Args:
            step_name: Name of the step (used in filename)
            
        Returns:
            Path to the screenshot file
        """
        filename = f"chrome_{step_name}.png"
        output_path = str(self.screenshots_dir / filename)
        
        success = self.capture.capture_window("Chrome", output_path)
        if success:
            logger.info(f"🖼️  Chrome window captured: {filename}")
        else:
            logger.warning(f"Chrome window capture failed: {filename}")
        
        return output_path
    
    def navigate_chrome_to_url(self, url: str) -> bool:
        """Navigate Chrome to a specific URL using keyboard automation.
        
        Args:
            url: URL to navigate to
            
        Returns:
            True if navigation was attempted successfully
        """
        logger.info(f"Navigating Chrome to: {url}")
        
        # Focus address bar (Ctrl+L)
        if not self.capture.focus_window_and_send_keys("Chrome", "^l"):
            return False
        
        import time
        time.sleep(0.5)
        
        # Type URL
        if not self.capture.focus_window_and_send_keys("Chrome", url):
            return False
        
        time.sleep(0.5)
        
        # Press Enter
        return self.capture.focus_window_and_send_keys("Chrome", "{ENTER}")