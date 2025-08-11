"""
Browser automation and lifecycle management.

This module handles launching Chrome with proper debugging flags,
managing browser instances, and coordinating with CDP connections.
"""

import asyncio
import logging
import os
import platform
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Optional

import psutil

from ..protocols.cdp import get_chrome_version, test_chrome_connection

logger = logging.getLogger(__name__)


class ChromeLaunchError(Exception):
    """Exception raised when Chrome fails to launch."""

    pass


class ChromeManager:
    """Manages Chrome browser instances for automation."""

    def __init__(self, debugging_port: int = 9222, headless: bool = False):
        """Initialize Chrome manager.

        Args:
            debugging_port: Port for Chrome remote debugging
            headless: Whether to run Chrome in headless mode
        """
        self.debugging_port = debugging_port
        self.headless = headless
        self.process: Optional[subprocess.Popen] = None
        self.user_data_dir: Optional[Path] = None
        self._cleanup_registered = False

    async def launch(self, additional_args: Optional[List[str]] = None) -> None:
        """Launch Chrome with debugging enabled.

        Args:
            additional_args: Additional Chrome command line arguments

        Raises:
            ChromeLaunchError: If Chrome fails to launch
        """
        if self.is_running():
            logger.info("Chrome is already running")
            return

        # Create temporary user data directory
        self.user_data_dir = Path(tempfile.mkdtemp(prefix="surfboard-chrome-"))

        try:
            chrome_path = self._find_chrome_executable()
            if not chrome_path:
                raise ChromeLaunchError("Chrome executable not found")

            # Build command line arguments
            chrome_args = self._build_chrome_args(additional_args or [])

            logger.info(f"Launching Chrome from {chrome_path}")
            logger.debug(f"Chrome arguments: {chrome_args}")

            # Launch Chrome process
            self.process = subprocess.Popen(
                [chrome_path] + chrome_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            # Wait for Chrome to be ready
            await self._wait_for_chrome_ready()

            logger.info(f"Chrome launched successfully (PID: {self.process.pid})")

        except Exception as e:
            await self.cleanup()
            raise ChromeLaunchError(f"Failed to launch Chrome: {e}") from e

    def is_running(self) -> bool:
        """Check if Chrome is running and accessible.

        Returns:
            True if Chrome is running and debugging port is accessible
        """
        if self.process and self.process.poll() is None:
            # Process is running, but we need to check debugging port
            # Since we can't use asyncio.run from async context, just check process
            return True
        return False

    async def is_running_async(self) -> bool:
        """Async version of is_running that can test CDP connection.

        Returns:
            True if Chrome is running and debugging port is accessible
        """
        if self.process and self.process.poll() is None:
            # Process is running, test if debugging port is accessible
            return await test_chrome_connection(port=self.debugging_port)
        return False

    async def cleanup(self) -> None:
        """Stop Chrome and cleanup resources."""
        if self.process:
            try:
                # Terminate Chrome process
                if self.process.poll() is None:
                    self.process.terminate()

                    # Wait for graceful shutdown
                    try:
                        await asyncio.wait_for(
                            asyncio.to_thread(self.process.wait), timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Chrome didn't shutdown gracefully, killing...")
                        self.process.kill()
                        await asyncio.to_thread(self.process.wait)

                logger.info("Chrome process stopped")

            except Exception as e:
                logger.error(f"Error stopping Chrome: {e}")
            finally:
                self.process = None

        # Cleanup user data directory
        if self.user_data_dir and self.user_data_dir.exists():
            try:
                shutil.rmtree(self.user_data_dir)
                logger.debug(f"Cleaned up user data directory: {self.user_data_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup user data directory: {e}")
            finally:
                self.user_data_dir = None

    def _find_chrome_executable(self) -> Optional[str]:
        """Find Chrome executable path on current platform.

        Returns:
            Path to Chrome executable or None if not found
        """
        system = platform.system().lower()

        if system == "windows":
            # Windows Chrome locations
            possible_paths = [
                os.path.expandvars(
                    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
                ),
                os.path.expandvars(
                    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
                ),
                os.path.expandvars(
                    r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
                ),
            ]
        elif system == "darwin":
            # macOS Chrome locations
            possible_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ]
        else:
            # Linux Chrome locations
            possible_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/snap/bin/chromium",
            ]

        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        # Try to find via PATH
        import shutil as sh

        chrome_names = [
            "chrome",
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
        ]
        for name in chrome_names:
            path = sh.which(name)
            if path:
                return path

        return None

    def _build_chrome_args(self, additional_args: List[str]) -> List[str]:
        """Build Chrome command line arguments.

        Args:
            additional_args: Additional arguments to include

        Returns:
            List of Chrome command line arguments
        """
        args = [
            f"--remote-debugging-port={self.debugging_port}",
            f"--user-data-dir={self.user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI,BlinkGenPropertyTrees",
            "--disable-client-side-phishing-detection",
            "--disable-sync",
            "--disable-background-networking",
            "--metrics-recording-only",
            "--no-report-upload",
            "--safebrowsing-disable-auto-update",
            "--enable-automation",
            "--password-store=basic",
            "--use-mock-keychain",
        ]

        if self.headless:
            args.extend(
                [
                    "--headless=new",  # Use new headless mode
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",  # Note: reduces security but needed for some environments
                ]
            )

        # Add additional arguments
        args.extend(additional_args)

        return args

    async def _wait_for_chrome_ready(self, timeout: float = 30.0) -> None:
        """Wait for Chrome to be ready for connections.

        Args:
            timeout: Maximum time to wait in seconds

        Raises:
            ChromeLaunchError: If Chrome doesn't become ready in time
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if await test_chrome_connection(port=self.debugging_port):
                # Additional verification - get version info
                version_info = await get_chrome_version(port=self.debugging_port)
                if version_info:
                    logger.info(
                        f"Chrome ready - {version_info.get('Browser', 'Unknown version')}"
                    )
                    return

            await asyncio.sleep(0.5)

        raise ChromeLaunchError(f"Chrome didn't become ready within {timeout} seconds")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.launch()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()


async def launch_chrome_for_testing(
    port: int = 9222, headless: bool = True
) -> ChromeManager:
    """Launch Chrome instance optimized for testing.

    Args:
        port: Debugging port to use
        headless: Whether to run headless

    Returns:
        ChromeManager instance with Chrome running

    Raises:
        ChromeLaunchError: If Chrome fails to launch
    """
    manager = ChromeManager(debugging_port=port, headless=headless)
    await manager.launch(
        [
            "--disable-web-security",  # For testing cross-origin requests
            "--disable-features=VizDisplayCompositor",  # Reduce resource usage
        ]
    )
    return manager


async def kill_existing_chrome_processes() -> int:
    """Kill any existing Chrome processes that might interfere.

    Returns:
        Number of processes killed
    """
    killed_count = 0

    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                process_info = proc.info
                name = process_info["name"]
                cmdline = process_info.get("cmdline", [])

                # Check if this is a Chrome process we should kill
                if name and ("chrome" in name.lower() or "chromium" in name.lower()):
                    # Only kill if it has debugging port in cmdline
                    if any("--remote-debugging-port" in arg for arg in cmdline):
                        proc.kill()
                        killed_count += 1
                        logger.info(f"Killed Chrome process {proc.pid}")

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process might have died or we don't have permission
                pass

    except Exception as e:
        logger.warning(f"Error killing Chrome processes: {e}")

    return killed_count
