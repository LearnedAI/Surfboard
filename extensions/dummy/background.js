/**
 * Background script for Surfboard test extension.
 * Handles Native Messaging communication with the Surfboard bridge.
 */

const NATIVE_HOST = 'com.surfboard.bridge';

// Port for native messaging
let nativePort = null;

// Connect to native messaging host on startup
chrome.runtime.onStartup.addListener(connectToNativeHost);
chrome.runtime.onInstalled.addListener(connectToNativeHost);

function connectToNativeHost() {
  try {
    nativePort = chrome.runtime.connectNative(NATIVE_HOST);

    nativePort.onMessage.addListener((message) => {
      console.log('Received from native host:', message);
      handleNativeMessage(message);
    });

    nativePort.onDisconnect.addListener(() => {
      console.log('Native host disconnected');
      if (chrome.runtime.lastError) {
        console.error('Native messaging error:', chrome.runtime.lastError.message);
      }
      nativePort = null;
    });

    // Send initial hello message
    sendToNativeHost({ type: 'hello', timestamp: Date.now() });

  } catch (error) {
    console.error('Failed to connect to native host:', error);
  }
}

function sendToNativeHost(message) {
  if (nativePort) {
    nativePort.postMessage(message);
  } else {
    console.error('Native port not connected');
  }
}

function handleNativeMessage(message) {
  switch (message.type) {
    case 'ping':
      sendToNativeHost({ type: 'pong', timestamp: Date.now() });
      break;

    case 'test_command':
      // Simulate executing a test command
      sendToNativeHost({
        type: 'command_result',
        success: true,
        data: { message: 'Test command executed successfully' }
      });
      break;

    default:
      console.log('Unknown message type:', message.type);
  }
}

// Handle messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'send_to_native') {
    sendToNativeHost(message.payload);
    sendResponse({ success: true });
  }
});
