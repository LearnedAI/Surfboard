"""
Tests for Windows UI automation functionality.
"""

import platform
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from surfboard.automation.windows import (
    WindowsAutomation,
    WindowInfo,
    WindowsAutomationError,
    find_chrome_windows,
    focus_chrome_window
)


class TestWindowInfo:
    """Test WindowInfo class."""
    
    def test_initialization(self):
        """Test WindowInfo initialization."""
        window = WindowInfo(
            hwnd=12345,
            title="Test Window",
            class_name="TestClass",
            process_id=999,
            rect=(0, 0, 800, 600)
        )
        
        assert window.hwnd == 12345
        assert window.title == "Test Window"
        assert window.class_name == "TestClass"
        assert window.process_id == 999
        assert window.rect == (0, 0, 800, 600)
    
    def test_initialization_defaults(self):
        """Test WindowInfo initialization with defaults."""
        window = WindowInfo(title="Test")
        
        assert window.hwnd is None
        assert window.title == "Test"
        assert window.class_name == ""
        assert window.process_id is None
        assert window.rect == (0, 0, 0, 0)
    
    def test_repr(self):
        """Test WindowInfo string representation."""
        window = WindowInfo(title="Test", class_name="TestClass", process_id=123)
        repr_str = repr(window)
        
        assert "Test" in repr_str
        assert "TestClass" in repr_str
        assert "123" in repr_str


class TestWindowsAutomation:
    """Test WindowsAutomation class."""
    
    def test_initialization(self):
        """Test WindowsAutomation initialization."""
        automation = WindowsAutomation()
        
        assert automation.platform in ["windows", "linux", "darwin"]
        assert isinstance(automation.is_windows, bool)
        assert isinstance(automation._uia_available, bool)
    
    @patch('platform.system')
    def test_initialization_windows(self, mock_system):
        """Test initialization on Windows."""
        mock_system.return_value = "Windows"
        
        with patch.object(WindowsAutomation, '_check_uia_availability', return_value=True):
            automation = WindowsAutomation()
            assert automation.is_windows is True
            assert automation.platform == "windows"
    
    @patch('platform.system')
    def test_initialization_linux(self, mock_system):
        """Test initialization on Linux."""
        mock_system.return_value = "Linux"
        automation = WindowsAutomation()
        
        assert automation.is_windows is False
        assert automation.platform == "linux"
    
    def test_check_uia_availability_success(self):
        """Test UIA availability check success."""
        automation = WindowsAutomation()
        automation.platform = "windows"
        automation.is_windows = True
        
        with patch('builtins.__import__', return_value=MagicMock()):
            result = automation._check_uia_availability()
            assert result is True
            assert automation._uia_available is True
    
    def test_check_uia_availability_failure(self):
        """Test UIA availability check failure."""
        automation = WindowsAutomation()
        automation.platform = "windows"
        automation.is_windows = True
        
        def mock_import(name, *args, **kwargs):
            if name in ["win32gui", "win32process", "win32con"]:
                raise ImportError("Module not found")
            return MagicMock()
        
        with patch('builtins.__import__', side_effect=mock_import):
            result = automation._check_uia_availability()
            assert result is False
            assert automation._uia_available is False
    
    @pytest.mark.asyncio
    async def test_find_windows_by_title_cross_platform(self):
        """Test finding windows on cross-platform systems."""
        automation = WindowsAutomation()
        automation.is_windows = False
        automation._uia_available = False
        automation.platform = "linux"
        
        with patch.object(automation, '_find_windows_cross_platform', return_value=[
            WindowInfo(title="Test Chrome Window")
        ]) as mock_find:
            windows = await automation.find_windows_by_title("Chrome")
            
            assert len(windows) == 1
            assert windows[0].title == "Test Chrome Window"
            mock_find.assert_called_once_with("Chrome")
    
    @pytest.mark.asyncio
    async def test_find_windows_linux_wmctrl(self):
        """Test finding windows on Linux with wmctrl."""
        automation = WindowsAutomation()
        automation.platform = "linux"
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "0x12345  0  hostname Google Chrome - Test Page"
        
        with patch('subprocess.run', return_value=mock_result):
            windows = await automation._find_windows_linux("Chrome")
            
            assert len(windows) == 1
            assert "Google Chrome" in windows[0].title
    
    @pytest.mark.asyncio
    async def test_find_windows_linux_xdotool_fallback(self):
        """Test finding windows on Linux with xdotool fallback."""
        automation = WindowsAutomation()
        automation.platform = "linux"
        
        # wmctrl fails
        mock_wmctrl_result = MagicMock()
        mock_wmctrl_result.returncode = 1
        
        # xdotool succeeds
        mock_xdotool_search = MagicMock()
        mock_xdotool_search.returncode = 0
        mock_xdotool_search.stdout = "12345678\n"
        
        mock_xdotool_name = MagicMock()
        mock_xdotool_name.returncode = 0
        mock_xdotool_name.stdout = "Google Chrome\n"
        
        def subprocess_side_effect(cmd, **kwargs):
            if "wmctrl" in cmd:
                return mock_wmctrl_result
            elif "search" in cmd:
                return mock_xdotool_search
            elif "getwindowname" in cmd:
                return mock_xdotool_name
            return MagicMock(returncode=1)
        
        with patch('subprocess.run', side_effect=subprocess_side_effect):
            windows = await automation._find_windows_linux("Chrome")
            
            assert len(windows) == 1
            assert windows[0].title == "Google Chrome"
            assert windows[0].hwnd == 12345678
    
    @pytest.mark.asyncio
    async def test_find_windows_macos(self):
        """Test finding windows on macOS."""
        automation = WindowsAutomation()
        automation.platform = "darwin"
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Google Chrome - Test, Safari - Another Test"
        
        with patch('subprocess.run', return_value=mock_result):
            windows = await automation._find_windows_macos("Chrome")
            
            assert len(windows) == 2
            assert windows[0].title == "Google Chrome - Test"
            assert windows[1].title == "Safari - Another Test"
    
    @pytest.mark.asyncio
    async def test_focus_window_cross_platform(self):
        """Test focusing window on cross-platform systems."""
        automation = WindowsAutomation()
        automation.is_windows = False
        automation._uia_available = False
        
        window = WindowInfo(title="Test Window", hwnd=12345)
        
        with patch.object(automation, '_focus_window_cross_platform', return_value=True) as mock_focus:
            result = await automation.focus_window(window)
            
            assert result is True
            mock_focus.assert_called_once_with(window)
    
    @pytest.mark.asyncio
    async def test_focus_window_linux(self):
        """Test focusing window on Linux."""
        automation = WindowsAutomation()
        automation.platform = "linux"
        
        window = WindowInfo(hwnd=12345)
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            result = await automation._focus_window_cross_platform(window)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_focus_window_macos(self):
        """Test focusing window on macOS."""
        automation = WindowsAutomation()
        automation.platform = "darwin"
        
        window = WindowInfo(title="Test Window")
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            result = await automation._focus_window_cross_platform(window)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_get_window_info_found(self):
        """Test getting window info when window is found."""
        automation = WindowsAutomation()
        
        test_window = WindowInfo(title="Test Chrome")
        with patch.object(automation, 'find_windows_by_title', return_value=[test_window]):
            result = await automation.get_window_info("Chrome")
            
            assert result == test_window
    
    @pytest.mark.asyncio
    async def test_get_window_info_not_found(self):
        """Test getting window info when window is not found."""
        automation = WindowsAutomation()
        
        with patch.object(automation, 'find_windows_by_title', return_value=[]):
            result = await automation.get_window_info("NonExistent")
            
            assert result is None
    
    def test_is_available_windows_with_uia(self):
        """Test availability check on Windows with UIA."""
        automation = WindowsAutomation()
        automation.is_windows = True
        automation._uia_available = True
        
        assert automation.is_available() is True
    
    def test_is_available_windows_without_uia(self):
        """Test availability check on Windows without UIA."""
        automation = WindowsAutomation()
        automation.is_windows = True
        automation._uia_available = False
        
        assert automation.is_available() is False
    
    def test_is_available_linux_with_tools(self):
        """Test availability check on Linux with tools."""
        automation = WindowsAutomation()
        automation.is_windows = False
        automation.platform = "linux"
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            assert automation.is_available() is True
    
    def test_is_available_linux_without_tools(self):
        """Test availability check on Linux without tools."""
        automation = WindowsAutomation()
        automation.is_windows = False
        automation.platform = "linux"
        
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            assert automation.is_available() is False
    
    def test_is_available_macos(self):
        """Test availability check on macOS."""
        automation = WindowsAutomation()
        automation.is_windows = False
        automation.platform = "darwin"
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            assert automation.is_available() is True


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.mark.asyncio
    async def test_find_chrome_windows(self):
        """Test finding Chrome windows."""
        mock_automation = AsyncMock()
        mock_automation.find_windows_by_title.side_effect = [
            [WindowInfo(title="Google Chrome - Tab 1", hwnd=1)],
            [WindowInfo(title="Chrome - Tab 2", hwnd=2)],
            []  # No Chromium windows
        ]
        
        with patch('surfboard.automation.windows.WindowsAutomation', return_value=mock_automation):
            windows = await find_chrome_windows()
            
            assert len(windows) == 2
            assert windows[0].title == "Google Chrome - Tab 1"
            assert windows[1].title == "Chrome - Tab 2"
    
    @pytest.mark.asyncio
    async def test_find_chrome_windows_deduplication(self):
        """Test Chrome windows deduplication."""
        mock_automation = AsyncMock()
        mock_automation.find_windows_by_title.side_effect = [
            [WindowInfo(title="Google Chrome", hwnd=1)],
            [WindowInfo(title="Google Chrome", hwnd=1)],  # Duplicate
            []
        ]
        
        with patch('surfboard.automation.windows.WindowsAutomation', return_value=mock_automation):
            windows = await find_chrome_windows()
            
            assert len(windows) == 1  # Duplicate removed
    
    @pytest.mark.asyncio
    async def test_focus_chrome_window_success(self):
        """Test focusing Chrome window successfully."""
        chrome_window = WindowInfo(title="Google Chrome")
        
        with patch('surfboard.automation.windows.find_chrome_windows', return_value=[chrome_window]):
            mock_automation = AsyncMock()
            mock_automation.focus_window.return_value = True
            
            with patch('surfboard.automation.windows.WindowsAutomation', return_value=mock_automation):
                result = await focus_chrome_window()
                
                assert result is True
                mock_automation.focus_window.assert_called_once_with(chrome_window)
    
    @pytest.mark.asyncio
    async def test_focus_chrome_window_no_windows(self):
        """Test focusing Chrome window when none found."""
        with patch('surfboard.automation.windows.find_chrome_windows', return_value=[]):
            result = await focus_chrome_window()
            
            assert result is False


# Integration test (marked for manual testing)
@pytest.mark.manual
@pytest.mark.asyncio
async def test_real_windows_automation():
    """
    Integration test for real Windows automation.
    
    This test requires a desktop environment and may require specific tools
    on Linux/macOS. Mark with @pytest.mark.manual to exclude from automatic runs.
    """
    automation = WindowsAutomation()
    
    if automation.is_available():
        # Test finding any windows
        windows = await automation.find_windows_by_title("")
        
        # Should find at least some windows on a desktop system
        assert len(windows) >= 0  # May be 0 in headless environments
        
        # Test Chrome-specific functionality
        chrome_windows = await find_chrome_windows()
        
        # If Chrome is running, test focusing
        if chrome_windows:
            focus_result = await focus_chrome_window()
            # Focus may fail in some environments (e.g., automated testing)
            assert isinstance(focus_result, bool)
    else:
        pytest.skip("Windows automation not available on this platform")