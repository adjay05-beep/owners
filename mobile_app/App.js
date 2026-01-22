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

  const dashboardRef = useRef(null);
  const scoutRef = useRef(null);

  // 3. Injected Script for Scout (Naver Place Scraper)
  const INJECTED_SCRIPT = `
    (function() {
      if (window.ownersInjected) return;
      window.ownersInjected = true;

      function log(msg) { window.ReactNativeWebView.postMessage(JSON.stringify({type: 'LOG', msg})); }

      setInterval(() => {
        try {
            const text = document.body.innerText;
            const currentUrl = window.location.href;
            
            // LOGIC: Check tabs on the PC Place Page
            // The tabs are usually in a <div role="tablist"> or similar.
            // On PC Map: 
            // - "홈" (Home)
            // - "소식" (News)
            // - "메뉴" (Menu)
            // - "리뷰" (Review)
            // - "사진" (Photo)
            // - "정보" (Info)
            
            // If the store hasn't uploaded 'Menu', the 'Menu' tab might still exist but be empty, 
            // OR sometimes it doesn't show up if completely empty. 
            // Naver Place usually shows tabs even if empty, but "소식" often disappears if no news.
            
            // Let's grab all text from the tab list to see what is enabled.
            const tabList = document.querySelector("div[role='tablist']") || document.body;
            const tabText = tabList.innerText; 
            const bodyText = document.body.innerText;

            const hasNews = tabText.includes("소식") ? "1" : "0";
            const hasMenu = (tabText.includes("메뉴") || bodyText.includes("가격")) ? "1" : "0";
            
            // For 'Info' (Description, Parking, Way), we usually need to look at the 'Home' tab content or 'Info' tab.
            // On 'Home' tab, they appear as sections.
            const hasDesc = (bodyText.includes("소개") && bodyText.length > 300) ? "1" : "0"; 
            const hasKeywords = (bodyText.match(/#\S+/g) || []).length > 2 ? "1" : "0";
            const hasParking = (bodyText.includes("주차") || bodyText.includes("발렛")) ? "1" : "0";
            const hasWay = (bodyText.includes("오시는") || bodyText.includes("찾아오는")) ? "1" : "0";
            
            // Only send if we found at least something distinctive (e.g. "홈" or Place title)
            if (document.querySelector(".zPfVt") || bodyText.includes("복사")) {
                 setTimeout(() => {
                    const result = {
                        type: 'SCOUT_RESULT',
                        data: {
                            has_desc: hasDesc,
                            has_menu: hasMenu,
                            has_keywords: hasKeywords,
                            has_parking: hasParking,
                            has_way: hasWay,
                            // Adding logic for 'News' later if needed in DB
                        }
                    };
                    window.ReactNativeWebView.postMessage(JSON.stringify(result));
                }, 1500);
            }
        } catch (e) {
            log("Scrape Error: " + e.toString());
        }
      }, 1000);
    })();
    true; 
  `;

  // 4. Message Handlers
  const onScoutMessage = (event) => {
    try {
      const msg = JSON.parse(event.nativeEvent.data);

      if (msg.type === 'SCOUT_RESULT') {
        const params = new URLSearchParams(msg.data);
        params.append('scout_done', '1');
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
        javaScriptEnabled={true}
        domStorageEnabled={true}
      />

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
        <View style={{ height: 1, width: 1, opacity: 0, position: 'absolute' }}>
          <WebView
            ref={scoutRef}
            source={{ uri: scoutUrl }}
            userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
  }
});
