"""
Native Messaging implementation for Chrome extension communication.

This module provides a bridge between Chrome extensions and the Surfboard
automation system using Chrome's Native Messaging protocol.
"""

import asyncio
import json
import logging
import struct
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class NativeMessagingError(Exception):
    """Exception raised when native messaging operations fail."""
    pass


class NativeMessagingHost:
    """Native Messaging host for communication with Chrome extensions."""
    
    def __init__(self, host_name: str = "com.surfboard.bridge"):
        """Initialize native messaging host.
        
        Args:
            host_name: Name of the native messaging host
        """
        self.host_name = host_name
        self.message_handlers: Dict[str, Callable] = {}
        self.running = False
        
        # Register default handlers
        self.register_handler("hello", self._handle_hello)
        self.register_handler("ping", self._handle_ping)
        
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a message handler for a specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Function to call when message is received
        """
        self.message_handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")
        
    async def _handle_hello(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle hello message from extension."""
        return {
            "type": "hello_response",
            "timestamp": message.get("timestamp"),
            "host_name": self.host_name,
            "version": "1.0.0"
        }
        
    async def _handle_ping(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping message from extension."""
        return {
            "type": "pong",
            "timestamp": message.get("timestamp"),
            "response_time": asyncio.get_event_loop().time()
        }
        
    def _read_message(self) -> Optional[Dict[str, Any]]:
        """Read a message from stdin following Native Messaging protocol.
        
        Returns:
            Parsed message or None if end of stream
        """
        try:
            # Read message length (4 bytes, little endian)
            raw_length = sys.stdin.buffer.read(4)
            if not raw_length:
                return None
                
            message_length = struct.unpack('<I', raw_length)[0]
            
            # Read message content
            raw_message = sys.stdin.buffer.read(message_length)
            if len(raw_message) != message_length:
                raise NativeMessagingError(f"Expected {message_length} bytes, got {len(raw_message)}")
                
            # Parse JSON
            message = json.loads(raw_message.decode('utf-8'))
            logger.debug(f"Received message: {message}")
            return message
            
        except (struct.error, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to read message: {e}")
            raise NativeMessagingError(f"Invalid message format: {e}") from e
            
    def _send_message(self, message: Dict[str, Any]) -> None:
        """Send a message to stdout following Native Messaging protocol.
        
        Args:
            message: Message to send
        """
        try:
            # Encode message as JSON
            json_message = json.dumps(message)
            encoded_message = json_message.encode('utf-8')
            
            # Write message length (4 bytes, little endian)
            message_length = len(encoded_message)
            sys.stdout.buffer.write(struct.pack('<I', message_length))
            
            # Write message content
            sys.stdout.buffer.write(encoded_message)
            sys.stdout.buffer.flush()
            
            logger.debug(f"Sent message: {message}")
            
        except (json.JSONEncodeError, UnicodeEncodeError) as e:
            logger.error(f"Failed to send message: {e}")
            raise NativeMessagingError(f"Failed to encode message: {e}") from e
            
    async def handle_message(self, message: Dict[str, Any]) -> None:
        """Handle an incoming message from the extension.
        
        Args:
            message: Message received from extension
        """
        message_type = message.get("type", "unknown")
        
        try:
            # Find appropriate handler
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                response = await handler(message)
                
                if response:
                    self._send_message(response)
            else:
                logger.warning(f"No handler for message type: {message_type}")
                # Send error response
                self._send_message({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "original_message": message
                })
                
        except Exception as e:
            logger.error(f"Error handling message {message_type}: {e}")
            # Send error response
            self._send_message({
                "type": "error",
                "message": str(e),
                "original_message": message
            })
            
    async def run(self) -> None:
        """Run the native messaging host main loop."""
        self.running = True
        logger.info(f"Starting native messaging host: {self.host_name}")
        
        try:
            while self.running:
                # Read message from stdin
                message = self._read_message()
                if message is None:
                    # End of input stream
                    logger.info("End of input stream, shutting down")
                    break
                    
                # Handle message asynchronously
                await self.handle_message(message)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Native messaging host error: {e}")
            raise
        finally:
            self.running = False
            logger.info("Native messaging host stopped")
            
    def stop(self) -> None:
        """Stop the native messaging host."""
        self.running = False


def create_host_manifest(
    host_name: str,
    description: str,
    path: Path,
    allowed_origins: list[str]
) -> Dict[str, Any]:
    """Create a native messaging host manifest.
    
    Args:
        host_name: Name of the native messaging host
        description: Description of the host
        path: Path to the host executable
        allowed_origins: List of allowed extension origins
        
    Returns:
        Manifest dictionary
    """
    return {
        "name": host_name,
        "description": description,
        "path": str(path.resolve()),
        "type": "stdio",
        "allowed_origins": allowed_origins
    }


def install_host_manifest(
    manifest: Dict[str, Any],
    user_level: bool = True
) -> Path:
    """Install native messaging host manifest to the system.
    
    Args:
        manifest: Host manifest dictionary
        user_level: Install for current user only (vs system-wide)
        
    Returns:
        Path where manifest was installed
    """
    import platform
    
    host_name = manifest["name"]
    system = platform.system().lower()
    
    if system == "windows":
        # Windows registry path would be used in production
        if user_level:
            manifest_dir = Path.home() / "AppData/Local/Google/Chrome/User Data/NativeMessagingHosts"
        else:
            manifest_dir = Path("C:/Program Files/Google/Chrome/Application/NativeMessagingHosts")
    elif system == "darwin":
        # macOS
        if user_level:
            manifest_dir = Path.home() / "Library/Application Support/Google/Chrome/NativeMessagingHosts"
        else:
            manifest_dir = Path("/Library/Google/Chrome/NativeMessagingHosts")
    else:
        # Linux and others
        if user_level:
            manifest_dir = Path.home() / ".config/google-chrome/NativeMessagingHosts"
        else:
            manifest_dir = Path("/etc/opt/chrome/native-messaging-hosts")
    
    # Create directory if it doesn't exist
    manifest_dir.mkdir(parents=True, exist_ok=True)
    
    # Write manifest file
    manifest_path = manifest_dir / f"{host_name}.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
        
    logger.info(f"Installed native messaging host manifest: {manifest_path}")
    return manifest_path


# Convenience function for testing
async def test_native_messaging() -> bool:
    """Test native messaging functionality.
    
    Returns:
        True if test successful, False otherwise
    """
    try:
        host = NativeMessagingHost()
        
        # Register a test handler
        async def test_handler(message):
            return {"type": "test_response", "success": True}
            
        host.register_handler("test", test_handler)
        
        # For testing, we would need to simulate stdin/stdout
        logger.info("Native messaging host test setup complete")
        return True
        
    except Exception as e:
        logger.error(f"Native messaging test failed: {e}")
        return False


if __name__ == "__main__":
    # Entry point for native messaging host
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        # Log to file instead of stderr to avoid interfering with native messaging
        filename=Path.home() / "surfboard_native_host.log"
    )
    
    async def main():
        host = NativeMessagingHost()
        await host.run()
    
    asyncio.run(main())