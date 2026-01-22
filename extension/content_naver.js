// ==========================================================
// [OWNERS] 네이버 플레이스 연동 스크립트 (Map SPA Support)
// ==========================================================

// 1. 초기화
try {
    const urlParams = new URLSearchParams(window.location.search);
    const ownersNonce = urlParams.get('owners_nonce');

    if (ownersNonce && chrome && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({
            owners_sync_session: {
                nonce: ownersNonce,
                store_id: urlParams.get('owners_store_id'),
                return_url: urlParams.get('owners_return_url'),
                target_url: window.location.href,
                mode: urlParams.get('owners_mode') || 'REVIEW'
            }
        });
    }
} catch (e) { }

// 2. 통합 Poller (0.5초 주기 for SPA responsiveness)
const mainPoller = setInterval(() => {
    try {
        if (typeof chrome === 'undefined' || !chrome.runtime || !chrome.runtime.id) {
            clearInterval(mainPoller);
            return;
        }

        // [BLOCK Internal App]
        if (window.location.href.includes("streamlit") || window.location.href.includes("owners")) return;

        chrome.storage.local.get(["owners_sync_session"], (data) => {
            if (chrome.runtime.lastError) return;

            const session = data.owners_sync_session;
            const currentUrl = window.location.href;
            const isReviewPage = currentUrl.includes("review") || currentUrl.includes("visitor");

            // [URL Pattern Matching for Naver Map SPA]
            // Case A: Detail View (Contains /place/{id})
            const isPlaceHome = currentUrl.match(/\/place\/\d+/);
            // Case B: List View (Contains /search/ or /list/ BUT NO /place/)
            // NOTE: The Detail URL also contains /search/, so we must check !isPlaceHome for list view logic
            const isPlaceList = (currentUrl.includes("/search/") || currentUrl.includes("/list")) && !isPlaceHome;

            // ----------------------------------------------------
            // MODE A: REVIEW SYNC
            // ----------------------------------------------------
            if (session && session.mode === 'REVIEW') {
                // ... (Review Logic preserved)
                let container = document.getElementById("owners-widget-container");
                if (!container) {
                    container = document.createElement("div");
                    container.id = "owners-widget-container";
                    Object.assign(container.style, {
                        position: "fixed", bottom: "30px", right: "30px",
                        width: "340px", zIndex: "2147483647",
                        fontFamily: "'Pretendard', sans-serif",
                        borderRadius: "20px", overflow: "hidden",
                        background: "rgba(20,20,20,0.9)", color: "white",
                        boxShadow: "0 20px 50px rgba(0,0,0,0.3)"
                    });
                    document.body.appendChild(container);
                }

                if (!isReviewPage) {
                    container.innerHTML = `<div style="padding:20px; text-align:center;"><div style="font-weight:bold;">리뷰 페이지가 아닙니다</div><button id="owners-ret" style="margin-top:10px; padding:5px 10px;">돌아가기</button></div>`;
                    document.getElementById("owners-ret").onclick = () => window.location.href = session.target_url;
                } else {
                    container.innerHTML = `<div style="padding:20px;"><button id="owners-go" style="width:100%; padding:10px; background:#3B82F6; color:white; border:none; border-radius:8px;">스캔 시작</button></div>`;
                    document.getElementById("owners-go").onclick = () => {
                        let c = 0; const t = document.body.innerText;
                        const m = t.match(/전체\s*([\d,]+)/) || t.match(/리뷰\s*([\d,]+)/);
                        if (m) c = parseInt(m[1].replace(/,/g, ''), 10);
                        window.location.href = `${session.return_url}?sync_done=1&store_id=${session.store_id}&nonce=${session.nonce}&status=OK&unreplied=${c}`;
                    };
                }
            }

            // ----------------------------------------------------
            // MODE B: SCOUT (Map SPA Support)
            // ----------------------------------------------------
            else if ((session && session.mode === 'SCOUT') || (!session && (isPlaceHome || isPlaceList))) {

                // [PRIORITY 1] Detail View -> Show SCAN Button
                if (currentUrl.includes("/place/") && !isReviewPage) {
                    const oldHint = document.getElementById("owners-list-hint");
                    if (oldHint) oldHint.remove();
                    if (document.getElementById("owners-scout-widget")) return;

                    const w = document.createElement("div");
                    w.id = "owners-scout-widget";
                    Object.assign(w.style, {
                        // POSITION: Bottom-Right (Safe from Left Sidebar)
                        position: "fixed", bottom: "50px", right: "50px",
                        width: "300px", zIndex: "2147483647",
                        padding: "24px", borderRadius: "20px",
                        background: "rgba(255, 255, 255, 0.95)",
                        color: "#1F2937",
                        boxShadow: "0 20px 60px rgba(0,0,0,0.15), 0 4px 16px rgba(0,0,0,0.05)",
                        fontFamily: "'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif",
                        border: "1px solid rgba(0,0,0,0.05)",
                        backdropFilter: "blur(10px)",
                        animation: "ownersFadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1)"
                    });

                    // Animation Style
                    if (!document.getElementById('owners-style')) {
                        const s = document.createElement('style');
                        s.id = 'owners-style';
                        s.innerHTML = `@keyframes ownersFadeIn { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:translateY(0); } }`;
                        document.head.appendChild(s);
                    }

                    w.innerHTML = `
                        <div style="display:flex; align-items:center; margin-bottom:16px;">
                            <div style="background:#7C3AED; width:8px; height:8px; border-radius:50%; margin-right:10px;"></div>
                            <div style="font-weight:700; font-size:16px; color:#111827;">매장 정보 스캔</div>
                        </div>
                        <p style="font-size:14px; margin-bottom:20px; color:#6B7280; line-height:1.4;">현재 보고 계신 매장 정보를<br>오너스로 가져올까요?</p>
                        <button id="owners-scout-btn" style="
                            width:100%; padding:14px; border:none; border-radius:12px; 
                            background:linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%); 
                            color:white; font-weight:600; font-size:15px; cursor:pointer;
                            transition: transform 0.1s;
                            box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);"
                            onmouseover="this.style.transform='scale(1.02)'" 
                            onmouseout="this.style.transform='scale(1)'"
                        >🔍 맞아요, 스캔하기</button>
                        <div id="owners-close" style="text-align:center; font-size:13px; margin-top:12px; cursor:pointer; color:#9CA3AF; text-decoration:underline;">닫기</div>
                     `;
                    document.body.appendChild(w);

                    document.getElementById("owners-scout-btn").onclick = () => {
                        const btn = document.getElementById("owners-scout-btn");
                        btn.innerText = "정보를 읽는 중...";
                        btn.style.opacity = "0.8";

                        const text = document.body.innerText;
                        const hasDesc = (text.includes("소개") && text.length > 500) || !!document.querySelector(".zPfVt");
                        const descScore = (text.match(/소개|안내/g) || []).length > 0 ? 1 : 0;
                        const hasMenu = (text.includes("메뉴") || text.includes("가격")) ? 1 : 0;
                        const hasKeywords = (text.match(/#\S+/g) || []).length > 2 ? 1 : 0;
                        const hasParking = (text.includes("주차") || text.includes("발렛")) ? 1 : 0;
                        const hasWay = (text.includes("오시는") || text.includes("찾아오는")) ? 1 : 0;

                        const ret = (session && session.return_url) ? session.return_url : "http://localhost:8501";
                        const sid = (session && session.store_id) ? session.store_id : "0";

                        const result = new URLSearchParams();
                        result.set("scout_done", "1");
                        result.set("store_id", sid);
                        result.set("has_desc", descScore || hasDesc ? "1" : "0");
                        result.set("has_menu", hasMenu ? "1" : "0");
                        result.set("has_keywords", hasKeywords ? "1" : "0");
                        result.set("has_parking", hasParking ? "1" : "0");
                        result.set("has_way", hasWay ? "1" : "0");

                        window.location.href = `${ret}?${result.toString()}`;
                    };
                    document.getElementById("owners-close").onclick = () => w.remove();
                }

                // [PRIORITY 2] Everything Else -> Show PROMPT (Implicit List View)
                // If we are in Scout Mode and NOT in Detail View, we assume user needs to select a store.
                else {
                    const old = document.getElementById("owners-scout-widget");
                    if (old) old.remove();
                    if (document.getElementById("owners-list-hint")) return;

                    const hint = document.createElement("div");
                    hint.id = "owners-list-hint";
                    Object.assign(hint.style, {
                        // POSITION: Bottom-Right
                        position: "fixed", bottom: "50px", right: "50px",
                        width: "auto", maxWidth: "300px", zIndex: "2147483647",
                        padding: "16px 24px", borderRadius: "50px",
                        background: "#1F2937",
                        color: "white", boxShadow: "0 10px 30px rgba(0,0,0,0.3)",
                        fontFamily: "'Pretendard', sans-serif",
                        border: "1px solid rgba(255,255,255,0.1)",
                        animation: "ownersFadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1)",
                        display: "flex", alignItems: "center", justifyContent: "center", gap: "10px",
                        whiteSpace: "nowrap"
                    });

                    // Same animation keyframes used

                    hint.innerHTML = `
                        <span style="font-size:20px;">👈</span>
                        <span style="font-weight:600; font-size:15px;">왼쪽 목록에서 매장을 선택해주세요</span>
                    `;
                    document.body.appendChild(hint);
                }
            }
        });
    } catch (e) {
        // Suppress errors
    }
}, 500);