"""
WebSocket server for real-time LLM communication.

This module provides a WebSocket server that enables real-time bidirectional
communication between LLMs and the Surfboard browser automation system.
"""

import asyncio
import json
import logging
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import websockets
from websockets import ConnectionClosed, WebSocketServerProtocol

from ..actions.core_actions import CoreActions
from ..automation.browser_manager import BrowserManager
from ..protocols.llm_protocol import (
    BaseCommand,
    BaseResponse,
    CommandType,
    LLMMessage,
    StatusType,
    create_command_from_dict,
    create_error_response,
    serialize_response,
)
from .command_executor import CommandExecutor

logger = logging.getLogger(__name__)


@dataclass
class ClientSession:
    """WebSocket client session information."""

    websocket: WebSocketServerProtocol
    session_id: str
    connected_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    browser_instances: Set[str] = field(default_factory=set)
    context: Dict[str, Any] = field(default_factory=dict)
    message_count: int = 0

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def add_browser(self, browser_id: str):
        """Add browser instance to session."""
        self.browser_instances.add(browser_id)

    def remove_browser(self, browser_id: str):
        """Remove browser instance from session."""
        self.browser_instances.discard(browser_id)


class WebSocketServer:
    """WebSocket server for LLM communication."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        max_clients: int = 10,
        max_browsers_per_client: int = 3,
        session_timeout: float = 3600.0,  # 1 hour
        heartbeat_interval: float = 30.0,  # 30 seconds
    ):
        """Initialize WebSocket server.

        Args:
            host: Server host address
            port: Server port number
            max_clients: Maximum concurrent clients
            max_browsers_per_client: Maximum browsers per client
            session_timeout: Session timeout in seconds
            heartbeat_interval: Heartbeat interval in seconds
        """
        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.max_browsers_per_client = max_browsers_per_client
        self.session_timeout = session_timeout
        self.heartbeat_interval = heartbeat_interval

        # Server state
        self.running = False
        self.clients: Dict[str, ClientSession] = {}
        self.browser_manager = BrowserManager(
            max_instances=max_clients * max_browsers_per_client
        )
        self.command_executor = CommandExecutor(self.browser_manager)

        # Statistics
        self.stats = {
            "total_connections": 0,
            "total_messages": 0,
            "total_commands": 0,
            "start_time": None,
            "last_cleanup": time.time(),
        }

    async def start(self):
        """Start the WebSocket server."""
        if self.running:
            logger.warning("Server is already running")
            return

        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")

        self.running = True
        self.stats["start_time"] = time.time()

        # Start background tasks
        cleanup_task = asyncio.create_task(self._cleanup_task())
        heartbeat_task = asyncio.create_task(self._heartbeat_task())

        try:
            async with websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10,
                max_size=1024 * 1024,  # 1MB max message size
                compression=None,
            ):
                logger.info("WebSocket server started successfully")

                # Keep server running
                while self.running:
                    await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            cleanup_task.cancel()
            heartbeat_task.cancel()
            await self._shutdown()

    async def stop(self):
        """Stop the WebSocket server."""
        logger.info("Stopping WebSocket server...")
        self.running = False

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new client connection."""
        if len(self.clients) >= self.max_clients:
            logger.warning("Maximum clients reached, rejecting connection")
            await websocket.close(code=1013, reason="Server at capacity")
            return

        # Create session
        session_id = f"session_{int(time.time() * 1000)}"
        session = ClientSession(websocket=websocket, session_id=session_id)
        self.clients[session_id] = session
        self.stats["total_connections"] += 1

        client_address = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client connected: {session_id} from {client_address}")

        try:
            # Send welcome message
            welcome = {
                "type": "welcome",
                "session_id": session_id,
                "server_info": {
                    "version": "1.0",
                    "max_browsers": self.max_browsers_per_client,
                    "supported_commands": [cmd.value for cmd in CommandType],
                },
            }
            await websocket.send(json.dumps(welcome))

            # Handle messages
            async for message in websocket:
                try:
                    await self._process_message(session, message)
                except Exception as e:
                    logger.error(f"Message processing error for {session_id}: {e}")
                    error_response = {
                        "type": "error",
                        "message": str(e),
                        "timestamp": time.time(),
                    }
                    await websocket.send(json.dumps(error_response))

        except ConnectionClosed:
            logger.info(f"Client disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Client handler error for {session_id}: {e}")
        finally:
            await self._cleanup_session(session_id)

    async def _process_message(self, session: ClientSession, message: str):
        """Process incoming message from client."""
        session.update_activity()
        session.message_count += 1
        self.stats["total_messages"] += 1

        try:
            # Parse message
            data = json.loads(message)

            # Handle different message types
            if "command" in data:
                await self._handle_command_message(session, data)
            elif data.get("type") == "ping":
                await self._handle_ping(session)
            elif data.get("type") == "subscribe":
                await self._handle_subscription(session, data)
            else:
                logger.warning(
                    f"Unknown message type from {session.session_id}: {data}"
                )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {session.session_id}: {e}")
            await session.websocket.send(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": time.time(),
                    }
                )
            )

    async def _handle_command_message(
        self, session: ClientSession, data: Dict[str, Any]
    ):
        """Handle command message from LLM."""
        try:
            # Create LLM message object
            llm_message = LLMMessage(**data)

            if not llm_message.command:
                raise ValueError("No command found in message")

            command = llm_message.command
            self.stats["total_commands"] += 1

            logger.info(
                f"Executing command {command.command_type} for {session.session_id}"
            )

            # Execute command
            start_time = time.time()
            response = await self.command_executor.execute_command(
                command, session.session_id
            )
            execution_time = time.time() - start_time

            # Update response timing
            response.execution_time = execution_time

            # Send response
            response_message = LLMMessage(
                message_id=llm_message.message_id,
                response=response,
                session_id=session.session_id,
            )

            await session.websocket.send(response_message.json())

            logger.debug(
                f"Command {command.command_type} completed in {execution_time:.2f}s"
            )

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            traceback.print_exc()

            # Send error response
            error_response = create_error_response(
                command_id=data.get("command", {}).get("command_id", "unknown"),
                error_message=str(e),
                execution_time=time.time() - start_time
                if "start_time" in locals()
                else 0.0,
            )

            error_message = LLMMessage(
                message_id=data.get("message_id", "unknown"),
                response=error_response,
                session_id=session.session_id,
            )

            await session.websocket.send(error_message.json())

    async def _handle_ping(self, session: ClientSession):
        """Handle ping message."""
        pong = {
            "type": "pong",
            "timestamp": time.time(),
            "session_id": session.session_id,
        }
        await session.websocket.send(json.dumps(pong))

    async def _handle_subscription(self, session: ClientSession, data: Dict[str, Any]):
        """Handle subscription requests."""
        # Future: Handle event subscriptions (page events, console logs, etc.)
        logger.info(f"Subscription request from {session.session_id}: {data}")

    async def _cleanup_session(self, session_id: str):
        """Clean up client session."""
        if session_id not in self.clients:
            return

        session = self.clients[session_id]

        # Close associated browser instances
        for browser_id in list(session.browser_instances):
            try:
                await self.browser_manager.close_instance(browser_id)
                logger.info(f"Closed browser {browser_id} for session {session_id}")
            except Exception as e:
                logger.warning(f"Error closing browser {browser_id}: {e}")

        # Remove session
        del self.clients[session_id]
        logger.info(f"Session cleaned up: {session_id}")

    async def _cleanup_task(self):
        """Background task for cleaning up idle sessions."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute

                current_time = time.time()
                idle_sessions = []

                for session_id, session in self.clients.items():
                    if current_time - session.last_activity > self.session_timeout:
                        idle_sessions.append(session_id)

                # Clean up idle sessions
                for session_id in idle_sessions:
                    logger.info(f"Cleaning up idle session: {session_id}")
                    session = self.clients[session_id]
                    try:
                        await session.websocket.close(
                            code=1001, reason="Session timeout"
                        )
                    except:
                        pass
                    await self._cleanup_session(session_id)

                if idle_sessions:
                    logger.info(f"Cleaned up {len(idle_sessions)} idle sessions")

                self.stats["last_cleanup"] = current_time

            except Exception as e:
                logger.error(f"Cleanup task error: {e}")

    async def _heartbeat_task(self):
        """Background task for sending heartbeat to clients."""
        while self.running:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # Send heartbeat to all clients
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": time.time(),
                    "server_stats": {
                        "active_clients": len(self.clients),
                        "total_messages": self.stats["total_messages"],
                        "uptime": time.time() - self.stats["start_time"]
                        if self.stats["start_time"]
                        else 0,
                    },
                }

                disconnected_sessions = []
                for session_id, session in self.clients.items():
                    try:
                        await session.websocket.send(json.dumps(heartbeat))
                    except ConnectionClosed:
                        disconnected_sessions.append(session_id)
                    except Exception as e:
                        logger.warning(f"Heartbeat failed for {session_id}: {e}")
                        disconnected_sessions.append(session_id)

                # Clean up disconnected sessions
                for session_id in disconnected_sessions:
                    await self._cleanup_session(session_id)

            except Exception as e:
                logger.error(f"Heartbeat task error: {e}")

    async def _shutdown(self):
        """Shutdown server and clean up resources."""
        logger.info("Shutting down WebSocket server...")

        # Close all client sessions
        for session_id in list(self.clients.keys()):
            await self._cleanup_session(session_id)

        # Close browser manager
        await self.browser_manager.close_all_instances()

        logger.info("WebSocket server shutdown complete")

    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        uptime = (
            time.time() - self.stats["start_time"] if self.stats["start_time"] else 0
        )

        return {
            "server_info": {
                "host": self.host,
                "port": self.port,
                "running": self.running,
                "uptime": uptime,
            },
            "client_stats": {
                "active_clients": len(self.clients),
                "max_clients": self.max_clients,
                "total_connections": self.stats["total_connections"],
            },
            "message_stats": {
                "total_messages": self.stats["total_messages"],
                "total_commands": self.stats["total_commands"],
                "messages_per_second": self.stats["total_messages"] / max(uptime, 1),
            },
            "browser_stats": {
                "active_browsers": len(self.browser_manager.instances),
                "max_browsers": self.browser_manager.max_instances,
            },
            "last_cleanup": self.stats["last_cleanup"],
        }

    async def broadcast_message(
        self, message: Dict[str, Any], exclude_session: Optional[str] = None
    ):
        """Broadcast message to all connected clients."""
        message_str = json.dumps(message)

        disconnected = []
        for session_id, session in self.clients.items():
            if session_id == exclude_session:
                continue

            try:
                await session.websocket.send(message_str)
            except ConnectionClosed:
                disconnected.append(session_id)
            except Exception as e:
                logger.warning(f"Broadcast failed for {session_id}: {e}")
                disconnected.append(session_id)

        # Clean up disconnected sessions
        for session_id in disconnected:
            await self._cleanup_session(session_id)


# Utility functions


async def start_server(
    host: str = "localhost", port: int = 8765, **kwargs
) -> WebSocketServer:
    """Start WebSocket server with configuration."""
    server = WebSocketServer(host=host, port=port, **kwargs)
    await server.start()
    return server


def create_test_client_message(command_type: CommandType, **kwargs) -> str:
    """Create test client message."""
    command_data = {"command_type": command_type.value, **kwargs}
    command = create_command_from_dict(command_data)

    message = LLMMessage(command=command)
    return message.json()


# Example usage for testing
if __name__ == "__main__":
    import asyncio

    async def main():
        server = WebSocketServer()
        try:
            await server.start()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        finally:
            await server.stop()

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
