"""
Surfboard Automation Module.

This module provides browser automation capabilities with CDP integration,
smart element selection, and LLM-optimized interactions.
"""

from .advanced_interactions import (
    AdvancedInteractionEngine,
    InteractionResult,
    InteractionSequence,
    InteractionType,
)
from .browser_manager import BrowserInstance, BrowserManager, managed_browser
from .element_selector import (
    AdvancedElementSelector,
    SelectionResult,
    SelectionStrategy,
)
from .error_recovery import (
    ErrorRecoverySystem,
    ErrorType,
    RecoveryResult,
    RecoveryStrategy,
)
from .performance_optimizer import (
    OptimizationLevel,
    OptimizationSettings,
    PerformanceOptimizer,
    ResourceMetrics,
)
from .smart_waiter import SmartWaiter, WaitResult, WaitType

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
    "InteractionSequence",
]
