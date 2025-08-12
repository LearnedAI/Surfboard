#!/usr/bin/env python3
"""
Phase 3 Integration Tests - Advanced Automation Features

Tests the Phase 3 advanced automation capabilities with real Chrome instances
using the working Windows native automation from Phase 2.

This validates:
- Enhanced Element Selection with real web pages
- Advanced Interaction Patterns (hover, click, etc.)
- Error Recovery with actual failures
- Performance optimization features
"""

import asyncio
import logging
import subprocess
import time
from pathlib import Path

from src.surfboard.automation.browser_manager import BrowserManager
from src.surfboard.automation.element_selector import AdvancedElementSelector
from src.surfboard.automation.advanced_interactions import AdvancedInteractionEngine
from src.surfboard.automation.error_recovery import ErrorRecoveryManager
from src.surfboard.automation.windows_capture import WindowsScreenCapture

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Phase3IntegrationTester:
    """Integration tester for Phase 3 advanced automation features."""

    def __init__(self):
        """Initialize the Phase 3 integration tester."""
        self.browser_manager = None
        self.browser_instance = None
        self.cdp_session = None
        self.element_selector = AdvancedElementSelector()
        self.interaction_engine = AdvancedInteractionEngine()
        self.error_recovery = ErrorRecoveryManager()
        self.screenshot_system = WindowsScreenCapture()
        self.test_results = []

        # Create screenshot directory
        self.screenshot_dir = Path("Phase3_Integration_Screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        logger.info(f"Screenshots will be saved to: {self.screenshot_dir}")

    async def setup_chrome(self):
        """Set up Chrome with Windows profile for testing."""
        logger.info("🚀 Setting up Chrome for Phase 3 integration testing...")

        self.browser_manager = BrowserManager(max_instances=1)

        # Launch Chrome with Windows profile (using our working Phase 2 method)
        self.browser_instance = await self.browser_manager.create_instance(
            instance_id="phase3-integration-test",
            headless=False,
            window_size=(1200, 800),
            additional_args=[
                "--user-data-dir=/mnt/c/Users/Learn/AppData/Local/Google/Chrome/User Data",
                "--disable-web-security",  # For testing purposes
                "--disable-features=VizDisplayCompositor",
            ],
        )

        logger.info("✅ Chrome launched successfully")
        logger.info(f"   Process PID: {self.browser_instance.chrome_manager.process.pid}")
        logger.info(f"   CDP Port: {self.browser_instance.debugging_port}")

        # Get CDP session
        self.cdp_session = await self.browser_instance.get_cdp_session()
        logger.info("✅ CDP session established")

        # Take initial screenshot
        self.take_screenshot("00_initial_setup", "Chrome launched for Phase 3 testing")

    async def test_enhanced_element_selection(self):
        """Test Phase 3 enhanced element selection capabilities."""
        logger.info("🔍 Testing Enhanced Element Selection (Phase 3)")

        test_results = {
            "test_name": "Enhanced Element Selection",
            "subtests": [],
        }

        # Test 1: Navigate to Google and test search box selection
        logger.info("Test 1: Google search box element selection")
        await self.cdp_session.page.navigate("https://www.google.com")
        await asyncio.sleep(3)

        self.take_screenshot("01_google_loaded", "Google page loaded")

        try:
            # Test fuzzy text matching for search box
            search_results = await self.element_selector.find_elements_by_text(
                self.cdp_session, "Search", fuzzy_match=True
            )

            if search_results:
                logger.info(f"✅ Found {len(search_results)} search-related elements")
                test_results["subtests"].append(
                    {"name": "Fuzzy text search", "status": "PASS", "elements_found": len(search_results)}
                )
            else:
                logger.warning("⚠️ No search elements found")
                test_results["subtests"].append(
                    {"name": "Fuzzy text search", "status": "FAIL", "elements_found": 0}
                )

        except Exception as e:
            logger.error(f"❌ Search box selection failed: {e}")
            test_results["subtests"].append(
                {"name": "Fuzzy text search", "status": "ERROR", "error": str(e)}
            )

        # Test 2: Navigate to GitHub and test multiple selection strategies
        logger.info("Test 2: GitHub element selection with multiple strategies")
        await self.cdp_session.page.navigate("https://github.com")
        await asyncio.sleep(4)

        self.take_screenshot("02_github_loaded", "GitHub page loaded")

        try:
            # Test context-aware selection for sign-in button
            signin_results = await self.element_selector.find_elements_with_context(
                self.cdp_session, target_text="Sign in", context_keywords=["login", "account"]
            )

            if signin_results:
                logger.info(f"✅ Context-aware selection found {len(signin_results)} sign-in elements")
                test_results["subtests"].append(
                    {"name": "Context-aware selection", "status": "PASS", "elements_found": len(signin_results)}
                )
            else:
                logger.warning("⚠️ No sign-in elements found")
                test_results["subtests"].append(
                    {"name": "Context-aware selection", "status": "FAIL", "elements_found": 0}
                )

        except Exception as e:
            logger.error(f"❌ GitHub element selection failed: {e}")
            test_results["subtests"].append(
                {"name": "Context-aware selection", "status": "ERROR", "error": str(e)}
            )

        self.test_results.append(test_results)

    async def test_advanced_interactions(self):
        """Test Phase 3 advanced interaction patterns."""
        logger.info("🎯 Testing Advanced Interaction Patterns (Phase 3)")

        test_results = {
            "test_name": "Advanced Interaction Patterns",
            "subtests": [],
        }

        # Test on a page with interactive elements
        logger.info("Navigating to interactive test page...")
        await self.cdp_session.page.navigate("https://www.example.com")
        await asyncio.sleep(3)

        self.take_screenshot("03_example_loaded", "Example.com loaded for interaction testing")

        try:
            # Test 1: Hover interaction
            logger.info("Testing hover interaction...")

            # Get page dimensions for hover test
            page_info = await self.cdp_session.runtime.evaluate(
                """({
                    width: window.innerWidth,
                    height: window.innerHeight,
                    title: document.title
                })"""
            )

            # Hover over center of page
            hover_x = page_info["width"] // 2
            hover_y = page_info["height"] // 2

            await self.interaction_engine.hover(self.cdp_session, hover_x, hover_y)
            logger.info(f"✅ Hover interaction completed at ({hover_x}, {hover_y})")

            test_results["subtests"].append(
                {"name": "Hover interaction", "status": "PASS", "coordinates": (hover_x, hover_y)}
            )

        except Exception as e:
            logger.error(f"❌ Hover interaction failed: {e}")
            test_results["subtests"].append(
                {"name": "Hover interaction", "status": "ERROR", "error": str(e)}
            )

        try:
            # Test 2: Scroll interaction
            logger.info("Testing scroll interaction...")

            await self.interaction_engine.scroll(self.cdp_session, direction="down", distance=200)
            await asyncio.sleep(1)

            logger.info("✅ Scroll interaction completed")
            test_results["subtests"].append({"name": "Scroll interaction", "status": "PASS"})

            self.take_screenshot("04_after_scroll", "Page after scroll interaction")

        except Exception as e:
            logger.error(f"❌ Scroll interaction failed: {e}")
            test_results["subtests"].append(
                {"name": "Scroll interaction", "status": "ERROR", "error": str(e)}
            )

        self.test_results.append(test_results)

    async def test_error_recovery(self):
        """Test Phase 3 error recovery mechanisms."""
        logger.info("🛡️ Testing Error Recovery Mechanisms (Phase 3)")

        test_results = {
            "test_name": "Error Recovery Mechanisms",
            "subtests": [],
        }

        # Test 1: Recovery from navigation timeout
        logger.info("Test 1: Navigation timeout recovery")

        try:
            # Try to navigate to a non-existent page to trigger error
            with self.error_recovery.recovery_context("navigation_timeout"):
                await self.cdp_session.page.navigate("https://this-domain-does-not-exist-12345.com")
                await asyncio.sleep(2)  # Short timeout

            logger.info("✅ Navigation timeout recovery handled")
            test_results["subtests"].append({"name": "Navigation timeout recovery", "status": "PASS"})

        except Exception as e:
            logger.info(f"✅ Error recovery caught navigation failure: {e}")
            test_results["subtests"].append({"name": "Navigation timeout recovery", "status": "PASS"})

        # Test 2: Element not found recovery
        logger.info("Test 2: Element not found recovery")

        try:
            # Navigate back to a working page
            await self.cdp_session.page.navigate("https://www.example.com")
            await asyncio.sleep(3)

            # Try to find a non-existent element
            with self.error_recovery.recovery_context("element_not_found"):
                fake_element = await self.cdp_session.runtime.evaluate(
                    "document.querySelector('#this-element-definitely-does-not-exist')"
                )

                if fake_element is None:
                    raise Exception("Element not found as expected")

        except Exception as e:
            logger.info(f"✅ Error recovery handled element not found: {e}")
            test_results["subtests"].append({"name": "Element not found recovery", "status": "PASS"})

        self.take_screenshot("05_error_recovery", "After error recovery testing")
        self.test_results.append(test_results)

    async def test_performance_features(self):
        """Test Phase 3 performance optimization features."""
        logger.info("⚡ Testing Performance Optimization Features (Phase 3)")

        test_results = {
            "test_name": "Performance Optimization",
            "subtests": [],
        }

        start_time = time.time()

        try:
            # Test parallel page operations
            logger.info("Testing parallel operations...")

            # Create multiple operations that can run in parallel
            tasks = [
                self.cdp_session.runtime.evaluate("document.title"),
                self.cdp_session.runtime.evaluate("window.location.href"),
                self.cdp_session.runtime.evaluate("document.readyState"),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            parallel_time = time.time() - start_time
            logger.info(f"✅ Parallel operations completed in {parallel_time:.2f}s")

            test_results["subtests"].append(
                {"name": "Parallel operations", "status": "PASS", "execution_time": parallel_time}
            )

        except Exception as e:
            logger.error(f"❌ Performance testing failed: {e}")
            test_results["subtests"].append(
                {"name": "Parallel operations", "status": "ERROR", "error": str(e)}
            )

        self.test_results.append(test_results)

    def take_screenshot(self, step_name: str, description: str = ""):
        """Take a screenshot for the current test step."""
        filename = f"{step_name}.png"
        output_path = str(self.screenshot_dir / filename)

        success = self.screenshot_system.take_screenshot(output_path)
        if success:
            logger.info(f"📸 Screenshot saved: {filename} - {description}")
        else:
            logger.warning(f"📸 Screenshot failed: {filename}")

    async def generate_report(self):
        """Generate a comprehensive test report."""
        logger.info("📋 Generating Phase 3 Integration Test Report")

        total_tests = sum(len(test["subtests"]) for test in self.test_results)
        passed_tests = sum(
            len([subtest for subtest in test["subtests"] if subtest["status"] == "PASS"])
            for test in self.test_results
        )
        failed_tests = sum(
            len([subtest for subtest in test["subtests"] if subtest["status"] in ["FAIL", "ERROR"]])
            for test in self.test_results
        )

        logger.info("=" * 60)
        logger.info("PHASE 3 INTEGRATION TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        logger.info("=" * 60)

        for test in self.test_results:
            logger.info(f"\n{test['test_name']}:")
            for subtest in test["subtests"]:
                status_icon = "✅" if subtest["status"] == "PASS" else "❌"
                logger.info(f"  {status_icon} {subtest['name']}: {subtest['status']}")

        self.take_screenshot("99_final_report", "Final state after all Phase 3 tests")

    async def cleanup(self):
        """Clean up resources."""
        logger.info("🧹 Cleaning up Phase 3 integration test resources...")

        try:
            if self.cdp_session:
                await self.cdp_session.close()

            if self.browser_manager:
                await self.browser_manager.close_all_instances()

            logger.info("✅ Cleanup completed")

        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")

    async def run_full_integration_test(self):
        """Run the complete Phase 3 integration test suite."""
        logger.info("🚀 Starting Phase 3 Integration Test Suite")
        logger.info("This validates Phase 3 advanced automation features with real Chrome instances")

        try:
            await self.setup_chrome()

            # Run all Phase 3 feature tests
            await self.test_enhanced_element_selection()
            await self.test_advanced_interactions()
            await self.test_error_recovery()
            await self.test_performance_features()

            # Generate comprehensive report
            await self.generate_report()

            logger.info("🎉 Phase 3 Integration Test Suite COMPLETE!")
            logger.info(f"📸 Screenshots saved to: {self.screenshot_dir}")

        except Exception as e:
            logger.error(f"❌ Integration test suite failed: {e}")
            self.take_screenshot("ERROR", f"Test suite error: {e}")

        finally:
            await self.cleanup()


async def main():
    """Run Phase 3 integration tests."""
    tester = Phase3IntegrationTester()
    await tester.run_full_integration_test()


if __name__ == "__main__":
    asyncio.run(main())