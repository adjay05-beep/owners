import React, { useState, useRef } from 'react';
import { StyleSheet, View, SafeAreaView, StatusBar, Platform, Modal, TouchableOpacity, Text, ActivityIndicator } from 'react-native';
import { WebView } from 'react-native-webview';

export default function App() {
  // 1. Configuration
  // PERMANENT SERVER (Streamlit Cloud)
  const SERVER_URL = "https://owners-twrcya3hrhhktgutcwsmtc.streamlit.app";

  // 2. State
  const [scoutUrl, setScoutUrl] = useState(null);   // Hidden Background Task
  const [reviewUrl, setReviewUrl] = useState(null); // Visible Modal Task
  const [isLoading, setIsLoading] = useState(false); // Spinner for Scout
  const [isExternal, setIsExternal] = useState(false); // If user is browsing outside

  const dashboardRef = useRef(null);
  const scoutRef = useRef(null);

  // 3. Injected Script for Scout (Naver Place Scraper) - TRANSPARENT AUDIT VERSION
  const INJECTED_SCRIPT = `
    (function() {
      if (window.ownersInjected) return;
      window.ownersInjected = true;

      function log(msg) { window.ReactNativeWebView.postMessage(JSON.stringify({type: 'LOG', msg})); }
      log("Advanced Scanner Booted.");

      // 1. Auto-Scroll (Gentle but steady)
      let scrollInt = setInterval(() => { window.scrollBy(0, 400); }, 1000);
      setTimeout(() => clearInterval(scrollInt), 12000);

      // 2. Continuous Scan
      let passes = 0;
      const scanInt = setInterval(() => {
        passes++;
        try {
            const body = document.body;
            const text = body.innerText || "";
            const html = body.innerHTML || "";
            
            if (passes % 3 === 0) log("Pass " + passes + " | Len: " + text.length + " | Preview: " + text.substring(0, 40).replace(/\\n/g, " "));

            // [NEW] Page Not Found Detection
            if (text.includes("페이지를 찾을 수 없습니다") || text.includes("존재하지 않는") || text.includes("잘못된 접근")) {
                clearInterval(scanInt);
                log("FATAL: Place Page Not Found on Naver.");
                window.ReactNativeWebView.postMessage(JSON.stringify({
                    type: 'SCOUT_RESULT',
                    data: { is_invalid_url: "1" }
                }));
                return;
            }

            if (text.length > 50) {
                // A. Matchers with Evidence Capture
                function findEvidence(patterns, source) {
                    for(let p of patterns) {
                        if (source.includes(p)) return p;
                    }
                    return null;
                }

                // [Hours] -> Check more patterns
                const hourPatterns = ["영업", "매일", "시 시작", "시 종료", "휴무", "브레이크타임", "시간"];
                const evHours = findEvidence(hourPatterns, text) || (html.includes("time") ? "HTML Tag Found" : null);

                // [Phone]
                const phoneMatch = text.match(/\\d{2,3}-\\d{3,4}-\\d{4}/);
                const evPhone = phoneMatch ? phoneMatch[0] : (html.includes("tel:") ? "Tel Link Found" : null);

                // [Address]
                const addrPatterns = ["서울", "경기", "인천", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주", "구 ", "동 ", "로 "];
                const evAddress = findEvidence(addrPatterns, text);
                
                // [Content]
                const evMenu = findEvidence(["메뉴", "가격표", "가격", "피드", "원"], text) || (html.includes("/menu") ? "Menu Tab Link" : null);
                const evNews = findEvidence(["최근 소식", "새소식", "소식", "공지", "이벤트"], text) || (html.includes("/feed") ? "Feed Tab Link" : null);
                const evDesc = findEvidence(["소개", "설명", "인사말", "브리핑"], text) || (text.length > 1500 ? "Long Content Found" : null);
                
                // [Convenience]
                const evKeywords = findEvidence(["키워드", "태그", "해시태그"], text) || (text.match(/#\\S+/)/ ? "HashTag Found" : null);
                const evParking = findEvidence(["주차", "발렛", "무료주차", "공영주차장"], text);
                const evWay = findEvidence(["오시는", "길찾기", "출구", "역 "], text);
                
                const score = [evHours, evPhone, evAddress, evMenu, evNews, evDesc].filter(x => !!x).length;
                
                if (passes > 18 || score >= 6) {
                    clearInterval(scanInt);
                    log("Scan Complete. Score=" + score);
                    
                    const auditDetails = {
                        hours: evHours, phone: evPhone, address: evAddress,
                        menu: evMenu, news: evNews, desc: evDesc,
                        keywords: evKeywords, parking: evParking, way: evWay
                    };

                    window.ReactNativeWebView.postMessage(JSON.stringify({
                        type: 'SCOUT_RESULT',
                        data: {
                            has_desc: evDesc ? "1" : "0",
                            has_menu: evMenu ? "1" : "0",
                            has_keywords: evKeywords ? "1" : "0",
                            has_parking: evParking ? "1" : "0",
                            has_way: evWay ? "1" : "0",
                            has_hours: evHours ? "1" : "0",
                            has_phone: evPhone ? "1" : "0",
                            has_address: evAddress ? "1" : "0",
                            has_news: evNews ? "1" : "0",
                            audit_json: JSON.stringify(auditDetails)
                        }
                    }));
                }
            }
        } catch (e) { log("Error: " + e.message); }

        if (passes > 30) { 
            clearInterval(scanInt);
            log("TIMEOUT.");
            window.ReactNativeWebView.postMessage(JSON.stringify({
                type: 'SCOUT_RESULT',
                data: { has_desc:"0", has_menu:"0", has_keywords:"0", has_parking:"0", has_way:"0", has_hours:"0", has_phone:"0", has_address:"0", has_news:"0" }
            }));
        }
      }, 800);
    })();
    true;
  `;

  // 4. Message Handlers
  const onScoutMessage = (event) => {
    try {
      const msg = JSON.parse(event.nativeEvent.data);

      if (msg.type === 'SCOUT_RESULT') {
        // Extract IDs from the Worker URL
        const workerUrl = new URL(scoutUrl);
        const sid = workerUrl.searchParams.get("owners_store_id") || "";
        const nonce = workerUrl.searchParams.get("owners_nonce") || "";

        const params = new URLSearchParams(msg.data);
        params.append('scout_done', '1');
        params.append('owners_store_id', sid);
        params.append('owners_nonce', nonce);

        const returnUrl = `${SERVER_URL}?${params.toString()}`;

        // Reset
        setScoutUrl(null);
        setIsLoading(false); // Hide Spinner

        // Navigate Dashboard
        dashboardRef.current.injectJavaScript(`
           window.location.href = "${returnUrl}";
         `);
      }
      if (msg.type === 'LOG') console.log("[MobileScout]", msg.msg);
    } catch (e) { }
  };

  // 5. Navigation Interceptor
  const shouldStartLoadWithRequest = (request) => {
    const url = request.url;

    // CASE A: Scout Mode (Background)
    if (url.includes("owners_mode=SCOUT") || (url.includes("map.naver.com") && !url.includes("owners_mode=REVIEW"))) {
      setScoutUrl(url);
      setIsLoading(true); // Show Feedback

      // SAFETY TIMEOUT: Force stop after 15 seconds if no result
      setTimeout(() => {
        setIsLoading((prev) => {
          if (prev) {
            // If still loading, kill it
            setScoutUrl(null);
            alert("스캔 시간이 초과되었습니다. (네이버 접속 지연)");
            return false;
          }
          return prev;
        });
      }, 15000);

      return false;
    }

    // CASE B: Review Mode (Visible Modal)
    if (url.includes("owners_mode=REVIEW")) {
      setReviewUrl(url); // Open Modal
      return false;
    }

    // CASE C: Fallback for other Naver links (like generic searches)
    // If we are strictly controlling, maybe block them too? 
    // For now let them slide if they aren't explicit modes.

    return true;
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />

      {/* MAIN DASHBOARD */}
      <WebView
        ref={dashboardRef}
        source={{ uri: SERVER_URL }}
        style={styles.webview}
        onShouldStartLoadWithRequest={shouldStartLoadWithRequest}
        onNavigationStateChange={(navState) => {
          // Check if we are on the main server or external
          if (!navState.url.includes("streamlit.app")) {
            setIsExternal(true);
          } else {
            setIsExternal(false);
          }
        }}
        javaScriptEnabled={true}
        domStorageEnabled={true}
      />

      {/* PRETTY HOME BUTTON (When external) */}
      {isExternal && (
        <TouchableOpacity
          style={styles.homeBtn}
          onPress={() => {
            // Go Home
            dashboardRef.current.injectJavaScript(`window.location.href = "${SERVER_URL}";`);
            setIsExternal(false);
          }}
        >
          <Text style={styles.homeBtnText}>🏠 홈으로 돌아가기</Text>
        </TouchableOpacity>
      )}

      {/* LOADER OVERLAY (For Scout) */}
      {isLoading && (
        <View style={styles.loadingOverlay}>
          <View style={styles.loadingBox}>
            <ActivityIndicator size="large" color="#FFD700" />
            <Text style={styles.loadingText}>매장 정보를 읽어오는 중...</Text>
          </View>
        </View>
      )}

      {/* HIDDEN SCOUT WORKER */}
      {scoutUrl && (
        <View style={{ position: 'absolute', width: '100%', height: '100%', zIndex: -1, opacity: 0.01 }}>
          <WebView
            ref={scoutRef}
            source={{ uri: scoutUrl }}
            injectedJavaScript={INJECTED_SCRIPT}
            onMessage={onScoutMessage}
            incognito={true}
          />
        </View>
      )}

      {/* REVIEW MODAL (Visible Browser) */}
      <Modal visible={!!reviewUrl} animationType="slide" presentationStyle="pageSheet">
        <SafeAreaView style={{ flex: 1, backgroundColor: '#fff' }}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>리뷰 답글 달기</Text>
            <TouchableOpacity onPress={() => setReviewUrl(null)} style={styles.closeBtn}>
              <Text style={styles.closeText}>닫기</Text>
            </TouchableOpacity>
          </View>
          {reviewUrl && (
            <WebView
              source={{ uri: reviewUrl }}
              style={{ flex: 1 }}
            />
          )}
        </SafeAreaView>
      </Modal>

    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0
  },
  webview: {
    flex: 1,
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.3)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 999
  },
  loadingBox: {
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 12,
    alignItems: 'center',
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    fontWeight: '600',
    color: '#333'
  },
  modalHeader: {
    height: 50,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#eee'
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: 'bold'
  },
  closeBtn: {
    padding: 8,
    backgroundColor: '#eee',
    borderRadius: 8
  },
  closeText: {
    fontSize: 14,
    fontWeight: '600'
  },
  homeBtn: {
    position: 'absolute',
    bottom: 30,
    alignSelf: 'center',
    backgroundColor: '#FFD700',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 25,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    elevation: 6,
    zIndex: 1000
  },
  homeBtnText: {
    fontWeight: 'bold',
    color: '#333',
    fontSize: 15
  }
});
