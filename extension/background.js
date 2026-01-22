// background.js (minimal)
chrome.runtime.onMessage.addListener((msg) => {
  if (msg?.type === "OPEN_TARGET" && msg?.url) {
    chrome.tabs.create({ url: msg.url });
  }
});
