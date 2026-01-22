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

  // 3. Injected Script for Scout (Naver Place Scraper) - SMART AUDIT VERSION
  const INJECTED_SCRIPT = `
    (function() {
      if (window.ownersInjected) return;
      window.ownersInjected = true;

      function log(msg) { window.ReactNativeWebView.postMessage(JSON.stringify({type: 'LOG', msg})); }
      log("Scanner Started...");

      // 1. Auto-Scroll to bottom (Force Naver to load hidden content)
      let scrollAttempts = 0;
      const scrollInterval = setInterval(() => {
          window.scrollBy(0, 800);
          scrollAttempts++;
          if (scrollAttempts > 4) {
              clearInterval(scrollInterval);
              log("Scroll Finished.");
          }
      }, 500);

      // 2. Data Extraction
      let scanCount = 0;
      const scanInterval = setInterval(() => {
        scanCount++;
        try {
            const body = document.body;
            const text = body.innerText || "";
            const html = body.innerHTML || "";
            
            if (scanCount % 2 === 0) log("Scanning... Pass: " + scanCount + " | TextLen: " + text.length);

            // Check if page is loaded
            if (text.length > 300) {
                
                // [A] Basic Info
                const hasHours = (text.includes("영업 중") || text.includes("매일") || text.includes("시 시작") || html.includes("time") || text.includes("영업시간")) ? "1" : "0";
                const hasPhone = (text.match(/\\d{2,3}-\\d{3,4}-\\d{4}/) || html.includes("tel:")) ? "1" : "0";
                const hasAddress = (text.includes("구 ") && text.includes("동 ") && text.match(/[가-히]{1,4}로/)) ? "1" : "0";
                
                // [B] Content Tabs
                const hasMenu = (text.includes("메뉴") || text.includes("가격") || html.includes("/menu")) ? "1" : "0";
                const hasNews = (text.includes("소식") || text.includes("새소식") || html.includes("/feed") || text.includes("최근 소식")) ? "1" : "0";
                const hasDesc = (text.includes("소개") || text.includes("설명") || (text.includes("인사말") && text.length > 500)) ? "1" : "0";
                
                // [C] Convenience
                const hasKeywords = (text.includes("키워드") || html.includes("tag_item") || text.match(/#\\S+/g)?.length > 0) ? "1" : "0";
                const hasParking = (text.includes("주차") || text.includes("발렛")) ? "1" : "0";
                const hasWay = (text.includes("오시는") || text.includes("길찾기") || text.includes("출구") || text.includes("m")) ? "1" : "0";
                
                // Detailed check log
                if (scanCount === 10) {
                    log("Current State: H=" + hasHours + " P=" + hasPhone + " N=" + hasNews + " D=" + hasDesc);
                }

                // SUCCESS CRITERIA: Wait enough for scroll tasks but return early if we found a lot
                const foundCount = [hasHours, hasPhone, hasAddress, hasMenu, hasNews, hasDesc, hasKeywords].filter(x => x === "1").length;
                
                if (scanCount > 12 || foundCount >= 7) { 
                     clearInterval(scanInterval);
                     log("Scan Success. Found Items: " + foundCount);
                     const result = {
                        type: 'SCOUT_RESULT',
                        data: {
                            has_desc: hasDesc,
                            has_menu: hasMenu,
                            has_keywords: hasKeywords,
                            has_parking: hasParking,
                            has_way: hasWay,
                            has_hours: hasHours,
                            has_phone: hasPhone,
                            has_address: hasAddress,
                            has_news: hasNews
                        }
                    };
                    window.ReactNativeWebView.postMessage(JSON.stringify(result));
                }
            }
        } catch (e) {
            log("Scan Error: " + e.message);
        }
        
        // Safety Fallback (18 seconds)
        if (scanCount > 30) {
             clearInterval(scanInterval);
             log("SCAN TIMEOUT [FATAL] - Body Text Sample: " + (document.body.innerText || "").substring(0, 100));
             window.ReactNativeWebView.postMessage(JSON.stringify({
                type: 'SCOUT_RESULT',
                data: { has_desc:"0", has_menu:"0", has_keywords:"0", has_parking:"0", has_way:"0", has_hours:"0", has_phone:"0", has_address:"0", has_news:"0" }
             }));
        }
        
      }, 600);
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
