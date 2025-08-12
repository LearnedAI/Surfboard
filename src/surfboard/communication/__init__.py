"""
LLM Communication Bridge.

This module provides the communication layer between LLMs and the Surfboard
browser automation system, including WebSocket servers, command execution,
and page analysis capabilities.
"""

from .command_executor import CommandExecutor
from .page_analyzer import ElementAnalysis, PageAnalyzer
from .websocket_server import ClientSession, WebSocketServer

__all__ = [
    "WebSocketServer",
    "ClientSession",
    "CommandExecutor",
    "PageAnalyzer",
    "ElementAnalysis",
]
