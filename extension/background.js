chrome.action.onClicked.addListener((tab) => {
  if (tab.url) {
    const cleanUrl = tab.url.split('#')[0];
    const targetUrl = 'https://gasteizlive.vercel.app/lector?url=' + encodeURIComponent(cleanUrl);
    chrome.tabs.create({ url: targetUrl });
  }
});