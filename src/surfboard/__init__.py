"""
Surfboard - Windows Chrome Automation Bridge for LLM Integration.

A native Windows automation bridge that enables LLMs to control Google Chrome
through intelligent protocol selection.
"""

__version__ = "0.1.0"
__author__ = "Surfboard Development Team"

from .core import SurfboardClient

__all__ = ["SurfboardClient"]
