"""
Surfboard Automation Module.

This module provides browser automation capabilities with CDP integration,
smart element selection, and LLM-optimized interactions.
"""

from .browser_manager import BrowserManager, BrowserInstance, managed_browser
from .element_selector import AdvancedElementSelector, SelectionResult, SelectionStrategy
from .smart_waiter import SmartWaiter, WaitResult, WaitType
from .error_recovery import ErrorRecoverySystem, RecoveryResult, ErrorType, RecoveryStrategy
from .performance_optimizer import PerformanceOptimizer, OptimizationSettings, OptimizationLevel, ResourceMetrics
from .advanced_interactions import AdvancedInteractionEngine, InteractionResult, InteractionType, InteractionSequence

__all__ = [
    "BrowserManager",
    "BrowserInstance", 
    "managed_browser",
    "AdvancedElementSelector",
    "SelectionResult",
    "SelectionStrategy",
    "SmartWaiter",
    "WaitResult",
    "WaitType",
    "ErrorRecoverySystem",
    "RecoveryResult",
    "ErrorType",
    "RecoveryStrategy",
    "PerformanceOptimizer",
    "OptimizationSettings",
    "OptimizationLevel",
    "ResourceMetrics",
    "AdvancedInteractionEngine",
    "InteractionResult",
    "InteractionType",
    "InteractionSequence"
]
