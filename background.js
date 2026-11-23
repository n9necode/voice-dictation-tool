chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((err) => console.error(err));

chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.type === "mic-granted") return;
});
