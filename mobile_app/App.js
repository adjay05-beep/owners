import React, { useState, useRef } from 'react';
import { StyleSheet, View, SafeAreaView, StatusBar, Platform } from 'react-native';
import { WebView } from 'react-native-webview';

export default function App() {
  // 1. Configuration
  // PLEASE REPLACE THIS IP with your actual PC IP if it changes.
  const SERVER_URL = "https://spicy-ghosts-deny.loca.lt";

  // 2. State
  const [scoutUrl, setScoutUrl] = useState(null);
  const dashboardRef = useRef(null);
  const scoutRef = useRef(null);

  // 3. Injected Script for Scout (Naver Place Scraper)
  // This replaces 'content_naver.js' logic for the Mobile App environment.
  const INJECTED_SCRIPT = `
    (function() {
      // Prevent multiple injections
      if (window.ownersInjected) return;
      window.ownersInjected = true;

      function log(msg) { window.ReactNativeWebView.postMessage(JSON.stringify({type: 'LOG', msg})); }

      // Poller to check if we are on a valid page
      setInterval(() => {
        try {
            const text = document.body.innerText;
            const currentUrl = window.location.href;
            
            // Check if we are on a Detail Page (contains /place/)
            if (currentUrl.includes("/place/") && !currentUrl.includes("review")) {
                
                // DATA EXTRACTION LOGIC (Same as content_naver.js)
                const hasDesc = (text.includes("소개") && text.length > 500) || !!document.querySelector(".zPfVt");
                const descScore = (text.match(/소개|안내/g) || []).length > 0 ? 1 : 0;
                const hasMenu = (text.includes("메뉴") || text.includes("가격")) ? 1 : 0;
                const hasKeywords = (text.match(/#\S+/g) || []).length > 2 ? 1 : 0;
                const hasParking = (text.includes("주차") || text.includes("발렛")) ? 1 : 0;
                const hasWay = (text.includes("오시는") || text.includes("찾아오는")) ? 1 : 0;
                
                // AUTO-SEND RESULT (No button click needed!)
                // Use a slight delay to ensure dynamic content loads
                setTimeout(() => {
                    const result = {
                        type: 'SCOUT_RESULT',
                        data: {
                            has_desc: descScore || hasDesc ? "1" : "0",
                            has_menu: hasMenu ? "1" : "0",
                            has_keywords: hasKeywords ? "1" : "0",
                            has_parking: hasParking ? "1" : "0",
                            has_way: hasWay ? "1" : "0"
                        }
                    };
                    window.ReactNativeWebView.postMessage(JSON.stringify(result));
                }, 2000); 
            }
        } catch (e) {
            log("Scrape Error: " + e.toString());
        }
      }, 1000);
    })();
    true; // Note: injectedJavaScript requires a true return
  `;

  // 4. Bridge Logic
  const onDashboardMessage = (event) => {
    try {
      // The Dashboard (Streamlit) sends messages via special link or console override?
      // Actually Streamlit is hard to inject into. 
      // STRATEGY: We intercept URL changes or specific 'owners://' links from Streamlit.
      // But for now, let's assume the user navigates to the 'Scout' page in Streamlit is enough?
      // No, we need a trigger.

      // TEMPORARY PROTOTYPE LOGIC:
      // We check if the Dashboard URL contains 'owners_mode=SCOUT' and 'target_url' 
      // But since Streamlit is SPA, we might not catch it in onNavigationStateChange easily.

      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === 'START_SCAN') {
        setScoutUrl(data.url);
      }
    } catch (e) { }
  };

  const onScoutMessage = (event) => {
    try {
      const msg = JSON.parse(event.nativeEvent.data);

      if (msg.type === 'SCOUT_RESULT') {
        // Send data back to Dashboard!
        // We construct the return URL with params
        // 'http://.../?scout_done=1&...'

        const params = new URLSearchParams(msg.data);
        params.append('scout_done', '1');

        // Force Dashboard to navigate to result
        const returnUrl = `${SERVER_URL}?${params.toString()}`;

        // Reset Scout
        setScoutUrl(null);

        // Navigate Dashboard
        // We inject JS to force location change
        dashboardRef.current.injectJavaScript(`
          window.location.href = "${returnUrl}";
        `);
      }

      if (msg.type === 'LOG') {
        console.log("[MobileScout]", msg.msg);
      }
    } catch (e) { }
  };

  // 5. Intercepting Streamlit Navigation for Triggers
  const handleDashboardNavState = (navState) => {
    // If Streamlit tries to open a Naver Map link, intercept it!
    const url = navState.url;
    if (url.includes("map.naver.com") || url.includes("place.naver.com")) {
      // STOP! Don't load it in Dashboard. Load it in Scout.
      // React Native WebView has 'onShouldStartLoadWithRequest' for this.
    }
  };

  const shouldStartLoadWithRequest = (request) => {
    const url = request.url;
    // If user clicks "스캔하기" link in Streamlit (which points to Naver Map)
    if (url.includes("map.naver.com") || url.includes("place.naver.com")) {
      setScoutUrl(url); // Load in hidden view
      return false;     // Block in main view
    }
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

      {/* HIDDEN SCOUT (Background Worker) */}
      {scoutUrl && (
        <View style={{ height: 1, width: 1, opacity: 0, position: 'absolute' }}>
          <WebView
            ref={scoutRef}
            source={{ uri: scoutUrl }}
            injectedJavaScript={INJECTED_SCRIPT}
            onMessage={onScoutMessage}
            incognito={true} // Clean session
          />
        </View>
      )}
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
});
