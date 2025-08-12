"""
Performance Optimization and Resource Management.

This module provides performance optimization, resource monitoring,
and memory management for efficient browser automation.
"""

import asyncio
import logging
import psutil
import time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from ..protocols.cdp_domains import CDPSession

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Types of resources to monitor."""
    
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    DISK = "disk"
    BROWSER_TABS = "browser_tabs"
    DOM_COMPLEXITY = "dom_complexity"


class OptimizationLevel(str, Enum):
    """Performance optimization levels."""
    
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"


@dataclass
class ResourceMetrics:
    """Resource usage metrics."""
    
    timestamp: float
    memory_usage_mb: float
    cpu_percent: float
    network_active_connections: int
    dom_element_count: int
    active_browser_instances: int
    page_load_time: float = 0.0
    script_execution_time: float = 0.0
    render_time: float = 0.0


@dataclass
class OptimizationSettings:
    """Performance optimization settings."""
    
    level: OptimizationLevel
    max_memory_mb: int = 2048
    max_cpu_percent: float = 80.0
    max_concurrent_operations: int = 5
    enable_resource_cleanup: bool = True
    enable_dom_optimization: bool = True
    enable_network_throttling: bool = False
    enable_script_optimization: bool = True
    cache_strategies: List[str] = field(default_factory=list)


class PerformanceOptimizer:
    """Performance optimizer with resource management."""
    
    def __init__(self, settings: OptimizationSettings):
        """Initialize performance optimizer."""
        self.settings = settings
        self.metrics_history = []
        self.resource_limits = {}
        self.optimization_cache = {}
        self.active_sessions = set()
        self.cleanup_tasks = []
        
        # Performance thresholds
        self.memory_warning_threshold = settings.max_memory_mb * 0.8
        self.cpu_warning_threshold = settings.max_cpu_percent * 0.8
        
        # Optimization strategies
        self.optimization_strategies = {
            OptimizationLevel.CONSERVATIVE: {
                "dom_cleanup_interval": 60,
                "cache_cleanup_interval": 300,
                "resource_monitoring_interval": 30,
                "enable_lazy_loading": True,
                "max_parallel_operations": 3
            },
            OptimizationLevel.MODERATE: {
                "dom_cleanup_interval": 30,
                "cache_cleanup_interval": 180,
                "resource_monitoring_interval": 15,
                "enable_lazy_loading": True,
                "max_parallel_operations": 5
            },
            OptimizationLevel.AGGRESSIVE: {
                "dom_cleanup_interval": 15,
                "cache_cleanup_interval": 60,
                "resource_monitoring_interval": 10,
                "enable_lazy_loading": False,
                "max_parallel_operations": 8
            },
            OptimizationLevel.MAXIMUM: {
                "dom_cleanup_interval": 10,
                "cache_cleanup_interval": 30,
                "resource_monitoring_interval": 5,
                "enable_lazy_loading": False,
                "max_parallel_operations": 10
            }
        }
        
    async def initialize(self) -> None:
        """Initialize performance optimization system."""
        logger.info(f"Initializing performance optimizer (level: {self.settings.level})")
        
        # Start resource monitoring
        asyncio.create_task(self._resource_monitor_loop())
        
        # Start periodic cleanup
        if self.settings.enable_resource_cleanup:
            asyncio.create_task(self._cleanup_loop())
            
        # Apply initial optimizations
        await self._apply_system_optimizations()
        
    async def register_session(self, session: CDPSession, session_id: str) -> None:
        """Register a CDP session for optimization."""
        logger.debug(f"Registering session for optimization: {session_id}")
        
        self.active_sessions.add((session, session_id))
        
        # Apply session-specific optimizations
        await self._optimize_session(session, session_id)
        
    async def unregister_session(self, session_id: str) -> None:
        """Unregister a CDP session."""
        logger.debug(f"Unregistering session: {session_id}")
        
        self.active_sessions = {
            (session, sid) for session, sid in self.active_sessions
            if sid != session_id
        }
        
        # Clean up session resources
        await self._cleanup_session_resources(session_id)
        
    async def optimize_page_load(
        self,
        session: CDPSession,
        url: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Optimize page loading performance."""
        start_time = time.time()
        
        logger.debug(f"Optimizing page load: {url}")
        
        # Pre-load optimizations
        await self._apply_preload_optimizations(session)
        
        # Monitor load performance
        load_metrics = await self._monitor_page_load(session, url)
        
        # Post-load optimizations
        await self._apply_postload_optimizations(session)
        
        total_time = time.time() - start_time
        
        optimization_result = {
            "url": url,
            "session_id": session_id,
            "total_optimization_time": total_time,
            "load_metrics": load_metrics,
            "optimizations_applied": await self._get_applied_optimizations(session)
        }
        
        # Cache optimization results
        self.optimization_cache[url] = optimization_result
        
        return optimization_result
        
    async def optimize_script_execution(
        self,
        session: CDPSession,
        script: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Optimize JavaScript execution performance."""
        
        if not self.settings.enable_script_optimization:
            # Execute without optimization
            start_time = time.time()
            result = await session.runtime.evaluate(script)
            execution_time = time.time() - start_time
            
            return {
                "result": result,
                "execution_time": execution_time,
                "optimized": False
            }
            
        # Apply script optimizations
        optimized_script = await self._optimize_script(script)
        
        # Execute with performance monitoring
        start_time = time.time()
        
        # Enable runtime profiling if aggressive optimization
        if self.settings.level in [OptimizationLevel.AGGRESSIVE, OptimizationLevel.MAXIMUM]:
            await session.profiler.enable()
            
        result = await session.runtime.evaluate(optimized_script)
        execution_time = time.time() - start_time
        
        # Disable profiling
        if self.settings.level in [OptimizationLevel.AGGRESSIVE, OptimizationLevel.MAXIMUM]:
            await session.profiler.disable()
            
        return {
            "result": result,
            "execution_time": execution_time,
            "optimized": True,
            "original_script_length": len(script),
            "optimized_script_length": len(optimized_script)
        }
        
    async def get_performance_metrics(self) -> ResourceMetrics:
        """Get current performance metrics."""
        
        # System metrics
        memory_info = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        network_connections = len(psutil.net_connections())
        
        # Browser-specific metrics
        dom_elements = 0
        if self.active_sessions:
            session, _ = next(iter(self.active_sessions))
            dom_elements = await self._get_dom_element_count(session)
            
        metrics = ResourceMetrics(
            timestamp=time.time(),
            memory_usage_mb=memory_info.used / 1024 / 1024,
            cpu_percent=cpu_percent,
            network_active_connections=network_connections,
            dom_element_count=dom_elements,
            active_browser_instances=len(self.active_sessions)
        )
        
        # Store in history
        self.metrics_history.append(metrics)
        
        # Keep only recent history
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-500:]
            
        return metrics
        
    async def cleanup_resources(self, force: bool = False) -> Dict[str, Any]:
        """Clean up system resources."""
        logger.info("Performing resource cleanup")
        
        cleanup_results = {
            "memory_freed_mb": 0,
            "cache_entries_cleared": 0,
            "sessions_cleaned": 0,
            "dom_nodes_removed": 0
        }
        
        # Memory cleanup
        if force or await self._should_cleanup_memory():
            memory_before = psutil.virtual_memory().used / 1024 / 1024
            
            # Clear optimization cache
            cache_size = len(self.optimization_cache)
            self.optimization_cache.clear()
            cleanup_results["cache_entries_cleared"] = cache_size
            
            # Clean up metrics history
            self.metrics_history = self.metrics_history[-100:]
            
            # Force garbage collection
            import gc
            gc.collect()
            
            memory_after = psutil.virtual_memory().used / 1024 / 1024
            cleanup_results["memory_freed_mb"] = max(0, memory_before - memory_after)
            
        # DOM cleanup for active sessions
        for session, session_id in self.active_sessions.copy():
            try:
                nodes_removed = await self._cleanup_dom_nodes(session)
                cleanup_results["dom_nodes_removed"] += nodes_removed
                cleanup_results["sessions_cleaned"] += 1
            except Exception as e:
                logger.warning(f"DOM cleanup failed for session {session_id}: {e}")
                
        logger.info(f"Resource cleanup completed: {cleanup_results}")
        return cleanup_results
        
    async def _resource_monitor_loop(self) -> None:
        """Background resource monitoring loop."""
        
        strategy = self.optimization_strategies[self.settings.level]
        interval = strategy["resource_monitoring_interval"]
        
        while True:
            try:
                metrics = await self.get_performance_metrics()
                
                # Check for resource warnings
                if metrics.memory_usage_mb > self.memory_warning_threshold:
                    logger.warning(f"High memory usage: {metrics.memory_usage_mb:.1f}MB")
                    await self.cleanup_resources()
                    
                if metrics.cpu_percent > self.cpu_warning_threshold:
                    logger.warning(f"High CPU usage: {metrics.cpu_percent:.1f}%")
                    await self._throttle_operations()
                    
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(interval * 2)  # Back off on error
                
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        
        strategy = self.optimization_strategies[self.settings.level]
        interval = strategy["cache_cleanup_interval"]
        
        while True:
            try:
                await asyncio.sleep(interval)
                await self.cleanup_resources()
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                
    async def _apply_system_optimizations(self) -> None:
        """Apply system-level optimizations."""
        logger.debug("Applying system optimizations")
        
        # Set process priority based on optimization level
        current_process = psutil.Process()
        
        if self.settings.level == OptimizationLevel.MAXIMUM:
            try:
                current_process.nice(-5)  # Higher priority
            except Exception:
                pass  # May not have permission
        elif self.settings.level == OptimizationLevel.CONSERVATIVE:
            try:
                current_process.nice(5)  # Lower priority
            except Exception:
                pass
                
    async def _optimize_session(self, session: CDPSession, session_id: str) -> None:
        """Apply session-specific optimizations."""
        
        # Disable unnecessary features for better performance
        if self.settings.level in [OptimizationLevel.AGGRESSIVE, OptimizationLevel.MAXIMUM]:
            # Disable images for faster loading
            await session.page.set_resource_response_interception(patterns=[
                {"urlPattern": "*.jpg", "resourceType": "Image"},
                {"urlPattern": "*.png", "resourceType": "Image"},
                {"urlPattern": "*.gif", "resourceType": "Image"}
            ])
            
        # Enable performance monitoring
        await session.performance.enable()
        
        # Set cache strategies
        if "no-cache" in self.settings.cache_strategies:
            await session.network.set_cache_disabled(cache_disabled=True)
            
    async def _apply_preload_optimizations(self, session: CDPSession) -> None:
        """Apply optimizations before page load."""
        
        # Clear previous page resources
        if self.settings.enable_dom_optimization:
            script = """
            // Clear previous page data
            if (window.performance && window.performance.mark) {
                window.performance.mark('surfboard-preload-start');
            }
            """
            await session.runtime.evaluate(script)
            
    async def _monitor_page_load(
        self,
        session: CDPSession,
        url: str
    ) -> Dict[str, Any]:
        """Monitor page load performance."""
        
        start_time = time.time()
        
        # Start navigation
        await session.page.navigate(url)
        
        # Wait for load with timeout
        await asyncio.sleep(0.1)  # Small delay to start measuring
        
        # Get performance metrics
        metrics_script = """
        (function() {
            if (!window.performance) return {};
            
            const navigation = performance.getEntriesByType('navigation')[0];
            const resources = performance.getEntriesByType('resource');
            
            return {
                loadTime: navigation ? navigation.loadEventEnd - navigation.navigationStart : 0,
                domContentLoaded: navigation ? navigation.domContentLoadedEventEnd - navigation.navigationStart : 0,
                resourceCount: resources.length,
                totalResourceSize: resources.reduce((sum, r) => sum + (r.transferSize || 0), 0),
                largestResource: Math.max(...resources.map(r => r.transferSize || 0))
            };
        })()
        """
        
        load_metrics = await session.runtime.evaluate(metrics_script) or {}
        load_metrics["total_time"] = time.time() - start_time
        
        return load_metrics
        
    async def _apply_postload_optimizations(self, session: CDPSession) -> None:
        """Apply optimizations after page load."""
        
        if not self.settings.enable_dom_optimization:
            return
            
        # Remove unused DOM nodes and optimize structure
        optimization_script = """
        (function() {
            let optimizations = {
                removedNodes: 0,
                optimizedStyles: 0,
                cleanedEvents: 0
            };
            
            // Remove hidden elements if aggressive optimization
            if (true) {  // Would check optimization level
                const hiddenElements = document.querySelectorAll('[style*="display: none"], [hidden]');
                hiddenElements.forEach(el => {
                    if (el.tagName !== 'SCRIPT' && el.tagName !== 'STYLE') {
                        el.remove();
                        optimizations.removedNodes++;
                    }
                });
            }
            
            // Clean up inline styles
            const elementsWithInlineStyles = document.querySelectorAll('[style]');
            elementsWithInlineStyles.forEach(el => {
                if (el.style.display === 'none' && el.tagName !== 'SCRIPT') {
                    el.remove();
                    optimizations.removedNodes++;
                }
            });
            
            // Mark optimization complete
            if (window.performance && window.performance.mark) {
                window.performance.mark('surfboard-optimization-complete');
            }
            
            return optimizations;
        })()
        """
        
        try:
            result = await session.runtime.evaluate(optimization_script)
            logger.debug(f"Post-load optimizations: {result}")
        except Exception as e:
            logger.debug(f"Post-load optimization error: {e}")
            
    async def _optimize_script(self, script: str) -> str:
        """Optimize JavaScript code for better performance."""
        
        # Basic script optimizations
        optimized = script.strip()
        
        # Remove comments for smaller payload
        if self.settings.level in [OptimizationLevel.AGGRESSIVE, OptimizationLevel.MAXIMUM]:
            import re
            optimized = re.sub(r'//.*?\n', '\n', optimized)
            optimized = re.sub(r'/\*.*?\*/', '', optimized, flags=re.DOTALL)
            
        # Minify whitespace
        if self.settings.level == OptimizationLevel.MAXIMUM:
            optimized = ' '.join(optimized.split())
            
        return optimized
        
    async def _get_applied_optimizations(self, session: CDPSession) -> List[str]:
        """Get list of optimizations applied to session."""
        
        optimizations = []
        
        if self.settings.enable_dom_optimization:
            optimizations.append("dom_cleanup")
            
        if self.settings.enable_script_optimization:
            optimizations.append("script_optimization")
            
        if "no-cache" in self.settings.cache_strategies:
            optimizations.append("cache_disabled")
            
        return optimizations
        
    async def _get_dom_element_count(self, session: CDPSession) -> int:
        """Get DOM element count for session."""
        
        script = "document.querySelectorAll('*').length"
        
        try:
            return await session.runtime.evaluate(script) or 0
        except Exception:
            return 0
            
    async def _should_cleanup_memory(self) -> bool:
        """Check if memory cleanup is needed."""
        
        memory_info = psutil.virtual_memory()
        memory_usage_mb = memory_info.used / 1024 / 1024
        
        return memory_usage_mb > self.memory_warning_threshold
        
    async def _cleanup_dom_nodes(self, session: CDPSession) -> int:
        """Clean up unnecessary DOM nodes."""
        
        cleanup_script = """
        (function() {
            let removed = 0;
            
            // Remove empty text nodes
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                {
                    acceptNode: function(node) {
                        return node.nodeValue.trim() === '' ? 
                               NodeFilter.FILTER_ACCEPT : 
                               NodeFilter.FILTER_REJECT;
                    }
                }
            );
            
            const emptyNodes = [];
            let node;
            while (node = walker.nextNode()) {
                emptyNodes.push(node);
            }
            
            emptyNodes.forEach(node => {
                if (node.parentNode) {
                    node.parentNode.removeChild(node);
                    removed++;
                }
            });
            
            // Remove invisible elements (if safe to do so)
            const invisibleElements = document.querySelectorAll('[style*="display: none"]:not(script):not(style)');
            invisibleElements.forEach(el => {
                if (!el.querySelector('script, style') && el.children.length === 0) {
                    el.remove();
                    removed++;
                }
            });
            
            return removed;
        })()
        """
        
        try:
            return await session.runtime.evaluate(cleanup_script) or 0
        except Exception:
            return 0
            
    async def _cleanup_session_resources(self, session_id: str) -> None:
        """Clean up resources for specific session."""
        
        # Remove session-specific cache entries
        keys_to_remove = [
            key for key in self.optimization_cache.keys()
            if isinstance(key, str) and session_id in key
        ]
        
        for key in keys_to_remove:
            del self.optimization_cache[key]
            
    async def _throttle_operations(self) -> None:
        """Throttle operations due to high CPU usage."""
        
        logger.info("Throttling operations due to high CPU usage")
        
        # Reduce max concurrent operations temporarily
        current_max = self.optimization_strategies[self.settings.level]["max_parallel_operations"]
        throttled_max = max(1, current_max // 2)
        
        # This would integrate with operation queue management
        # For now, just add a delay
        await asyncio.sleep(1.0)
        
    def get_optimization_recommendations(self) -> Dict[str, str]:
        """Get optimization recommendations based on current metrics."""
        
        if not self.metrics_history:
            return {"status": "No metrics available"}
            
        recent_metrics = self.metrics_history[-10:]  # Last 10 measurements
        avg_memory = sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics)
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        
        recommendations = {}
        
        if avg_memory > self.memory_warning_threshold:
            recommendations["memory"] = "Consider upgrading to aggressive optimization level or increasing memory limits"
            
        if avg_cpu > self.cpu_warning_threshold:
            recommendations["cpu"] = "Consider reducing concurrent operations or enabling CPU throttling"
            
        if len(self.active_sessions) > 10:
            recommendations["sessions"] = "Consider implementing session pooling to reduce resource overhead"
            
        if not recommendations:
            recommendations["status"] = "Performance is within acceptable parameters"
            
        return recommendations