"""
Tests for Chrome browser launching and management.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from surfboard.automation.browser import (
    ChromeManager,
    kill_existing_chrome_processes,
    launch_chrome_for_testing,
)


class TestChromeManager:
    """Test Chrome manager functionality."""

    def test_initialization(self):
        """Test Chrome manager initialization."""
        manager = ChromeManager(debugging_port=9333, headless=True)

        assert manager.debugging_port == 9333
        assert manager.headless is True
        assert manager.process is None
        assert manager.user_data_dir is None

    @patch("platform.system")
    def test_find_chrome_executable_windows(self, mock_system):
        """Test finding Chrome executable on Windows."""
        mock_system.return_value = "Windows"

        manager = ChromeManager()

        with patch("os.path.isfile") as mock_isfile, patch("os.access") as mock_access:
            mock_isfile.return_value = True
            mock_access.return_value = True

            # Mock first Windows path
            with patch("os.path.expandvars") as mock_expandvars:
                mock_expandvars.return_value = (
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                )

                result = manager._find_chrome_executable()

                assert (
                    result == r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                )

    @patch("platform.system")
    def test_find_chrome_executable_linux(self, mock_system):
        """Test finding Chrome executable on Linux."""
        mock_system.return_value = "Linux"

        manager = ChromeManager()

        with patch("os.path.isfile") as mock_isfile, patch("os.access") as mock_access:

            def isfile_side_effect(path):
                return path == "/usr/bin/google-chrome"

            mock_isfile.side_effect = isfile_side_effect
            mock_access.return_value = True

            result = manager._find_chrome_executable()

            assert result == "/usr/bin/google-chrome"

    def test_build_chrome_args_basic(self):
        """Test building basic Chrome arguments."""
        manager = ChromeManager(debugging_port=9222, headless=False)
        manager.user_data_dir = Path("/tmp/test-chrome")

        args = manager._build_chrome_args([])

        assert "--remote-debugging-port=9222" in args
        assert "--user-data-dir=/tmp/test-chrome" in args
        assert "--no-first-run" in args
        assert "--enable-automation" in args

        # Should not have headless args
        assert "--headless=new" not in args

    def test_build_chrome_args_headless(self):
        """Test building Chrome arguments for headless mode."""
        manager = ChromeManager(debugging_port=9222, headless=True)
        manager.user_data_dir = Path("/tmp/test-chrome")

        args = manager._build_chrome_args([])

        assert "--headless=new" in args
        assert "--disable-gpu" in args
        assert "--no-sandbox" in args

    def test_build_chrome_args_additional(self):
        """Test building Chrome arguments with additional args."""
        manager = ChromeManager()
        manager.user_data_dir = Path("/tmp/test-chrome")

        additional_args = ["--disable-web-security", "--window-size=1920,1080"]
        args = manager._build_chrome_args(additional_args)

        assert "--disable-web-security" in args
        assert "--window-size=1920,1080" in args

    def test_is_running_with_process(self):
        """Test is_running when process exists."""
        manager = ChromeManager()
        manager.process = MagicMock()
        manager.process.poll.return_value = None  # Process is running

        result = manager.is_running()

        assert result is True

    def test_is_running_without_process(self):
        """Test is_running when no process exists."""
        manager = ChromeManager()
        manager.process = None

        result = manager.is_running()

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_with_running_process(self):
        """Test cleanup with running Chrome process."""
        manager = ChromeManager()

        # Mock running process - use regular MagicMock since we're not awaiting the calls
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running

        # Mock asyncio.to_thread for process.wait()
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = 0  # Process exited successfully
            manager.process = mock_process

            # Mock temporary directory
            with patch("shutil.rmtree") as mock_rmtree, patch(
                "pathlib.Path.exists"
            ) as mock_exists:
                manager.user_data_dir = Path("/tmp/test")
                mock_exists.return_value = True

                await manager.cleanup()

                mock_process.terminate.assert_called_once()
                mock_rmtree.assert_called_once_with(Path("/tmp/test"))
                assert manager.process is None
                assert manager.user_data_dir is None

    @pytest.mark.asyncio
    async def test_cleanup_with_dead_process(self):
        """Test cleanup when process is already dead."""
        manager = ChromeManager()

        # Mock dead process
        mock_process = MagicMock()
        mock_process.poll.return_value = 0  # Process is dead
        manager.process = mock_process

        await manager.cleanup()

        mock_process.terminate.assert_not_called()
        assert manager.process is None


@pytest.mark.asyncio
@patch("surfboard.automation.browser.ChromeManager.launch")
async def test_launch_chrome_for_testing(mock_launch):
    """Test launch_chrome_for_testing function."""
    mock_launch.return_value = None

    manager = await launch_chrome_for_testing(port=9333, headless=False)

    assert manager.debugging_port == 9333
    assert manager.headless is False
    mock_launch.assert_called_once()

    # Check additional args were passed
    call_args = mock_launch.call_args[0][0]
    assert "--disable-web-security" in call_args


@pytest.mark.asyncio
@patch("psutil.process_iter")
async def test_kill_existing_chrome_processes(mock_process_iter):
    """Test killing existing Chrome processes."""
    # Mock Chrome processes
    mock_chrome_proc = MagicMock()
    mock_chrome_proc.info = {
        "pid": 1234,
        "name": "chrome",
        "cmdline": ["chrome", "--remote-debugging-port=9222"],
    }

    mock_other_proc = MagicMock()
    mock_other_proc.info = {"pid": 5678, "name": "firefox", "cmdline": ["firefox"]}

    mock_process_iter.return_value = [mock_chrome_proc, mock_other_proc]

    killed_count = await kill_existing_chrome_processes()

    assert killed_count == 1
    mock_chrome_proc.kill.assert_called_once()
    mock_other_proc.kill.assert_not_called()


# Integration test for real Chrome launching (marked for manual testing)
@pytest.mark.manual
@pytest.mark.asyncio
async def test_real_chrome_launch():
    """
    Integration test for real Chrome launching.

    This test requires Chrome to be installed.
    Mark with @pytest.mark.manual to exclude from automatic test runs.
    """
    # Kill any existing Chrome processes first
    await kill_existing_chrome_processes()

    # Test launching Chrome
    async with ChromeManager(debugging_port=9999, headless=True) as manager:
        # Verify Chrome is running
        assert manager.is_running()

        # Test CDP connection
        from surfboard.protocols.cdp import CDPClient

        async with CDPClient(port=9999) as client:
            # Test basic operation
            result = await client.send_command(
                "Runtime.evaluate",
                {"expression": "navigator.userAgent", "returnByValue": True},
            )

            # Handle both possible result structures
            user_agent = result.get("value") or result.get("result", {}).get(
                "value", ""
            )
            assert "Chrome" in str(user_agent)
