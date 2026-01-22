import streamlit as st
import time
import os
import requests
import sqlite3
import streamlit.components.v1 as components
from datetime import datetime

# Custom Modules
from constants import STYLES, MAIN_CATEGORIES, SUBCATS_FOOD_CAFE, PLACE_REQUIRED_FIELDS
from utils import naver_button, get_missing_fields, days_since, now_iso
from database import (
    DB_PATH, init_db, fix_database_schema, set_app_state, get_app_state,
    get_user_stores, get_store_info, get_checklist, refresh_checklist_from_store,
    add_store, update_store, get_store, update_checklist_flags, set_review_sync_pending, set_review_sync_result,
    set_price_sync_result, mark_price_sync_fail, save_history, mark_task_done
)
from auth import verify_user, create_user, username_exists, seed_admin
from services import calc_az_progress
from views import (
    render_place, render_review, render_blog, render_insta, render_event, render_order
)

# =========================
# 0) Config & Env
# =========================
st.set_page_config(layout="wide", page_title="OWNERS - 사장님 비서", page_icon="🏢")
st.markdown(STYLES, unsafe_allow_html=True)

DEV_MODE = os.environ.get("DEV_MODE", "0") == "1"
AUTO_LOGIN = os.environ.get("AUTO_LOGIN", "1") == "1"
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")
# OPENAI_API_KEY handled in views.py / services.py

# =========================
# 1) Session & Route Control
# =========================
if "page" not in st.session_state: st.session_state.page = "LANDING"
if "auth" not in st.session_state: st.session_state.auth = False
if "username" not in st.session_state: st.session_state.username = None
if "store_id" not in st.session_state: st.session_state.store_id = None
if "order_menu_selection" not in st.session_state: st.session_state.order_menu_selection = "⚡ 통합 발주하기"

# URL에 'price_done'이나 'price_cancel' 신호가 있으면 무조건 페이지를 ORDER로 고정
if st.query_params.get("price_done") == "1" or st.query_params.get("price_cancel") == "1":
    st.session_state.page = "ORDER"
    st.session_state["order_menu_selection"] = "🌐 온라인 링크"

# Caches
if "p_keywords" not in st.session_state: st.session_state.p_keywords = ""
if "p_desc" not in st.session_state: st.session_state.p_desc = ""
if "p_way" not in st.session_state: st.session_state.p_way = ""
if "p_parking" not in st.session_state: st.session_state.p_parking = ""
if "place_qa_res" not in st.session_state: st.session_state.place_qa_res = ""
if "res_rev" not in st.session_state: st.session_state.res_rev = ""
if "res_blo" not in st.session_state: st.session_state.res_blo = ""
if "res_ins" not in st.session_state: st.session_state.res_ins = ""
if "res_evt" not in st.session_state: st.session_state.res_evt = ""

def go_to(page):
    st.session_state.page = page
    st.rerun()

def _qp_get(key: str, default: str = "") -> str:
    try:
        v = st.query_params.get(key)
        return str(v) if v is not None else default
    except:
        return default

def handle_price_qp_global():
    qp = st.query_params
    # 1) 가격 스캔 완료 신호
    if _qp_get("price_done") == "1":
        try:
            item_id = int(_qp_get("item_id") or _qp_get("id") or "0")
            nonce = _qp_get("nonce")
            status = (_qp_get("status") or "OK").upper().strip()
            price = _qp_get("price")
            title = _qp_get("title")
            url = _qp_get("url")

            if status == "OK":
                ok = set_price_sync_result(item_id, nonce, price, title, url)
            else:
                mark_price_sync_fail(item_id)
                ok = False
            pass 

        except Exception as e:
            st.toast(f"❌ 가격 스캔 처리 오류: {e}", icon="🚨")

def handle_review_sync_qp_global():
    # 2) 리뷰 동기화 완료 신호
    if _qp_get("sync_done") == "1":
        try:
            store_id = int(_qp_get("store_id") or "0")
            nonce = _qp_get("nonce")
            status = (_qp_get("status") or "OK").upper().strip()
            unreplied = int(_qp_get("unreplied") or "-1")
            
            # DB Update
            # (See database.py -> set_review_sync_result updates 'review_sync_status', 'review_unreplied_count', 'review_sync_at')
            ok = set_review_sync_result(store_id, nonce, status, unreplied)
            
            if ok:
                st.toast(f"✅ 동기화 완료! 미답변 리뷰 {unreplied}건이 반영되었습니다.", icon="🎉")
                # Clean URL logic is tricky in Streamlit, maybe just leave it or use st.query_params.clear() later
            else:
                st.toast("⚠️ 동기화 검증 실패 (보안 토큰 불일치)", icon="🔒")
                
        except Exception as e:
            st.toast(f"❌ 동기화 처리 오류: {e}", icon="🚨")

def handle_scout_qp_global():
    # 3) 플레이스 정보 스캔 완료 신호
    if _qp_get("scout_done") == "1":
        try:
            store_id = int(_qp_get("store_id") or "0")
            # nonce check can be added if needed
            
            # Parse flags (1 or 0)
            has_desc = int(_qp_get("has_desc") or "0")
            has_menu = int(_qp_get("has_menu") or "0")
            has_keywords = int(_qp_get("has_keywords") or "0")
            has_parking = int(_qp_get("has_parking") or "0")
            has_way = int(_qp_get("has_way") or "0")
            
            # Update DB (checklist)
            update_checklist_flags(store_id, 
                has_place_desc=has_desc,
                has_keywords=has_keywords,
                has_parking_guide=has_parking,
                has_way_guide=has_way,
            )
            
            # Detailed Feedback Toast
            msg_found = []
            msg_missing = []
            
            if has_desc: msg_found.append("설명")
            else: msg_missing.append("설명")
            
            if has_keywords: msg_found.append("키워드")
            else: msg_missing.append("키워드")
            
            if has_parking: msg_found.append("주차")
            else: msg_missing.append("주차")
             
            if has_way: msg_found.append("길찾기")
            else: msg_missing.append("길찾기")
            
            summary = ""
            if msg_found: summary += f"✅ 발견: {', '.join(msg_found)}  \n"
            if msg_missing: summary += f"❌ 누락: {', '.join(msg_missing)}"
            
            st.toast(f"🔎 스캔 완료!\n{summary}", icon="🤖")
            
            # Clear params and refresh UI to show new data
            time.sleep(2.0)
            st.query_params.clear()
            st.rerun()
            
        except Exception as e:
            st.toast(f"❌ 스캔 처리 오류: {e}", icon="🚨")

    # 4) 스캔 결과 모달 (Removed)
    # Check if we just finished a scout task
    if _qp_get("scout_done") == "1":
        st.toast("✅ 매장 정보 스캔 완료! 결과가 반영되었습니다.", icon="🔎")
        # Clear params to prevent toast loop? 
        # Actually usually we leave them or clear them. 
        # Streamlit query params persistence is tricky. 
        # But user wants no popup, so just toast is fine.

# Run Global Handlers
handle_price_qp_global()
handle_review_sync_qp_global()
handle_scout_qp_global()

# =========================
# 2) Dev/Auto Login Logic
# =========================
if DEV_MODE:
    st.session_state.auth = True
    st.session_state.username = "admin"
    if st.session_state.store_id is None:
        _stores = get_user_stores("admin")
        if _stores:
            st.session_state.store_id = _stores[0]["store_id"]
    if st.session_state.page in {"LANDING", "LOGIN", "SIGNUP"}:
        st.session_state.page = "DASHBOARD"
        st.rerun()

if (not DEV_MODE) and AUTO_LOGIN and (not st.session_state.auth):
    last_user = get_app_state("last_login_user")
    if last_user and username_exists(last_user):
        st.session_state.auth = True
        st.session_state.username = last_user
        
        # [AUTO-SELECT STORE]
        _stores = get_user_stores(last_user)
        if _stores:
            st.session_state.store_id = _stores[0]["store_id"]
        else:
            st.session_state.store_id = None
            
        st.session_state.page = "DASHBOARD"
        st.rerun()

PROTECTED_PAGES = {
    "DASHBOARD", "REVIEW", "BLOG", "PLACE", "INSTA", "EVENT", "STORE_ADD",
    "STORE_EDIT", "HISTORY", "TEMPLATES", "ORDER"
}
if st.session_state.page in PROTECTED_PAGES:
    if not st.session_state.auth or not st.session_state.username:
        st.session_state.page = "LOGIN"
        st.rerun()

# =========================
# 3) Public Pages
# =========================
if st.session_state.page == "LANDING":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown(
            "<h1 style='text-align: center; font-size: 4rem; color: #FFD700;'>OWNERS</h1>",
            unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align: center; color: #888;'>오프라인 비즈니스 통합 솔루션</p>",
            unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("로그인", type="primary", use_container_width=True):
                go_to("LOGIN")
        with c2:
            if st.button("회원가입", type="secondary", use_container_width=True):
                go_to("SIGNUP")
elif st.session_state.page == "LOGIN":
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### 로그인")
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("접속", type="primary", use_container_width=True):
                if verify_user(username, password):
                    st.session_state.auth = True
                    st.session_state.username = username
                    st.session_state.store_id = None
                    set_app_state("last_login_user", username)
                    go_to("DASHBOARD")
                else:
                    st.error("계정 확인 필요")

            if st.button("취소", type="secondary", use_container_width=True):
                go_to("LANDING")

elif st.session_state.page == "SIGNUP":
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### 회원가입")
            new_user = st.text_input("아이디")
            new_pw = st.text_input("비밀번호", type="password")
            new_pw2 = st.text_input("비밀번호 확인", type="password")

            if st.button("가입하기", type="primary", use_container_width=True):
                if not new_user.strip():
                    st.error("아이디를 입력해 주세요.")
                elif len(new_pw) < 4:
                    st.error("비밀번호는 4자 이상으로 입력해 주세요.")
                elif new_pw != new_pw2:
                    st.error("비밀번호가 일치하지 않습니다.")
                elif username_exists(new_user.strip()):
                    st.error("이미 존재하는 아이디입니다.")
                else:
                    create_user(new_user.strip(), new_pw)
                    st.session_state.auth = True
                    st.session_state.username = new_user.strip()
                    st.session_state.store_id = None
                    set_app_state("last_login_user", new_user.strip())
                    go_to("STORE_ADD")

            if st.button("메인으로", type="secondary", use_container_width=True):
                go_to("LANDING")

# =========================
# 4) Protected Pages
# =========================
elif st.session_state.page in PROTECTED_PAGES:
    # 0. Global Handler (Scout/Sync) - Process before UI load
    handle_scout_qp_global()

    with st.sidebar:
        st.subheader("OWNERS")
        st.caption(f"계정: {st.session_state.username}")

        stores = get_user_stores(st.session_state.username)
        if not stores:
            st.error("등록된 매장이 없습니다. 먼저 매장을 추가해 주세요.")
            if st.button("➕ 매장 추가", type="primary", use_container_width=True):
                go_to("STORE_ADD")
            # Force stop unless on add page
            if st.session_state.page != "STORE_ADD":
                st.stop()

        if st.session_state.store_id is None and stores:
            st.session_state.store_id = stores[0]["store_id"]

        if stores:
            store_options = {f'{s["store_name"]} (ID:{s["store_id"]})': s["store_id"] for s in stores}
            labels = list(store_options.keys())
            selected_label = labels[0]
            for lb in labels:
                if store_options[lb] == st.session_state.store_id:
                    selected_label = lb
                    break
            new_label = st.selectbox("매장 선택", labels, index=labels.index(selected_label))
            new_store_id = store_options[new_label]
            if new_store_id != st.session_state.store_id:
                st.session_state.store_id = new_store_id
                st.rerun()

        st.markdown("---")
        if st.button("AI 간편 발주", type="secondary", use_container_width=True):
            go_to("ORDER")
        st.markdown("---")
        if st.button("➕ 매장 추가", type="secondary", use_container_width=True):
            go_to("STORE_ADD")
        if st.button("✏️ 매장 정보 수정", type="secondary", use_container_width=True):
            go_to("STORE_EDIT")
        st.markdown("---")
        if st.button("홈 (대시보드)", type="secondary", use_container_width=True):
            go_to("DASHBOARD")
        if st.button("리뷰 관리", type="secondary", use_container_width=True):
            go_to("REVIEW")
        if st.button("마케팅 공고", type="secondary", use_container_width=True):
            go_to("BLOG")
        if st.button("플레이스 관리", type="secondary", use_container_width=True):
            go_to("PLACE")
        if st.button("인스타그램", type="secondary", use_container_width=True):
            go_to("INSTA")
        if st.button("이벤트 기획", type="secondary", use_container_width=True):
            go_to("EVENT")
        st.markdown("---")
        if st.button("로그아웃", type="secondary", use_container_width=True):
            st.session_state.auth = False
            st.session_state.username = None
            st.session_state.store_id = None
            go_to("LANDING")

    # Load Store Data
    if st.session_state.store_id:
        data = get_store_info(st.session_state.username, st.session_state.store_id)
        if not data:
            if st.session_state.page != "STORE_ADD":
                st.error("선택된 매장 정보를 불러오지 못했습니다.")
                st.stop()
        else:
            refresh_checklist_from_store(st.session_state.username, st.session_state.store_id)
            ck = get_checklist(st.session_state.store_id)
            u_name = data["store_name"]
            u_addr = data["address"]
            u_target = data["target"]
            u_sig = data["signature"]
            u_str = data["strengths"]
            u_cat = data["category"]
            u_sub = (data["sub_category"] or "").strip()
            u_review_url = data["review_url"]
            u_insta_url = data["insta_url"]
            u_keywords = data["keywords"]
            cat_label = u_cat + (f" · {u_sub}" if u_sub else "")

    # 4-1) STORE ADD
    if st.session_state.page == "STORE_ADD":
        st.subheader("➕ 매장 추가")
        with st.container(border=True):
            store_name = st.text_input("상호")
            category = st.selectbox("업종(1차)", MAIN_CATEGORIES, index=0)

            sub_category = ""
            if category == "음식점/카페":
                sub_sel = st.selectbox("세부 업종(2차, 선택)", SUBCATS_FOOD_CAFE, index=0)
                if sub_sel == "기타(직접입력)":
                    sub_category = st.text_input("세부 업종 직접 입력", placeholder="예: 분식/김밥, 베이커리 등")
                else:
                    sub_category = sub_sel

            address = st.text_input("주소")
            target = st.text_input("타겟 고객")
            signature = st.text_input("대표 메뉴/서비스")
            strengths = st.text_area("강점", height=90)
            keywords = st.text_input("키워드(선택)")
            review_url = st.text_input("네이버 플레이스 URL (권장)", placeholder="예: https://map.naver.com/p/entry/place/...")
            insta_url = st.text_input("인스타그램 URL(선택)")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("추가", type="primary", use_container_width=True):
                    if not store_name.strip(): st.error("상호를 입력해 주세요.")
                    elif not address.strip(): st.error("주소를 입력해 주세요.")
                    else:
                        sid = add_store(st.session_state.username, store_name.strip(), category, (sub_category or "").strip(),
                                        address.strip(), target.strip(), signature.strip(), strengths.strip(),
                                        keywords.strip(), review_url.strip(), insta_url.strip())
                        st.session_state.store_id = sid
                        go_to("DASHBOARD")
            with c2:
                if st.button("취소", type="secondary", use_container_width=True):
                    go_to("DASHBOARD")

    # 4-2) STORE EDIT
    elif st.session_state.page == "STORE_EDIT":
        st.subheader("✏️ 매장 정보 수정")
        with st.container(border=True):
            store_name = st.text_input("상호", value=u_name)
            cat_index = MAIN_CATEGORIES.index(u_cat) if u_cat in MAIN_CATEGORIES else 0
            category = st.selectbox("업종(1차)", MAIN_CATEGORIES, index=cat_index)

            sub_category = u_sub
            if category == "음식점/카페":
                if u_sub and u_sub in SUBCATS_FOOD_CAFE:
                    sub_index = SUBCATS_FOOD_CAFE.index(u_sub)
                    sub_sel = st.selectbox("세부 업종(2차)", SUBCATS_FOOD_CAFE, index=sub_index)
                else:
                    sub_sel = st.selectbox("세부 업종(2차)", SUBCATS_FOOD_CAFE, index=0)
                
                if sub_sel == "기타(직접입력)":
                    sub_category = st.text_input("세부 업종 직접 입력", value=(u_sub if u_sub and u_sub not in SUBCATS_FOOD_CAFE else ""))
                else:
                    sub_category = sub_sel
            else:
                sub_category = ""

            address = st.text_input("주소", value=u_addr)
            target = st.text_input("타겟 고객", value=u_target)
            signature = st.text_input("대표 메뉴/서비스", value=u_sig)
            strengths = st.text_area("강점", value=u_str, height=90)
            keywords = st.text_input("키워드(선택)", value=(u_keywords or ""))
            review_url = st.text_input("네이버 플레이스 URL (권장)", value=(u_review_url or ""))
            insta_url = st.text_input("인스타그램 URL(선택)", value=(u_insta_url or ""))

            c1, c2 = st.columns(2)
            with c1:
                if st.button("저장", type="primary", use_container_width=True):
                    ok = update_store(st.session_state.username, st.session_state.store_id, store_name.strip(), category,
                                      (sub_category or "").strip(), address.strip(), target.strip(), signature.strip(),
                                      strengths.strip(), keywords.strip(), review_url.strip(), insta_url.strip())
                    if ok:
                        st.success("저장 완료")
                        go_to("DASHBOARD")
                    else: st.error("저장 실패")
            with c2:
                if st.button("취소", type="secondary", use_container_width=True):
                    go_to("DASHBOARD")

    # 4-3) DASHBOARD
    elif st.session_state.page == "DASHBOARD":
        if st.query_params.get("sync_cancel") == "1":
            update_checklist_flags(st.session_state.store_id, review_sync_status="FAIL")
            st.toast("동기화를 취소했습니다.", icon="🛑")
            st.query_params.clear()
            time.sleep(0.5)
            st.rerun()

        # 진단 결과 계산 (Services)
        az_res = calc_az_progress(data, ck)
        prog = az_res['progress']
        done = az_res['done']
        total = az_res['total']
        items = az_res['items']
        
        # --- HEADER ---
        st.markdown(f"## 👋 안녕하세요, {u_name} 사장님!")
        st.markdown(f"<div style='color:var(--secondary); margin-top:-10px; margin-bottom:20px;'>오늘도 매장 성장을 위해 달려볼까요?</div>", unsafe_allow_html=True)

        # --- STAT CARDS ---
        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown(f"""
            <div class="app-card">
                <div class="card-header">📊 내 매장 진단 점수</div>
                <div style="font-size: 2rem; font-weight: 800; color: var(--primary);">{prog}<span style="font-size:1rem; color:var(--text-sub);">점</span></div>
                <div style="font-size: 0.875rem; color: var(--secondary);">업종 평균 대비 상위 10%</div>
            </div>
            """, unsafe_allow_html=True)
        with sc2:
            st.markdown(f"""
            <div class="app-card">
                <div class="card-header">✅ 완료한 항목</div>
                <div style="font-size: 2rem; font-weight: 800; color: var(--text-main);">{done} <span style="font-size:1rem; color:var(--text-sub);">/ {total}</span></div>
                <div style="font-size: 0.875rem; color: var(--secondary);">달성률 {prog}%</div>
            </div>
            """, unsafe_allow_html=True)

        # --- PENDING TODOS (Rule-Based 7 items) ---
        st.markdown("### 🔥 미완료 항목")
        
        pending_items = []

        # 1. Owners Info
        missing_fields = get_missing_fields(data, PLACE_REQUIRED_FIELDS)
        if missing_fields:
            pending_items.append({
                "label": f"매장 필수 정보 입력 ({', '.join(missing_fields[:2])} 등)",
                "btn": "입력하기",
                "target": "STORE_EDIT",
                "type": "GO"
            })

         # 2. Place Setting (+ Scout Button)
        if not (ck.get("has_keywords") and ck.get("has_place_desc") and ck.get("has_way_guide") and ck.get("has_parking_guide")):
             
             # Identify missing fields for label
             missing_list = []
             if not ck.get("has_place_desc"): missing_list.append("설명")
             if not ck.get("has_keywords"): missing_list.append("보유키워드")
             if not ck.get("has_parking_guide"): missing_list.append("주차")
             if not ck.get("has_way_guide"): missing_list.append("오시는길")
             missing_str = ", ".join(missing_list)
             
             if missing_list:
                 label_text = f"플레이스 정보가 부족합니다 (<span style='color: #E53E3E; font-weight: 800;'>누락: {missing_str}</span>)"
             else:
                 label_text = "플레이스 정보를 스캔해주세요"
             
             # [VALIDATION] Check if URL exists
             if not u_review_url or "naver.com" not in u_review_url:
                  pending_items.append({
                     "label": "스캔을 위해 '매장 URL' 입력이 필요합니다.",
                     "btn": "URL 입력하러 가기",
                     "target": "STORE_EDIT",
                     "type": "GO" 
                  })
             else:
                 # [OPTIMIZATION] Construct CLEAN Mobile URL
                 # Extract Place ID from: .../place/123456...
                 scout_target = ""
                 try:
                     if "/place/" in u_review_url:
                         # Split by /place/ and take the next part, then split by ? or /
                         p_part = u_review_url.split("/place/")[1]
                         place_id = p_part.split("?")[0].split("/")[0]
                         # FORCE MOBILE HOME URL (Lightweight, reliable)
                         scout_target = f"https://m.place.naver.com/place/{place_id}/home"
                     else:
                         # Fallback if ID parsing fails
                         scout_target = u_review_url
                 except:
                     scout_target = u_review_url

                 # Add Params
                 nonce = set_review_sync_pending(st.session_state.store_id)
                 return_base = "https://owners-twrcya3hrhhktgutcwsmtc.streamlit.app"
                 scout_target += f"{'&' if '?' in scout_target else '?'}owners_nonce={nonce}&owners_store_id={st.session_state.store_id}&owners_return_url={return_base}&owners_mode=SCOUT"

                 pending_items.append({
                     "label": label_text,
                     "btn": "내 플레이스 정보 불러오기",
                     "target": scout_target,
                     "type": "LINK_SCOUT",
                     "sub_btn": "정보 수정하기 (네이버)",
                     "sub_target": "https://new.smartplace.naver.com/" 
                 })

        # 3. Review Reply (Sync Check)
        # If SyncStatus is not OK or Unreplied > 0
        sync_status = (ck.get("review_sync_status") or "").upper()
        unreplied = ck.get("review_unreplied_count") or 0
        if sync_status != "OK" or unreplied > 0:
            # Sync Button Action Logic embedded here
            # Construct Link
            nonce = set_review_sync_pending(st.session_state.store_id)
            base_url = u_review_url or "https://smartplace.naver.com/"
            if "hasReply=false" not in base_url:
                base_url += "&hasReply=false" if "?" in base_url else "?hasReply=false"
            return_base = "http://localhost:8501"
            target_link = f"{base_url}&owners_nonce={nonce}&owners_store_id={st.session_state.store_id}&owners_return_url={return_base}&owners_mode=REVIEW"
            
            pending_items.append({
                "label": f"미완료 리뷰 답글이 {unreplied}개 있습니다 (또는 동기화 필요)",
                "btn": "동기화 & 답글달기",
                "target": target_link,
                "type": "LINK_SYNC" # Custom Type
            })

        # 4. Ad Analysis (15 days)
        last_ad = ck.get("last_ad_analysis_at")
        if days_since(last_ad) >= 15:
            pending_items.append({
                "label": "네이버 광고 키워드 분석 및 단가 관리 (15일 주기)",
                "btn": "점검 완료",
                "key_suffix": "ad_analysis",
                "task_col": "last_ad_analysis_at",
                "type": "ACTION_DONE"
            })

        # 5. Insta Post (3 days)
        last_insta = ck.get("last_insta_caption_at")
        if days_since(last_insta) >= 3:
             pending_items.append({
                 "label": "인스타그램 새로운 게시글 업로드 (3일 주기)",
                 "btn": "콘텐츠 생성",
                 "target": "INSTA",
                 "type": "GO"
             })

        # 6. Blog Post (15 days)
        last_blog = ck.get("last_blog_post_at")
        if days_since(last_blog) >= 15:
             pending_items.append({
                 "label": "네이버 블로그 새로운 글 작성 (15일 주기)",
                 "btn": "초안 작성",
                 "target": "BLOG",
                 "type": "GO"
             })

        # 7. Place News (3 days)
        last_news = ck.get("last_place_news_at")
        if days_since(last_news) >= 3:
            pending_items.append({
                "label": "네이버 플레이스 '새소식/공지' 등록 (3일 주기)",
                "btn": "등록 완료",
                "key_suffix": "place_news",
                "task_col": "last_place_news_at",
                "type": "ACTION_DONE"
            })


        if not pending_items:
             st.success("👏 모든 필수 항목을 완료했습니다! 매장이 완벽하게 준비되었습니다.")
        else:
            for idx, item in enumerate(pending_items):
                with st.container():
                    c_txt, c_btn = st.columns([4, 1.2])
                    with c_txt:
                        st.markdown(f"""
                        <div style="
                            padding: 16px; 
                            background: #F8FAFC; 
                            border-radius: 8px; 
                            border-left: 5px solid var(--primary);
                            display:flex; align-items:center; 
                            color: #333;
                            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                        ">
                            <span style="color: #333; font-weight: 600; font-size: 15px;">{item['label']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    with c_btn:
                        # RENDER BUTTON based on TYPE
                        if item["type"] == "GO":
                             if st.button(f"{item['btn']}", key=f"btn_go_{idx}", type="primary", use_container_width=True):
                                 go_to(item['target'])
                                 
                        elif item["type"] == "ACTION_DONE":
                             if st.button(f"{item['btn']}", key=f"btn_act_{item['key_suffix']}", type="primary", use_container_width=True):
                                 mark_task_done(st.session_state.store_id, item['task_col'])
                                 st.toast("✅ 작업 완료 확인!", icon="📅")
                                 time.sleep(0.5)
                                 st.rerun()
                                 
                        elif item["type"] == "LINK_SYNC":
                            # Render Link Button with N Style
                            st.markdown(f"""
                            <a href="{item['target']}" target="_self" style="text-decoration:none;">
                                <div style="
                                    background-color: #03C75A; color: white; border-radius: 6px; 
                                    padding: 10px 0; text-align: center; font-weight: bold; font-size: 14px;
                                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); display:block;
                                    margin-top: 2px;
                                ">
                                    {item['btn']}
                                </div>
                            </a>
                            """, unsafe_allow_html=True)
                            
                        elif item["type"] == "LINK_SCOUT":
                            # Render Scout Button with Purple Style
                            st.markdown(f"""
                            <a href="{item['target']}" target="_self" style="text-decoration:none;">
                                <div style="
                                    background: linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%); 
                                    color: white; border-radius: 6px; 
                                    padding: 10px 0; text-align: center; font-weight: bold; font-size: 14px;
                                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); display:block;
                                    margin-top: 2px;
                                ">
                                    {item['btn']}
                                </div>
                            </a>
                            """, unsafe_allow_html=True)
                            
                            # Secondary 'Edit' Button
                            if "sub_btn" in item:
                                 st.markdown(f"""
                                <a href="{item['sub_target']}" target="_blank" style="text-decoration:none;">
                                    <div style="
                                        background-color: #F1F5F9; 
                                        color: #64748B; border: 1px solid #CBD5E1;
                                        border-radius: 6px; 
                                        padding: 8px 0; text-align: center; font-weight: 600; font-size: 13px;
                                        display:block; margin-top: 6px;
                                    ">
                                        {item['sub_btn']} ➜
                                    </div>
                                </a>
                                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        # --- SYNC BUTTON (ALWAYS VISIBLE) ---
        _, center_col, _ = st.columns([0.2, 0.6, 0.2])
        with center_col:
            # 1. Nonce 생성 및 DB 저장 (매번 생성해도 됨)
            nonce = set_review_sync_pending(st.session_state.store_id)
            
            # 2. URL 파라미터 구성
            base_url = u_review_url or "https://smartplace.naver.com/"
            if "hasReply=false" not in base_url:
                base_url += "&hasReply=false" if "?" in base_url else "?hasReply=false"
            
            return_base = "http://localhost:8501"
            
            target_link = f"{base_url}&owners_nonce={nonce}&owners_store_id={st.session_state.store_id}&owners_return_url={return_base}"
            
            st.markdown(f"""
                <a href="{target_link}" target="_self" style="text-decoration:none;">
                    <div style="
                        background-color: #03C75A; 
                        color: white; 
                        border-radius: 8px; 
                        padding: 12px; 
                        text-align: center; 
                        font-weight: bold; 
                        font-size: 16px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        transition: all 0.2s;
                    ">
                        N 네이버 리뷰 동기화 시작 ➜
                    </div>
                </a>
            """, unsafe_allow_html=True)



    # 4-4) Feature Pages (Using Views)
    else:
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("이전", type="secondary"): go_to("DASHBOARD")
        st.markdown("---")

        left_info, right_work = st.columns([1, 2])
        with left_info:
             st.markdown(f"""
            <div class="guide-box" style="border-left:none; border-top: 4px solid #FFD700;">
                <div style="color:#fff; font-size:16px; font-weight:700; margin-bottom:15px;">상호 : {u_name}</div>
                <div style="color:#888; font-size:13px; margin-bottom:2px;">업종</div>
                <div style="color:#ddd; margin-bottom:10px;">{cat_label}</div>
                <div style="color:#888; font-size:13px; margin-bottom:2px;">주소</div>
                <div style="color:#ddd; margin-bottom:10px;">{u_addr}</div>
            </div>
            """, unsafe_allow_html=True)

        with right_work:
            if st.session_state.page == "PLACE":
                render_place(u_name, u_addr, cat_label, u_sig, u_str, u_target)
            elif st.session_state.page == "REVIEW":
                render_review(u_name, cat_label, u_sig, u_review_url)
            elif st.session_state.page == "BLOG":
                render_blog(u_name, cat_label, "") # u_ben? Input inside
            elif st.session_state.page == "INSTA":
                render_insta(u_name, cat_label, u_sig, u_addr, u_insta_url)
            elif st.session_state.page == "EVENT":
                render_event(u_name, cat_label, u_addr, u_sig, u_str, u_target)
            elif st.session_state.page == "ORDER":
                render_order()

init_db()
seed_admin()
fix_database_schema()