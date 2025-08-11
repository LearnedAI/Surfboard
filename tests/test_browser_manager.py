"""
Tests for enhanced browser manager functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from surfboard.automation.browser_manager import (
    BrowserInstance,
    BrowserManager,
    BrowserProfile,
    managed_browser,
)
from surfboard.automation.browser import ChromeManager
from surfboard.protocols.cdp import CDPClient


class TestBrowserProfile:
    """Test BrowserProfile functionality."""

    def test_create_temporary_profile(self):
        """Test creating temporary profile."""
        profile = BrowserProfile.create_temporary("test-profile")
        
        assert profile.name == "test-profile"
        assert profile.temporary is True
        assert "surfboard_temp_test-profile" in str(profile.path)
        assert profile.path.exists()
        
        # Clean up
        profile.cleanup()
        assert not profile.path.exists()

    def test_create_persistent_profile(self):
        """Test creating persistent profile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            profile = BrowserProfile.create_persistent("test-profile", base_dir)
            
            assert profile.name == "test-profile"
            assert profile.temporary is False
            assert profile.path == base_dir / "test-profile"
            assert profile.path.exists()

    def test_configure_preferences(self):
        """Test configuring Chrome preferences."""
        profile = BrowserProfile.create_temporary("test-prefs")
        
        preferences = {
            "profile": {
                "default_content_setting_values": {
                    "notifications": 2
                }
            }
        }
        
        profile.configure_preferences(preferences)
        
        prefs_file = profile.path / "Default" / "Preferences"
        assert prefs_file.exists()
        
        import json
        with open(prefs_file, 'r') as f:
            saved_prefs = json.load(f)
            
        assert saved_prefs == preferences
        
        # Clean up
        profile.cleanup()


class TestBrowserInstance:
    """Test BrowserInstance functionality."""

    @pytest.mark.asyncio
    async def test_browser_instance_creation(self):
        """Test browser instance creation."""
        mock_manager = MagicMock()
        mock_manager.debugging_port = 9222
        mock_manager.is_running.return_value = True
        
        instance = BrowserInstance(
            instance_id="test-instance",
            manager=mock_manager,
            profile_path=Path("/tmp/test")
        )
        
        assert instance.instance_id == "test-instance"
        assert instance.debugging_port == 9222
        assert instance.is_running is True
        assert instance.profile_path == Path("/tmp/test")

    @pytest.mark.asyncio
    async def test_get_cdp_session(self):
        """Test getting CDP session."""
        mock_manager = MagicMock()
        mock_manager.debugging_port = 9222
        
        mock_cdp_client = AsyncMock()
        mock_cdp_client.connect = AsyncMock()
        
        with patch('surfboard.automation.browser_manager.CDPClient', return_value=mock_cdp_client):
            instance = BrowserInstance("test", mock_manager)
            
            session = await instance.get_cdp_session()
            
            mock_cdp_client.connect.assert_called_once()
            assert instance.cdp_client == mock_cdp_client

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test instance cleanup."""
        mock_manager = AsyncMock()
        mock_manager.cleanup = AsyncMock()
        
        mock_cdp_client = AsyncMock()
        mock_cdp_client.disconnect = AsyncMock()
        
        profile = BrowserProfile.create_temporary("test-cleanup")
        
        instance = BrowserInstance(
            "test",
            mock_manager,
            mock_cdp_client,
            profile.path
        )
        
        await instance.cleanup()
        
        mock_cdp_client.disconnect.assert_called_once()
        mock_manager.cleanup.assert_called_once()


class TestBrowserManager:
    """Test BrowserManager functionality."""

    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """Test browser manager initialization."""
        manager = BrowserManager(max_instances=3)
        
        assert manager.max_instances == 3
        assert len(manager.instances) == 0
        assert len(manager.profiles) == 0
        assert manager._port_counter == 9222

    @pytest.mark.asyncio
    async def test_create_instance_success(self):
        """Test successful instance creation."""
        with patch('surfboard.automation.browser_manager.ChromeManager') as mock_chrome_class:
            mock_chrome = AsyncMock()
            mock_chrome.launch = AsyncMock()
            mock_chrome.debugging_port = 9222
            mock_chrome_class.return_value = mock_chrome
            
            with patch('surfboard.automation.browser_manager.CDPClient') as mock_cdp_class:
                mock_cdp = AsyncMock()
                mock_cdp.connect = AsyncMock()
                mock_cdp_class.return_value = mock_cdp
                
                manager = BrowserManager(max_instances=2)
                
                instance = await manager.create_instance(
                    instance_id="test-browser",
                    headless=True
                )
                
                assert instance.instance_id == "test-browser"
                assert len(manager.instances) == 1
                mock_chrome.launch.assert_called_once()
                mock_cdp.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance_max_exceeded(self):
        """Test instance creation when max exceeded."""
        manager = BrowserManager(max_instances=1)
        manager.instances["existing"] = MagicMock()  # Fake existing instance
        
        with pytest.raises(RuntimeError, match="Maximum instances"):
            await manager.create_instance("new-instance")

    @pytest.mark.asyncio
    async def test_get_instance(self):
        """Test getting instance by ID."""
        manager = BrowserManager()
        mock_instance = MagicMock()
        manager.instances["test-id"] = mock_instance
        
        result = await manager.get_instance("test-id")
        assert result == mock_instance
        
        result = await manager.get_instance("non-existent")
        assert result is None

    @pytest.mark.asyncio
    async def test_close_instance(self):
        """Test closing instance."""
        manager = BrowserManager()
        
        mock_instance = AsyncMock()
        mock_instance.cleanup = AsyncMock()
        manager.instances["test-id"] = mock_instance
        
        result = await manager.close_instance("test-id")
        
        assert result is True
        assert "test-id" not in manager.instances
        mock_instance.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_all_instances(self):
        """Test closing all instances."""
        manager = BrowserManager()
        
        # Add mock instances
        for i in range(3):
            mock_instance = AsyncMock()
            mock_instance.cleanup = AsyncMock()
            manager.instances[f"instance-{i}"] = mock_instance
        
        result = await manager.close_all_instances()
        
        assert result == 3
        assert len(manager.instances) == 0

    @pytest.mark.asyncio
    async def test_list_instances(self):
        """Test listing instances."""
        manager = BrowserManager()
        
        # Add mock instance
        mock_instance = MagicMock()
        mock_instance.debugging_port = 9222
        mock_instance.is_running = True
        mock_instance.created_at = 1234567890
        mock_instance.last_activity = 1234567900
        mock_instance.profile_path = Path("/tmp/profile")
        
        manager.instances["test-instance"] = mock_instance
        
        instances = await manager.list_instances()
        
        assert len(instances) == 1
        instance_info = instances[0]
        assert instance_info["id"] == "test-instance"
        assert instance_info["port"] == 9222
        assert instance_info["running"] is True
        assert instance_info["profile_path"] == "/tmp/profile"

    @pytest.mark.asyncio
    async def test_cleanup_idle_instances(self):
        """Test cleaning up idle instances."""
        manager = BrowserManager()
        
        import asyncio
        current_time = asyncio.get_event_loop().time()
        
        # Add idle instance
        idle_instance = AsyncMock()
        idle_instance.cleanup = AsyncMock()
        idle_instance.last_activity = current_time - 4000  # 4000s ago
        manager.instances["idle"] = idle_instance
        
        # Add active instance
        active_instance = MagicMock()
        active_instance.last_activity = current_time - 100  # 100s ago
        manager.instances["active"] = active_instance
        
        result = await manager.cleanup_idle_instances(max_idle_time=3600)
        
        assert result == 1
        assert "idle" not in manager.instances
        assert "active" in manager.instances
        idle_instance.cleanup.assert_called_once()

    def test_create_profile(self):
        """Test creating profile."""
        manager = BrowserManager()
        
        # Create temporary profile
        profile = manager.create_profile("test-temp", temporary=True)
        
        assert profile.name == "test-temp"
        assert profile.temporary is True
        assert "test-temp" in manager.profiles
        
        # Create another profile with same name (should return existing)
        profile2 = manager.create_profile("test-temp", temporary=False)
        assert profile2 == profile  # Same instance

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test browser manager as context manager."""
        with patch.object(BrowserManager, 'close_all_instances', new_callable=AsyncMock) as mock_close:
            async with BrowserManager() as manager:
                assert isinstance(manager, BrowserManager)
            
            mock_close.assert_called_once()


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_managed_browser(self):
        """Test managed browser context manager."""
        with patch('surfboard.automation.browser_manager.BrowserManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_instance = MagicMock()
            mock_instance.instance_id = "test-instance"
            
            mock_manager.create_instance = AsyncMock(return_value=mock_instance)
            mock_manager.close_instance = AsyncMock(return_value=True)
            mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
            mock_manager.__aexit__ = AsyncMock()
            
            mock_manager_class.return_value = mock_manager
            
            async with managed_browser(headless=True, profile="test") as instance:
                assert instance == mock_instance
            
            mock_manager.create_instance.assert_called_once()
            mock_manager.close_instance.assert_called_once_with("test-instance")

    @pytest.mark.asyncio  
    async def test_kill_all_chrome_processes(self):
        """Test killing all Chrome processes."""
        from surfboard.automation.browser_manager import kill_all_chrome_processes
        
        mock_processes = []
        
        # Mock Chrome process with debugging flag
        mock_chrome_proc = MagicMock()
        mock_chrome_proc.info = {
            'pid': 1234,
            'name': 'chrome',
            'cmdline': ['chrome', '--remote-debugging-port=9222']
        }
        mock_chrome_proc.kill = MagicMock()
        mock_processes.append(mock_chrome_proc)
        
        # Mock non-Chrome process
        mock_other_proc = MagicMock()
        mock_other_proc.info = {
            'pid': 5678,
            'name': 'firefox',
            'cmdline': ['firefox']
        }
        mock_other_proc.kill = MagicMock()
        mock_processes.append(mock_other_proc)
        
        # Mock Chrome process without debugging
        mock_regular_chrome = MagicMock()
        mock_regular_chrome.info = {
            'pid': 9999,
            'name': 'chrome',
            'cmdline': ['chrome', '--no-debugging']
        }
        mock_regular_chrome.kill = MagicMock()
        mock_processes.append(mock_regular_chrome)
        
        with patch('psutil.process_iter', return_value=mock_processes):
            killed_count = await kill_all_chrome_processes()
            
        assert killed_count == 1  # Only the debugging Chrome process
        mock_chrome_proc.kill.assert_called_once()
        mock_other_proc.kill.assert_not_called()
        mock_regular_chrome.kill.assert_not_called()