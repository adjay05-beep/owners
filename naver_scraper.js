(async function () {
  const st = await chrome.storage.local.get([
    "owners_return_url",
    "pending_item_id",
    "pending_nonce",
    "pending_started_at"
  ]);

  // 스캔 대기 상태가 아니면 아무것도 안함
  if (!st.pending_item_id || !st.pending_nonce || !st.owners_return_url) return;

  // 너무 오래됐으면(예: 2분) FAIL로 돌려보냄
  if (st.pending_started_at && Date.now() - st.pending_started_at > 120000) {
    const failUrl = new URL(st.owners_return_url);
    failUrl.searchParams.set("price_done", "1");
    failUrl.searchParams.set("item_id", String(st.pending_item_id));
    failUrl.searchParams.set("nonce", String(st.pending_nonce));
    failUrl.searchParams.set("status", "FAIL");
    window.location.href = failUrl.toString();
    return;
  }

  function pickText(selList) {
    for (const sel of selList) {
      const el = document.querySelector(sel);
      if (el && el.textContent) {
        const t = el.textContent.trim();
        if (t) return t;
      }
    }
    return "";
  }

  function extractPriceNumber(text) {
    if (!text) return "";
    // "12,900원" -> "12900"
    const m = text.replace(/\s/g, "").match(/([\d,]+)원/);
    return m ? m[1].replace(/,/g, "") : "";
  }

  // 네이버 쇼핑은 페이지 유형이 다양해서 후보 셀렉터를 여러 개 둔다
  const titleSel = [
    "h2.top_summary_title__15yAr",
    "h2[class*='top_summary_title']",
    "h3[class*='product_title']",
    "h1"
  ];

  const priceSel = [
    "span.price_num__2WUXn",
    "span[class*='price_num']",
    "strong[class*='price']",
    "em[class*='price']"
  ];

  async function tryScrapeOnce() {
    const title = pickText(titleSel);
    const priceRaw = pickText(priceSel);
    const price = extractPriceNumber(priceRaw) || extractPriceNumber(document.body.innerText);

    // 너무 공격적이면 오탐이 있으니 title+price 둘 중 하나라도 있으면 OK로 보냄(원하면 더 엄격하게 가능)
    if (title || price) {
      const u = new URL(st.owners_return_url);
      u.searchParams.set("price_done", "1");
      u.searchParams.set("item_id", String(st.pending_item_id));
      u.searchParams.set("nonce", String(st.pending_nonce));
      u.searchParams.set("status", "OK");
      if (price) u.searchParams.set("price", price);
      if (title) u.searchParams.set("title", title);
      u.searchParams.set("url", window.location.href);

      // 스캔 종료(중복 방지)
      await chrome.storage.local.remove(["pending_item_id", "pending_nonce", "pending_started_at"]);

      window.location.href = u.toString();
      return true;
    }
    return false;
  }

  // 1) 즉시 시도
  if (await tryScrapeOnce()) return;

  // 2) 로딩 늦으면 잠깐 기다리며 재시도
  let tries = 0;
  const timer = setInterval(async () => {
    tries += 1;
    if (await tryScrapeOnce()) {
      clearInterval(timer);
      return;
    }
    if (tries >= 20) { // 약 10초
      clearInterval(timer);
      const u = new URL(st.owners_return_url);
      u.searchParams.set("price_done", "1");
      u.searchParams.set("item_id", String(st.pending_item_id));
      u.searchParams.set("nonce", String(st.pending_nonce));
      u.searchParams.set("status", "FAIL");
      u.searchParams.set("url", window.location.href);
      await chrome.storage.local.remove(["pending_item_id", "pending_nonce", "pending_started_at"]);
      window.location.href = u.toString();
    }
  }, 500);
})();
