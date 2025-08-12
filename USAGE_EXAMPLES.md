# Surfboard Phase 2 - Usage Examples

## Quick Start with Windows Chrome Profile

### Basic Chrome Automation with Your Windows Profile

```python
import asyncio
from surfboard.automation.browser_manager import BrowserManager

async def basic_example():
    """Launch Chrome with Windows profile and navigate."""

    # Create browser manager
    manager = BrowserManager(max_instances=1)

    try:
        # Launch Chrome with your Windows profile
        browser = await manager.create_instance(
            instance_id="my-browser",
            headless=False,  # Visible window
            window_size=(1200, 800),
            additional_args=[
                "--user-data-dir=/mnt/c/Users/Learn/AppData/Local/Google/Chrome/User Data"
            ]
        )

        print(f"✅ Chrome launched with profile!")
        print(f"   Process PID: {browser.chrome_manager.process.pid}")

        # Get CDP session for automation
        session = await browser.get_cdp_session()

        # Navigate to a page
        await session.page.navigate("https://google.com")
        await asyncio.sleep(2)

        # Get page title
        title = await session.runtime.evaluate("document.title")
        print(f"Page title: {title}")

        # Close session
        await session.close()

    finally:
        # Always clean up
        await manager.close_all_instances()

# Run the example
asyncio.run(basic_example())
```

### Using the Profile Helper

```python
import asyncio
from profile_helper import create_chrome_with_windows_profile

async def profile_helper_example():
    """Use the profile helper for easier setup."""

    browser, manager = await create_chrome_with_windows_profile(
        instance_id="profile-demo",
        profile_name="Default",  # Your main profile
        headless=False,
        window_size=(1400, 900)
    )

    try:
        # Browser opens with your bookmarks, extensions, saved passwords
        print("Chrome opened with your Windows profile!")

        # Automate as needed...
        session = await browser.get_cdp_session()
        await session.page.navigate("https://github.com")

        # If you're logged into GitHub, you should see your account
        await asyncio.sleep(5)

        await session.close()

    finally:
        await manager.close_all_instances()

asyncio.run(profile_helper_example())
```

### Profile Discovery

```python
import asyncio
from profile_helper import ChromeProfileHelper

async def discover_profiles():
    """Discover all available Chrome profiles."""

    helper = ChromeProfileHelper()
    profiles = helper.detect_windows_profiles()

    print(f"Found {len(profiles)} Chrome profiles:")

    profile_info = helper.list_available_profiles()
    for name, info in profile_info.items():
        print(f"\n📁 {name}")
        print(f"   Display Name: {info['display_name']}")
        print(f"   Path: {info['path']}")
        print(f"   Has Settings: {info['has_preferences']}")

asyncio.run(discover_profiles())
```

## Advanced Usage Patterns

### Multiple Browser Instances

```python
import asyncio
from surfboard.automation.browser_manager import BrowserManager

async def multiple_browsers():
    """Manage multiple Chrome instances."""

    manager = BrowserManager(max_instances=3)
    profile_path = "/mnt/c/Users/Learn/AppData/Local/Google/Chrome/User Data"

    try:
        # Create multiple instances
        browsers = []
        for i in range(2):
            browser = await manager.create_instance(
                instance_id=f"browser-{i+1}",
                headless=False,
                additional_args=[f"--user-data-dir={profile_path}"]
            )
            browsers.append(browser)

        # Each browser runs in its own process
        for i, browser in enumerate(browsers):
            session = await browser.get_cdp_session()
            await session.page.navigate(f"https://httpbin.org/get?instance={i+1}")
            await session.close()

        print(f"Created {len(browsers)} Chrome instances")

    finally:
        await manager.close_all_instances()

asyncio.run(multiple_browsers())
```

### Form Automation with Profile

```python
import asyncio
from profile_helper import create_chrome_with_windows_profile

async def form_automation():
    """Automate form filling with saved profile data."""

    browser, manager = await create_chrome_with_windows_profile(
        instance_id="form-filler",
        headless=False
    )

    try:
        session = await browser.get_cdp_session()

        # Navigate to a form page
        await session.page.navigate("https://httpbin.org/forms/post")
        await asyncio.sleep(2)

        # Chrome may auto-fill if you have saved data
        # Or you can fill programmatically:
        await session.runtime.evaluate("""
            document.querySelector('input[name="custname"]').value = 'John Doe';
            document.querySelector('input[name="custtel"]').value = '555-1234';
        """)

        print("Form filled successfully!")
        await asyncio.sleep(3)

        await session.close()

    finally:
        await manager.close_all_instances()

asyncio.run(form_automation())
```

## Troubleshooting

### Common Issues

1. **Chrome doesn't appear**: Check if `headless=False` is set
2. **Profile not found**: Verify the path exists: `/mnt/c/Users/Learn/AppData/Local/Google/Chrome/User Data`
3. **Permission errors**: Make sure Chrome isn't already running
4. **CDP timeout**: Chrome may take time to start, increase timeouts if needed

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.INFO)

# Run any example above with detailed logging
```

### Verify Setup

```python
# Quick verification script
import asyncio
from surfboard.automation.browser_manager import BrowserManager

async def verify():
    manager = BrowserManager()
    browser = await manager.create_instance(headless=False)
    print("✅ Surfboard Chrome integration working!")
    await manager.close_all_instances()

asyncio.run(verify())
```

## What You Get with Windows Profile Integration

When Chrome launches with your Windows profile, you automatically get:

- 🔖 **Your bookmarks** - All your saved bookmarks appear
- 🔑 **Saved passwords** - Auto-login to sites you've saved
- 🧩 **Extensions** - Ad blockers, password managers, etc.
- 🎨 **Themes & settings** - Your custom Chrome appearance
- 📱 **Sync data** - If you use Chrome sync across devices
- 🍪 **Cookies & sessions** - Stay logged into websites
- 📝 **Form data** - Auto-complete forms with saved information

This makes Surfboard automation feel natural and integrated with your existing workflow!
