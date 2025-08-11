/**
 * Popup script for Surfboard test extension.
 * Provides UI for testing Native Messaging functionality.
 */

document.addEventListener('DOMContentLoaded', () => {
  const statusDiv = document.getElementById('status');
  const logDiv = document.getElementById('log');
  const pingBtn = document.getElementById('ping-btn');
  const testCmdBtn = document.getElementById('test-cmd-btn');
  const clearLogBtn = document.getElementById('clear-log-btn');
  
  function log(message) {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.textContent = `[${timestamp}] ${message}`;
    logDiv.appendChild(logEntry);
    logDiv.scrollTop = logDiv.scrollHeight;
  }
  
  function updateStatus(connected) {
    if (connected) {
      statusDiv.className = 'status connected';
      statusDiv.textContent = 'Native Messaging: Connected';
      pingBtn.disabled = false;
      testCmdBtn.disabled = false;
    } else {
      statusDiv.className = 'status disconnected';
      statusDiv.textContent = 'Native Messaging: Disconnected';
      pingBtn.disabled = true;
      testCmdBtn.disabled = true;
    }
  }
  
  // Check connection status by sending message to background
  chrome.runtime.sendMessage({ type: 'check_connection' }, (response) => {
    if (chrome.runtime.lastError) {
      log('Error checking connection: ' + chrome.runtime.lastError.message);
      updateStatus(false);
    } else {
      updateStatus(response && response.connected);
    }
  });
  
  // Button event listeners
  pingBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({
      type: 'send_to_native',
      payload: { type: 'ping', timestamp: Date.now() }
    }, (response) => {
      if (chrome.runtime.lastError) {
        log('Error sending ping: ' + chrome.runtime.lastError.message);
      } else {
        log('Ping sent successfully');
      }
    });
  });
  
  testCmdBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({
      type: 'send_to_native',
      payload: {
        type: 'test_command',
        data: { action: 'navigate', url: 'https://example.com' },
        timestamp: Date.now()
      }
    }, (response) => {
      if (chrome.runtime.lastError) {
        log('Error sending test command: ' + chrome.runtime.lastError.message);
      } else {
        log('Test command sent successfully');
      }
    });
  });
  
  clearLogBtn.addEventListener('click', () => {
    logDiv.innerHTML = '';
  });
  
  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'native_message') {
      log(`Received: ${JSON.stringify(message.data)}`);
    }
  });
  
  log('Popup initialized');
});