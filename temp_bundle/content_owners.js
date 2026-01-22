// content_owners.js (OWNERS에서 작동)

(function () {
  // =========================
  // A) 기존: 리뷰 동기화 신호 (owners-sync-signal)
  // =========================
  setInterval(() => {
    const signal = document.getElementById("owners-sync-signal");
    if (signal && !signal.classList.contains("handled")) {
      signal.classList.add("handled");

      const nonce = signal.getAttribute("data-nonce");
      const storeId = signal.getAttribute("data-store-id");
      const storeName = signal.getAttribute("data-store-name");
      const targetUrl = signal.getAttribute("data-target-url");
      const returnUrl = window.location.href.split("?")[0];

      if (nonce && targetUrl) {
        chrome.storage.local.set(
          {
            sync_nonce: nonce,
            sync_store_id: storeId,
            sync_store_name: storeName,
            return_url: returnUrl,
            target_review_url: targetUrl
          },
          () => {
            console.log("[OWNERS][REVIEW] 이동:", targetUrl);
            window.location.href = targetUrl;
          }
        );
      }
    }
  }, 500);

  // =========================
  // B) 추가: 가격 스캔 신호 (owners-price-signal)
  //   - signal이 보이면 storage 저장 후 새 탭 열기
  // =========================
  const PRICE_SIGNAL_SELECTOR = ".owners-price-signal, #owners-price-signal";

  setInterval(() => {
    const el = document.querySelector(PRICE_SIGNAL_SELECTOR);
    if (!el) return;

    if (el.classList.contains("handled")) return;
    el.classList.add("handled");

    const itemId = el.getAttribute("data-item-id");
    const nonce = el.getAttribute("data-nonce");
    const targetUrl = el.getAttribute("data-target-url");

    const ownersReturnUrl = window.location.href.split("?")[0]; // ORDER든 DASHBOARD든 base만

    if (!itemId || !nonce || !targetUrl) {
      console.log("[OWNERS][PRICE] signal found but missing fields", { itemId, nonce, targetUrl });
      return;
    }

    console.log("[OWNERS][PRICE] signal OK => open tab", { itemId, nonce, targetUrl });

    chrome.storage.local.set(
      {
        owners_return_url: ownersReturnUrl,
        pending_item_id: String(itemId),
        pending_nonce: String(nonce),
        pending_started_at: Date.now()
      },
      () => {
        // 새 탭 열기: background.js에게 요청
        chrome.runtime.sendMessage({ type: "OPEN_TARGET", url: targetUrl }, () => {
          // 혹시 메시지가 막히면 fallback
          try {
            window.open(targetUrl, "_blank");
          } catch (e) {}
        });
      }
    );
  }, 300);

})();
