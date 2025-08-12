"""
Enhanced Chrome Profile Management Helper
Combines insights from Chromite approach with current Surfboard system
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from surfboard.automation.browser_manager import BrowserManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChromeProfileHelper:
    """Helper class for Chrome profile management with WSL/Windows integration."""

    def __init__(self):
        self.detected_profiles = {}
        self._scan_complete = False

    def detect_windows_profiles(self) -> Dict[str, Path]:
        """Detect Windows Chrome profiles accessible from WSL."""
        profiles = {}

        # Common Windows profile locations accessible via WSL
        base_paths = [
            Path("/mnt/c/Users/Learn/AppData/Local/Google/Chrome/User Data"),
            Path("/mnt/c/Users/Learn/AppData/Roaming/Google/Chrome/User Data"),
        ]

        for base_path in base_paths:
            if base_path.exists():
                logger.info(f"Found Chrome User Data directory: {base_path}")

                # Check for profiles
                profile_dirs = [
                    "Default",
                    "Profile 1",
                    "Profile 2",
                    "Profile 3",
                    "Guest Profile",
                ]

                for profile_name in profile_dirs:
                    profile_path = base_path / profile_name
                    if profile_path.exists():
                        profiles[profile_name] = profile_path
                        logger.info(f"  - Found profile: {profile_name}")

        self.detected_profiles = profiles
        self._scan_complete = True
        return profiles

    def get_default_profile_path(self) -> Optional[Path]:
        """Get the default Windows Chrome profile path."""
        if not self._scan_complete:
            self.detect_windows_profiles()

        # Prefer Default profile, fallback to first available
        if "Default" in self.detected_profiles:
            return self.detected_profiles["Default"].parent
        elif self.detected_profiles:
            return list(self.detected_profiles.values())[0].parent
        return None

    def list_available_profiles(self) -> Dict[str, Dict[str, Any]]:
        """List all available Chrome profiles with metadata."""
        if not self._scan_complete:
            self.detect_windows_profiles()

        profile_info = {}
        for name, path in self.detected_profiles.items():
            info = {
                "path": path,
                "parent": path.parent,
                "exists": path.exists(),
                "preferences_file": path / "Preferences",
                "has_preferences": (path / "Preferences").exists(),
            }

            # Try to read profile name from preferences
            if info["has_preferences"]:
                try:
                    import json

                    with open(info["preferences_file"], "r", encoding="utf-8") as f:
                        prefs = json.load(f)
                        profile_name = prefs.get("profile", {}).get("name", name)
                        info["display_name"] = profile_name
                except Exception as e:
                    logger.debug(f"Could not read preferences for {name}: {e}")
                    info["display_name"] = name
            else:
                info["display_name"] = name

            profile_info[name] = info

        return profile_info


async def create_chrome_with_windows_profile(
    instance_id: str = "windows-profile-chrome",
    profile_name: str = "Default",
    headless: bool = False,
    window_size: tuple = (1200, 800),
) -> Any:
    """Create Chrome instance using Windows profile."""

    helper = ChromeProfileHelper()
    profiles = helper.detect_windows_profiles()

    if not profiles:
        raise ValueError("No Windows Chrome profiles found")

    if profile_name not in profiles:
        available = list(profiles.keys())
        raise ValueError(f"Profile '{profile_name}' not found. Available: {available}")

    profile_path = profiles[profile_name].parent
    logger.info(f"Using Windows Chrome profile: {profile_path}")

    # Create browser manager
    manager = BrowserManager(max_instances=1)

    # Create Chrome instance with Windows profile
    browser = await manager.create_instance(
        instance_id=instance_id,
        headless=headless,
        window_size=window_size,
        additional_args=[
            f"--user-data-dir={profile_path}",
            # Additional args from Chromite approach for better compatibility
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-blink-features=AutomationControlled",
            "--exclude-switches=enable-automation",
        ],
    )

    logger.info(f"✅ Chrome instance created with Windows profile!")
    logger.info(f"   Instance ID: {browser.instance_id}")
    logger.info(f"   CDP Port: {browser.debugging_port}")
    logger.info(f"   Profile: {profile_path}")

    return browser, manager


async def demo_windows_profile_integration():
    """Demo the Windows profile integration."""

    logger.info("=== Chrome Windows Profile Integration Demo ===")

    # Discover profiles
    helper = ChromeProfileHelper()
    profiles = helper.detect_windows_profiles()

    if not profiles:
        logger.error("❌ No Windows Chrome profiles found")
        return

    logger.info(f"Found {len(profiles)} Chrome profiles:")
    profile_info = helper.list_available_profiles()

    for name, info in profile_info.items():
        logger.info(f"  - {name}: {info['display_name']}")
        logger.info(f"    Path: {info['path']}")
        logger.info(f"    Has preferences: {info['has_preferences']}")

    # Try to create Chrome with Default profile
    try:
        browser, manager = await create_chrome_with_windows_profile(
            instance_id="demo-windows-profile",
            profile_name="Default",
            headless=False,
            window_size=(1200, 800),
        )

        logger.info(
            "Chrome launched with Windows profile - you should see your bookmarks!"
        )
        logger.info("Waiting 10 seconds to observe...")
        await asyncio.sleep(10)

        # Test navigation
        session = await browser.get_cdp_session()
        logger.info("Testing navigation with profile...")

        await session.page.navigate("https://google.com")
        await asyncio.sleep(3)

        title = await session.runtime.evaluate("document.title")
        logger.info(f"Page title: {title}")

        await session.close()
        await manager.close_all_instances()
        logger.info("✅ Demo complete!")

    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(demo_windows_profile_integration())
