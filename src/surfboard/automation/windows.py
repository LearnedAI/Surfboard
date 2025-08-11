"""
Windows UI Automation implementation.

This module provides cross-platform desktop automation capabilities,
with Windows UI Automation API integration when available.
"""

import logging
import platform
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class WindowsAutomationError(Exception):
    """Exception raised when Windows automation operations fail."""
    pass


class WindowInfo:
    """Information about a window."""
    
    def __init__(
        self, 
        hwnd: Optional[int] = None, 
        title: str = "", 
        class_name: str = "",
        process_id: Optional[int] = None,
        rect: Optional[Tuple[int, int, int, int]] = None
    ):
        """Initialize window information.
        
        Args:
            hwnd: Window handle (Windows only)
            title: Window title
            class_name: Window class name
            process_id: Process ID that owns the window
            rect: Window rectangle (left, top, right, bottom)
        """
        self.hwnd = hwnd
        self.title = title
        self.class_name = class_name
        self.process_id = process_id
        self.rect = rect or (0, 0, 0, 0)
    
    def __repr__(self) -> str:
        return f"WindowInfo(title='{self.title}', class='{self.class_name}', pid={self.process_id})"


class WindowsAutomation:
    """Cross-platform Windows/desktop automation interface."""
    
    def __init__(self):
        """Initialize Windows automation."""
        self.platform = platform.system().lower()
        self.is_windows = self.platform == "windows"
        self._uia_available = False
        
        if self.is_windows:
            try:
                self._check_uia_availability()
            except Exception as e:
                logger.warning(f"Windows UI Automation not fully available: {e}")
    
    def _check_uia_availability(self) -> bool:
        """Check if Windows UI Automation is available."""
        try:
            # Try to import Windows-specific modules
            import win32gui  # pywin32
            import win32process
            import win32con
            self._uia_available = True
            logger.info("Windows UI Automation libraries available")
            return True
        except ImportError as e:
            logger.info(f"Windows UI Automation libraries not available: {e}")
            # Fall back to cross-platform alternatives
            self._uia_available = False
            return False
    
    async def find_windows_by_title(self, title_pattern: str) -> List[WindowInfo]:
        """Find windows matching title pattern.
        
        Args:
            title_pattern: Title pattern to match (supports partial matches)
            
        Returns:
            List of matching windows
            
        Raises:
            WindowsAutomationError: If window enumeration fails
        """
        if self.is_windows and self._uia_available:
            return self._find_windows_win32(title_pattern)
        else:
            return await self._find_windows_cross_platform(title_pattern)
    
    def _find_windows_win32(self, title_pattern: str) -> List[WindowInfo]:
        """Find windows using Win32 APIs (Windows only)."""
        try:
            import win32gui
            import win32process
            
            windows = []
            
            def enum_windows_callback(hwnd, windows_list):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    class_name = win32gui.GetClassName(hwnd)
                    
                    if title_pattern.lower() in title.lower():
                        try:
                            _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                            rect = win32gui.GetWindowRect(hwnd)
                            
                            window_info = WindowInfo(
                                hwnd=hwnd,
                                title=title,
                                class_name=class_name,
                                process_id=process_id,
                                rect=rect
                            )
                            windows_list.append(window_info)
                        except Exception as e:
                            logger.debug(f"Error getting window info for {hwnd}: {e}")
                return True
            
            win32gui.EnumWindows(enum_windows_callback, windows)
            logger.debug(f"Found {len(windows)} windows matching '{title_pattern}'")
            return windows
            
        except Exception as e:
            raise WindowsAutomationError(f"Failed to find windows: {e}") from e
    
    async def _find_windows_cross_platform(self, title_pattern: str) -> List[WindowInfo]:
        """Find windows using cross-platform methods."""
        windows = []
        
        if self.platform == "linux":
            # Use xdotool or wmctrl on Linux
            windows.extend(await self._find_windows_linux(title_pattern))
        elif self.platform == "darwin":
            # Use AppleScript on macOS  
            windows.extend(await self._find_windows_macos(title_pattern))
        else:
            logger.warning(f"Window enumeration not implemented for platform: {self.platform}")
        
        return windows
    
    async def _find_windows_linux(self, title_pattern: str) -> List[WindowInfo]:
        """Find windows on Linux using wmctrl."""
        windows = []
        
        try:
            # Try wmctrl first
            result = subprocess.run(
                ["wmctrl", "-l"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line and title_pattern.lower() in line.lower():
                        parts = line.split(None, 3)
                        if len(parts) >= 4:
                            window_id = parts[0]
                            title = parts[3]
                            
                            windows.append(WindowInfo(
                                title=title,
                                class_name="",
                                # Convert hex window ID to int if possible
                                hwnd=int(window_id, 16) if window_id.startswith('0x') else None
                            ))
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            logger.debug("wmctrl not available or failed")
        
        # Try xdotool as fallback
        if not windows:
            try:
                result = subprocess.run(
                    ["xdotool", "search", "--name", title_pattern],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    for window_id in result.stdout.strip().split('\n'):
                        if window_id.strip():
                            # Get window title
                            title_result = subprocess.run(
                                ["xdotool", "getwindowname", window_id.strip()],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )
                            
                            title = title_result.stdout.strip() if title_result.returncode == 0 else "Unknown"
                            
                            windows.append(WindowInfo(
                                title=title,
                                hwnd=int(window_id.strip()) if window_id.strip().isdigit() else None
                            ))
                            
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                logger.debug("xdotool not available or failed")
        
        return windows
    
    async def _find_windows_macos(self, title_pattern: str) -> List[WindowInfo]:
        """Find windows on macOS using AppleScript."""
        windows = []
        
        # AppleScript to find windows by title
        applescript = f'''
        tell application "System Events"
            set windowList to {{}}
            repeat with proc in (every application process whose background only is false)
                try
                    repeat with win in (every window of proc)
                        set winTitle to (name of win as string)
                        if winTitle contains "{title_pattern}" then
                            set end of windowList to winTitle
                        end if
                    end repeat
                end try
            end repeat
            return windowList
        end tell
        '''
        
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse AppleScript list output
                window_titles = result.stdout.strip().split(", ")
                for title in window_titles:
                    if title.strip():
                        windows.append(WindowInfo(title=title.strip()))
                        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.debug(f"AppleScript window search failed: {e}")
        
        return windows
    
    async def focus_window(self, window: WindowInfo) -> bool:
        """Bring window to foreground and focus it.
        
        Args:
            window: Window to focus
            
        Returns:
            True if successful, False otherwise
        """
        if self.is_windows and self._uia_available and window.hwnd:
            return self._focus_window_win32(window)
        else:
            return await self._focus_window_cross_platform(window)
    
    def _focus_window_win32(self, window: WindowInfo) -> bool:
        """Focus window using Win32 APIs."""
        try:
            import win32gui
            import win32con
            
            if window.hwnd:
                # Show and activate the window
                win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(window.hwnd)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to focus window {window}: {e}")
            return False
    
    async def _focus_window_cross_platform(self, window: WindowInfo) -> bool:
        """Focus window using cross-platform methods."""
        if self.platform == "linux" and window.hwnd:
            try:
                # Try wmctrl first
                result = subprocess.run(
                    ["wmctrl", "-i", "-a", str(window.hwnd)],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return True
                
                # Try xdotool as fallback
                result = subprocess.run(
                    ["xdotool", "windowactivate", str(window.hwnd)],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
                
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        elif self.platform == "darwin":
            # Use AppleScript on macOS
            applescript = f'''
            tell application "System Events"
                repeat with proc in (every application process)
                    try
                        repeat with win in (every window of proc)
                            if (name of win as string) = "{window.title}" then
                                set frontmost of proc to true
                                return true
                            end if
                        end repeat
                    end try
                end repeat
            end tell
            '''
            
            try:
                result = subprocess.run(
                    ["osascript", "-e", applescript],
                    capture_output=True,
                    timeout=10
                )
                return result.returncode == 0
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        return False
    
    async def get_window_info(self, title_pattern: str) -> Optional[WindowInfo]:
        """Get information about the first window matching pattern.
        
        Args:
            title_pattern: Title pattern to match
            
        Returns:
            WindowInfo if found, None otherwise
        """
        windows = await self.find_windows_by_title(title_pattern)
        return windows[0] if windows else None
    
    def is_available(self) -> bool:
        """Check if Windows automation is available on this platform."""
        if self.is_windows:
            return self._uia_available
        else:
            # Check for Linux/macOS tools
            if self.platform == "linux":
                # Check for wmctrl or xdotool
                for tool in ["wmctrl", "xdotool"]:
                    try:
                        subprocess.run([tool, "--version"], capture_output=True, timeout=2)
                        return True
                    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                        continue
            elif self.platform == "darwin":
                # AppleScript should be available on macOS
                try:
                    subprocess.run(["osascript", "-e", "return 1"], capture_output=True, timeout=2)
                    return True
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                    pass
        
        return False


# Convenience functions

async def find_chrome_windows() -> List[WindowInfo]:
    """Find all Chrome browser windows.
    
    Returns:
        List of Chrome windows
    """
    automation = WindowsAutomation()
    
    # Try different Chrome window title patterns
    patterns = ["Google Chrome", "Chrome", "Chromium"]
    all_windows = []
    
    for pattern in patterns:
        windows = await automation.find_windows_by_title(pattern)
        all_windows.extend(windows)
    
    # Remove duplicates based on hwnd or title
    seen = set()
    unique_windows = []
    for window in all_windows:
        key = window.hwnd if window.hwnd else window.title
        if key not in seen:
            seen.add(key)
            unique_windows.append(window)
    
    return unique_windows


async def focus_chrome_window() -> bool:
    """Focus the first available Chrome window.
    
    Returns:
        True if successful, False otherwise
    """
    chrome_windows = await find_chrome_windows()
    if chrome_windows:
        automation = WindowsAutomation()
        return await automation.focus_window(chrome_windows[0])
    return False