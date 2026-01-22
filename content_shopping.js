// content_shopping.js (DEBUG minimal)

console.log("[OWNERS][SHOPPING] content_shopping.js loaded:", location.href);

// 혹시 확장 프로그램이 주입됐는지 화면에서도 바로 보이게(10초 후 자동 제거)
try {
  const badge = document.createElement("div");
  badge.textContent = "OWNERS SHOPPING SCANNER LOADED";
  badge.style.position = "fixed";
  badge.style.top = "10px";
  badge.style.right = "10px";
  badge.style.zIndex = "999999";
  badge.style.background = "rgba(0,0,0,0.75)";
  badge.style.color = "white";
  badge.style.padding = "8px 10px";
  badge.style.borderRadius = "8px";
  badge.style.fontSize = "12px";
  document.documentElement.appendChild(badge);
  setTimeout(() => badge.remove(), 10000);
} catch (e) {}
