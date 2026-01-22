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

  // 3. Injected Script for Scout (Naver Place Scraper) - OPTIMISTIC VERSION
  const INJECTED_SCRIPT = `
    (function() {
      // Prevent multiple injections
      if (window.ownersInjected) return;
      window.ownersInjected = true;

      function log(msg) { window.ReactNativeWebView.postMessage(JSON.stringify({type: 'LOG', msg})); }

      let attempts = 0;
      const intervalId = setInterval(() => {
        attempts++;
        try {
            const bodyText = document.body.innerText || "";
            
            // Check if page has some content
            if (bodyText.length > 50) {
                
                // Logic for Mobile Place
                const hasNews = (bodyText.includes("소식") || bodyText.includes("새소식")) ? "1" : "0";
                const hasMenu = (bodyText.includes("메뉴") || bodyText.includes("가격")) ? "1" : "0";
                
                const hasDesc = (bodyText.includes("소개") && bodyText.length > 100) ? "1" : "0";
                const hasKeywords = (bodyText.includes("키워드") || bodyText.match(/#\S+/g)?.length > 1) ? "1" : "0";
                const hasParking = (bodyText.includes("주차") || bodyText.includes("발렛")) ? "1" : "0";
                const hasWay = (bodyText.includes("오시는") || bodyText.includes("길찾기")) ? "1" : "0";
                
                // If we found meaningful content OR we simply timed out (force return partial data)
                if (hasDesc === "1" || hasMenu === "1" || attempts > 2) {
                     clearInterval(intervalId);
                     const result = {
                        type: 'SCOUT_RESULT',
                        data: {
                            has_desc: hasDesc,
                            has_menu: hasMenu,
                            has_keywords: hasKeywords,
                            has_parking: hasParking,
                            has_way: hasWay
                        }
                    };
                    window.ReactNativeWebView.postMessage(JSON.stringify(result));
                }
            }
        } catch (e) {
            // Keep trying
        }
        
        // Safety Fallback: Force quit and send something after 3 seconds
        if (attempts > 5) {
             clearInterval(intervalId);
             window.ReactNativeWebView.postMessage(JSON.stringify({
                type: 'SCOUT_RESULT',
                data: { has_desc:"0", has_menu:"0", has_keywords:"0", has_parking:"0", has_way:"0" } // Fallback empty
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
