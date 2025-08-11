/**
 * Content script for Surfboard test extension.
 * Provides interface for web page interaction testing.
 */

console.log('Surfboard test extension content script loaded');

// Add visual indicator that extension is active
function addExtensionIndicator() {
  const indicator = document.createElement('div');
  indicator.id = 'surfboard-extension-indicator';
  indicator.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    background: #4CAF50;
    color: white;
    padding: 5px 10px;
    border-radius: 3px;
    z-index: 10000;
    font-family: Arial, sans-serif;
    font-size: 12px;
    opacity: 0.8;
  `;
  indicator.textContent = 'Surfboard Test Extension Active';

  document.body.appendChild(indicator);

  // Remove indicator after 3 seconds
  setTimeout(() => {
    if (indicator.parentNode) {
      indicator.parentNode.removeChild(indicator);
    }
  }, 3000);
}

// Add indicator when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', addExtensionIndicator);
} else {
  addExtensionIndicator();
}

// Listen for messages from background script or injected scripts
window.addEventListener('message', (event) => {
  if (event.source !== window) return;

  if (event.data.type === 'SURFBOARD_TEST') {
    // Forward test messages to background script
    chrome.runtime.sendMessage({
      type: 'send_to_native',
      payload: event.data
    });
  }
});

// Inject a global function for testing
const script = document.createElement('script');
script.textContent = `
  window.surfboardTest = function(command, data) {
    window.postMessage({
      type: 'SURFBOARD_TEST',
      command: command,
      data: data,
      timestamp: Date.now()
    }, '*');
  };
`;
document.head.appendChild(script);
script.remove();
