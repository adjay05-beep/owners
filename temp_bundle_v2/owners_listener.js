(function () {
  const SIGNAL_CLASS = ".owners-price-signal";

  function getBaseUrlWithoutQuery() {
    const u = new URL(window.location.href);
    u.search = "";
    return u.toString();
  }

  async function startIfSignalExists() {
    const el = document.querySelector(SIGNAL_CLASS);
    if (!el) return;

    const itemId = el.getAttribute("data-item-id");
    const nonce = el.getAttribute("data-nonce");
    const targetUrl = el.getAttribute("data-target-url");

    if (!itemId || !nonce || !targetUrl) return;

    // 저장(네이버 페이지에서 결과를 되돌려줄 때 사용)
    await chrome.storage.local.set({
      owners_return_url: getBaseUrlWithoutQuery(),
      pending_item_id: itemId,
      pending_nonce: nonce,
      pending_started_at: Date.now()
    });

    // 네이버 페이지 열기(새탭)
    chrome.runtime?.sendMessage?.({ type: "OPEN_TARGET", url: targetUrl });
  }

  // manifest v3 에서는 content script에서 tabs API 직접 호출이 제한적이라
  // message로 열게 하고, background가 없으면 아래 fallback으로 그냥 location 이동도 가능.
  // (여기서는 message만 보냄)

  // DOM 변화 감지 (Streamlit rerun으로 신호가 늦게 생길 수 있음)
  const obs = new MutationObserver(() => startIfSignalExists());
  obs.observe(document.documentElement, { childList: true, subtree: true });

  // 초기 1회
  startIfSignalExists();
})();
