"""
Enhanced browser lifecycle management system.

This module provides comprehensive browser management with multiple instance support,
profile management, and advanced configuration options.
"""

import asyncio
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import asynccontextmanager

import psutil

from .browser import ChromeManager
from ..protocols.cdp import CDPClient
from ..protocols.cdp_domains import CDPSession

logger = logging.getLogger(__name__)


class BrowserInstance:
    """Represents a managed browser instance."""
    
    def __init__(
        self,
        instance_id: str,
        manager: ChromeManager,
        cdp_client: Optional[CDPClient] = None,
        profile_path: Optional[Path] = None
    ):
        """Initialize browser instance.
        
        Args:
            instance_id: Unique instance identifier
            manager: Chrome manager
            cdp_client: CDP client connection
            profile_path: Profile directory path
        """
        self.instance_id = instance_id
        self.manager = manager
        self.cdp_client = cdp_client
        self.profile_path = profile_path
        self.created_at = asyncio.get_event_loop().time()
        self.last_activity = self.created_at
        
    @property
    def is_running(self) -> bool:
        """Check if browser instance is running."""
        return self.manager.is_running()
        
    @property
    def debugging_port(self) -> int:
        """Get debugging port."""
        return self.manager.debugging_port
        
    async def get_cdp_session(self) -> CDPSession:
        """Get high-level CDP session."""
        if not self.cdp_client:
            self.cdp_client = CDPClient(port=self.debugging_port)
            await self.cdp_client.connect()
        
        from ..protocols.cdp_domains import CDPSession
        return CDPSession(self.cdp_client)
        
    async def cleanup(self) -> None:
        """Clean up browser instance."""
        if self.cdp_client:
            await self.cdp_client.disconnect()
            
        await self.manager.cleanup()
        
        # Clean up profile if it was temporary
        if self.profile_path and self.profile_path.name.startswith("surfboard_temp_"):
            try:
                shutil.rmtree(self.profile_path)
                logger.debug(f"Cleaned up temporary profile: {self.profile_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up profile {self.profile_path}: {e}")


class BrowserProfile:
    """Browser profile management."""
    
    def __init__(self, name: str, path: Path, temporary: bool = False):
        """Initialize browser profile.
        
        Args:
            name: Profile name
            path: Profile directory path
            temporary: Whether profile is temporary
        """
        self.name = name
        self.path = path
        self.temporary = temporary
        
    @classmethod
    def create_temporary(cls, name: str) -> "BrowserProfile":
        """Create temporary profile.
        
        Args:
            name: Profile name
            
        Returns:
            Temporary profile instance
        """
        temp_dir = Path(tempfile.mkdtemp(prefix=f"surfboard_temp_{name}_"))
        return cls(name=name, path=temp_dir, temporary=True)
        
    @classmethod
    def create_persistent(cls, name: str, base_dir: Optional[Path] = None) -> "BrowserProfile":
        """Create persistent profile.
        
        Args:
            name: Profile name
            base_dir: Base directory for profiles
            
        Returns:
            Persistent profile instance
        """
        if not base_dir:
            base_dir = Path.home() / ".surfboard" / "profiles"
            
        profile_dir = base_dir / name
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        return cls(name=name, path=profile_dir, temporary=False)
        
    def configure_preferences(self, preferences: Dict[str, Any]) -> None:
        """Configure Chrome preferences.
        
        Args:
            preferences: Chrome preferences dictionary
        """
        prefs_file = self.path / "Default" / "Preferences"
        prefs_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(prefs_file, 'w') as f:
            json.dump(preferences, f, indent=2)
            
        logger.debug(f"Configured preferences for profile {self.name}")
        
    def cleanup(self) -> None:
        """Clean up profile if temporary."""
        if self.temporary and self.path.exists():
            try:
                shutil.rmtree(self.path)
                logger.debug(f"Cleaned up temporary profile: {self.name}")
            except Exception as e:
                logger.warning(f"Failed to clean up profile {self.name}: {e}")


class BrowserManager:
    """Enhanced browser lifecycle management."""
    
    def __init__(self, max_instances: int = 5):
        """Initialize browser manager.
        
        Args:
            max_instances: Maximum number of concurrent browser instances
        """
        self.max_instances = max_instances
        self.instances: Dict[str, BrowserInstance] = {}
        self.profiles: Dict[str, BrowserProfile] = {}
        self._port_counter = 9222
        self._lock = asyncio.Lock()
        
    async def create_instance(
        self,
        instance_id: Optional[str] = None,
        profile: Optional[Union[str, BrowserProfile]] = None,
        headless: bool = True,
        window_size: Optional[Tuple[int, int]] = None,
        user_agent: Optional[str] = None,
        additional_args: Optional[List[str]] = None,
        auto_connect_cdp: bool = True
    ) -> BrowserInstance:
        """Create new browser instance.
        
        Args:
            instance_id: Instance identifier (auto-generated if None)
            profile: Profile name or BrowserProfile instance
            headless: Whether to run in headless mode
            window_size: Browser window size (width, height)
            user_agent: Custom user agent
            additional_args: Additional Chrome arguments
            auto_connect_cdp: Whether to automatically connect CDP
            
        Returns:
            Browser instance
            
        Raises:
            RuntimeError: If maximum instances exceeded
        """
        async with self._lock:
            if len(self.instances) >= self.max_instances:
                raise RuntimeError(f"Maximum instances ({self.max_instances}) exceeded")
                
            # Generate instance ID if not provided
            if not instance_id:
                instance_id = f"browser_{len(self.instances) + 1}"
                
            # Get available port
            port = await self._get_available_port()
            
            # Handle profile
            profile_path = None
            if isinstance(profile, str):
                if profile not in self.profiles:
                    self.profiles[profile] = BrowserProfile.create_temporary(profile)
                profile_obj = self.profiles[profile]
                profile_path = profile_obj.path
            elif isinstance(profile, BrowserProfile):
                profile_path = profile.path
                self.profiles[profile.name] = profile
                
            # Build Chrome arguments
            chrome_args = additional_args or []
            
            if window_size:
                chrome_args.append(f"--window-size={window_size[0]},{window_size[1]}")
                
            if user_agent:
                chrome_args.append(f"--user-agent={user_agent}")
                
            # Create Chrome manager
            manager = ChromeManager(
                debugging_port=port,
                headless=headless
            )
            
            try:
                # Launch Chrome
                await manager.launch(chrome_args)
                
                # Create CDP client if requested
                cdp_client = None
                if auto_connect_cdp:
                    cdp_client = CDPClient(port=port)
                    await cdp_client.connect()
                    
                # Create instance
                instance = BrowserInstance(
                    instance_id=instance_id,
                    manager=manager,
                    cdp_client=cdp_client,
                    profile_path=profile_path
                )
                
                self.instances[instance_id] = instance
                logger.info(f"Created browser instance: {instance_id} on port {port}")
                
                return instance
                
            except Exception:
                # Clean up on failure
                await manager.cleanup()
                raise
                
    async def get_instance(self, instance_id: str) -> Optional[BrowserInstance]:
        """Get browser instance by ID.
        
        Args:
            instance_id: Instance identifier
            
        Returns:
            Browser instance if found, None otherwise
        """
        return self.instances.get(instance_id)
        
    async def close_instance(self, instance_id: str) -> bool:
        """Close browser instance.
        
        Args:
            instance_id: Instance identifier
            
        Returns:
            True if closed, False if not found
        """
        async with self._lock:
            if instance_id not in self.instances:
                return False
                
            instance = self.instances[instance_id]
            await instance.cleanup()
            
            del self.instances[instance_id]
            logger.info(f"Closed browser instance: {instance_id}")
            
            return True
            
    async def close_all_instances(self) -> int:
        """Close all browser instances.
        
        Returns:
            Number of instances closed
        """
        instance_ids = list(self.instances.keys())
        closed_count = 0
        
        for instance_id in instance_ids:
            if await self.close_instance(instance_id):
                closed_count += 1
                
        return closed_count
        
    async def list_instances(self) -> List[Dict[str, Any]]:
        """List all browser instances.
        
        Returns:
            List of instance information dictionaries
        """
        instances_info = []
        
        for instance_id, instance in self.instances.items():
            info = {
                "id": instance_id,
                "port": instance.debugging_port,
                "running": instance.is_running,
                "created_at": instance.created_at,
                "last_activity": instance.last_activity,
                "profile_path": str(instance.profile_path) if instance.profile_path else None
            }
            instances_info.append(info)
            
        return instances_info
        
    async def cleanup_idle_instances(self, max_idle_time: float = 3600.0) -> int:
        """Clean up idle instances.
        
        Args:
            max_idle_time: Maximum idle time in seconds
            
        Returns:
            Number of instances cleaned up
        """
        current_time = asyncio.get_event_loop().time()
        idle_instances = []
        
        for instance_id, instance in self.instances.items():
            if current_time - instance.last_activity > max_idle_time:
                idle_instances.append(instance_id)
                
        cleanup_count = 0
        for instance_id in idle_instances:
            if await self.close_instance(instance_id):
                cleanup_count += 1
                
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} idle instances")
            
        return cleanup_count
        
    def create_profile(self, name: str, temporary: bool = True) -> BrowserProfile:
        """Create browser profile.
        
        Args:
            name: Profile name
            temporary: Whether profile should be temporary
            
        Returns:
            Browser profile instance
        """
        if name in self.profiles:
            return self.profiles[name]
            
        if temporary:
            profile = BrowserProfile.create_temporary(name)
        else:
            profile = BrowserProfile.create_persistent(name)
            
        self.profiles[name] = profile
        return profile
        
    async def _get_available_port(self) -> int:
        """Get next available debugging port."""
        while True:
            port = self._port_counter
            self._port_counter += 1
            
            # Check if port is in use
            in_use = any(
                instance.debugging_port == port 
                for instance in self.instances.values()
            )
            
            if not in_use:
                return port
                
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_all_instances()
        
        # Clean up temporary profiles
        for profile in self.profiles.values():
            profile.cleanup()


# Convenience functions
@asynccontextmanager
async def managed_browser(
    headless: bool = True,
    window_size: Optional[Tuple[int, int]] = None,
    profile: Optional[str] = None,
    **kwargs
):
    """Context manager for single managed browser instance.
    
    Args:
        headless: Whether to run in headless mode
        window_size: Browser window size
        profile: Profile name
        **kwargs: Additional arguments for create_instance
        
    Yields:
        Browser instance
    """
    async with BrowserManager(max_instances=1) as manager:
        instance = await manager.create_instance(
            headless=headless,
            window_size=window_size,
            profile=profile,
            **kwargs
        )
        try:
            yield instance
        finally:
            await manager.close_instance(instance.instance_id)


async def kill_all_chrome_processes() -> int:
    """Kill all Chrome processes on the system.
    
    Returns:
        Number of processes killed
    """
    killed_count = 0
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_info = proc.info
                if proc_info['name'] and 'chrome' in proc_info['name'].lower():
                    # Check if it's a debugging Chrome instance
                    cmdline = proc_info.get('cmdline', [])
                    if any('--remote-debugging-port' in arg for arg in cmdline):
                        proc.kill()
                        killed_count += 1
                        logger.debug(f"Killed Chrome process {proc_info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
    except Exception as e:
        logger.error(f"Error killing Chrome processes: {e}")
        
    if killed_count > 0:
        logger.info(f"Killed {killed_count} Chrome debugging processes")
        
    return killed_count