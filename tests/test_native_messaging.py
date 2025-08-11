"""
Tests for Native Messaging functionality.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from surfboard.protocols.native_messaging import (
    NativeMessagingError,
    NativeMessagingHost,
    create_host_manifest,
    test_native_messaging,
)


class TestNativeMessagingHost:
    """Test Native Messaging host functionality."""

    def test_initialization(self):
        """Test host initialization."""
        host = NativeMessagingHost("com.test.host")
        
        assert host.host_name == "com.test.host"
        assert host.running is False
        assert "hello" in host.message_handlers
        assert "ping" in host.message_handlers

    def test_register_handler(self):
        """Test handler registration."""
        host = NativeMessagingHost()
        
        def test_handler(message):
            return {"test": "response"}
            
        host.register_handler("test_type", test_handler)
        
        assert "test_type" in host.message_handlers
        assert host.message_handlers["test_type"] == test_handler

    @pytest.mark.asyncio
    async def test_handle_hello_message(self):
        """Test hello message handling."""
        host = NativeMessagingHost()
        
        message = {"type": "hello", "timestamp": 1234567890}
        response = await host._handle_hello(message)
        
        assert response["type"] == "hello_response"
        assert response["timestamp"] == 1234567890
        assert response["host_name"] == host.host_name
        assert "version" in response

    @pytest.mark.asyncio
    async def test_handle_ping_message(self):
        """Test ping message handling."""
        host = NativeMessagingHost()
        
        message = {"type": "ping", "timestamp": 1234567890}
        response = await host._handle_ping(message)
        
        assert response["type"] == "pong"
        assert response["timestamp"] == 1234567890
        assert "response_time" in response

    @pytest.mark.asyncio
    @patch('surfboard.protocols.native_messaging.sys.stdout')
    async def test_send_message(self, mock_stdout):
        """Test message sending."""
        host = NativeMessagingHost()
        
        # Mock the buffer attribute
        mock_buffer = MagicMock()
        mock_stdout.buffer = mock_buffer
        
        message = {"type": "test", "data": "hello"}
        host._send_message(message)
        
        # Verify write was called with correct data
        mock_buffer.write.assert_called()
        mock_buffer.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_with_handler(self):
        """Test message handling with registered handler."""
        host = NativeMessagingHost()
        
        # Mock _send_message to avoid stdout interaction
        with patch.object(host, '_send_message') as mock_send:
            # Register test handler
            async def test_handler(message):
                return {"type": "test_response", "success": True}
                
            host.register_handler("test", test_handler)
            
            # Handle test message
            message = {"type": "test", "data": "test_data"}
            await host.handle_message(message)
            
            # Verify response was sent
            mock_send.assert_called_once()
            response = mock_send.call_args[0][0]
            assert response["type"] == "test_response"
            assert response["success"] is True

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self):
        """Test handling unknown message type."""
        host = NativeMessagingHost()
        
        with patch.object(host, '_send_message') as mock_send:
            message = {"type": "unknown_type", "data": "test"}
            await host.handle_message(message)
            
            # Verify error response was sent
            mock_send.assert_called_once()
            response = mock_send.call_args[0][0]
            assert response["type"] == "error"
            assert "Unknown message type" in response["message"]

    @pytest.mark.asyncio
    async def test_handle_message_error(self):
        """Test error handling in message processing."""
        host = NativeMessagingHost()
        
        # Register handler that raises exception
        async def failing_handler(message):
            raise ValueError("Test error")
            
        host.register_handler("failing", failing_handler)
        
        with patch.object(host, '_send_message') as mock_send:
            message = {"type": "failing", "data": "test"}
            await host.handle_message(message)
            
            # Verify error response was sent
            mock_send.assert_called_once()
            response = mock_send.call_args[0][0]
            assert response["type"] == "error"
            assert "Test error" in response["message"]


class TestHostManifest:
    """Test host manifest functionality."""

    def test_create_host_manifest(self):
        """Test manifest creation."""
        manifest = create_host_manifest(
            host_name="com.test.host",
            description="Test host",
            path=Path("/usr/bin/test-host"),
            allowed_origins=["chrome-extension://abc123/"]
        )
        
        assert manifest["name"] == "com.test.host"
        assert manifest["description"] == "Test host"
        assert manifest["path"] == "/usr/bin/test-host"
        assert manifest["type"] == "stdio"
        assert manifest["allowed_origins"] == ["chrome-extension://abc123/"]

    @patch('platform.system')
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open', new_callable=mock_open)
    def test_install_host_manifest_linux(self, mock_file, mock_mkdir, mock_system):
        """Test manifest installation on Linux."""
        from surfboard.protocols.native_messaging import install_host_manifest
        
        mock_system.return_value = "Linux"
        
        manifest = {
            "name": "com.test.host",
            "description": "Test",
            "path": "/test/path",
            "type": "stdio",
            "allowed_origins": []
        }
        
        result_path = install_host_manifest(manifest, user_level=True)
        
        # Verify path construction
        expected_dir = Path.home() / ".config/google-chrome/NativeMessagingHosts"
        expected_path = expected_dir / "com.test.host.json"
        
        assert result_path == expected_path
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called_once()


class TestNativeMessagingConvenience:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_native_messaging_test(self):
        """Test native messaging test function."""
        result = await test_native_messaging()
        
        # Should succeed with basic setup
        assert result is True


# Integration test (marked for manual testing)
@pytest.mark.manual
@pytest.mark.asyncio
async def test_real_native_messaging():
    """
    Integration test for real native messaging.
    
    This test would require a Chrome extension to be installed.
    Mark with @pytest.mark.manual to exclude from automatic runs.
    """
    # In a real test, we would:
    # 1. Install the test extension
    # 2. Start the native messaging host
    # 3. Test bidirectional communication
    # 4. Verify message handling
    
    host = NativeMessagingHost("com.surfboard.test")
    
    # Test basic functionality
    assert host.host_name == "com.surfboard.test"
    assert not host.running
    
    # Test message handlers
    test_message = {"type": "hello", "timestamp": 1234567890}
    response = await host._handle_hello(test_message)
    
    assert response["type"] == "hello_response"
    assert response["host_name"] == "com.surfboard.test"