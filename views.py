import streamlit as st
import time
import os
import urllib.parse
import json
import pandas as pd
import re
from openai import OpenAI

from constants import CATEGORY_PROFILES
from database import (
    save_history, update_checklist_flags, save_todo_event, now_iso,
    get_suppliers, get_online_items, get_store, add_supplier, update_supplier, delete_supplier,
    delete_online_item, add_online_item, set_price_sync_pending, set_price_sync_result, mark_price_sync_fail,
    ensure_online_items_price_columns, DB_PATH
)
from utils import get_naver_coordinates, naver_button, insta_button
import sqlite3

# OpenAI Client Setup
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

def render_place(u_name, u_addr, cat_label, u_sig, u_str, u_target):
    st.subheader("네이버 플레이스 셋팅")

    with st.expander("STEP 1. 관리자 페이지 접속", expanded=True):
        naver_button("네이버 스마트플레이스 열기 ➜", "https://new.smartplace.naver.com")

    with st.expander("STEP 2. 상세 정보 생성", expanded=True):
        st.markdown("#### 1. 대표 키워드 생성(5개)")
        if st.button("키워드 추출", type="primary", use_container_width=True, key="place_kw_btn"):
            if not client:
                st.error("OpenAI API Key가 필요합니다.")
                return
            with st.spinner("분석 중..."):
                prompt = f"매장:{u_name}, 지역:{u_addr}, 업종:{cat_label}, 메뉴:{u_sig}. 네이버 플레이스용 SEO 키워드 5개 추천 (형식: #키워드1 #키워드2...)"
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                st.session_state.p_keywords = res.choices[0].message.content
                save_history(st.session_state.username, st.session_state.store_id, "PLACE", "플레이스 키워드", f"{u_name} / {cat_label} / {u_addr} / {u_sig}", st.session_state.p_keywords)
                update_checklist_flags(st.session_state.store_id, has_keywords=1)

        if st.session_state.get("p_keywords"):
            st.text_area("결과", value=st.session_state.p_keywords, height=80, key="place_kw_out")

        st.markdown("---")
        st.markdown("#### 2. 상세 설명 생성")
        in_phone = st.text_input("대표 번호", placeholder="02-xxxx-xxxx", key="place_phone")
        in_time = st.text_input("영업 시간", placeholder="매일 10:00 - 22:00", key="place_time")
        if st.button("상세 설명 생성", type="primary", use_container_width=True, key="place_desc_btn"):
            if not client:
                st.error("OpenAI API Key가 필요합니다.")
                return
            with st.spinner("작성 중..."):
                prompt = f"""
                매장:{u_name}, 업종:{cat_label}, 주소:{u_addr}, 전화:{in_phone}, 시간:{in_time},
                특징:{u_str}, 메뉴:{u_sig}, 타겟:{u_target}. 네이버 플레이스 상세설명. 신뢰감 있고 전문적인 톤으로 작성.
                """
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                st.session_state.p_desc = res.choices[0].message.content
                save_history(st.session_state.username, st.session_state.store_id, "PLACE", "플레이스 상세설명", f"전화:{in_phone} / 시간:{in_time}", st.session_state.p_desc)
                update_checklist_flags(st.session_state.store_id, has_place_desc=1)

        if st.session_state.get("p_desc"):
            st.text_area("결과", value=st.session_state.p_desc, height=250, key="place_desc_out")

        st.markdown("---")
        st.markdown("#### 3. 찾아오시는 길 생성")
        in_addr = st.text_input("매장 주소", value=u_addr, key="place_addr")
        if st.button("길 안내 문구 생성", type="primary", use_container_width=True, key="place_way_btn"):
            if not client:
                st.error("OpenAI API Key가 필요합니다.")
                return
            with st.spinner("경로 분석 중..."):
                # Notice: client_id/secret for Naver map is not passed here. 
                # Assuming render_place is called where NAVER envs are available or handle it inside utils.
                # get_naver_coordinates needs keys. They are in main.py ENV vars. 
                # I should import them from main or pass them? main.py has them.
                # Better: get them from os.environ here.
                nid = os.environ.get("NAVER_CLIENT_ID")
                nsecret = os.environ.get("NAVER_CLIENT_SECRET")
                
                lng, lat, _ = get_naver_coordinates(in_addr, nid, nsecret)
                tone_prompt = """
                [작성 지침]
                1. 감정적인 표현(친절한, 맛있는 등)을 배제할 것.
                2. 내비게이션처럼 정확한 미터(m)와 방향(좌회전/우회전) 위주로 서술할 것.
                3. 랜드마크(편의점, 은행 등)를 기준으로 설명할 것.
                4. 예시: '사당역 10번 출구에서 150m 직진 후 스타벅스 골목으로 진입. 1층에 위치.'
                """
                if lng and lat:
                    prompt = f"매장:{u_name}, 업종:{cat_label}, 주소:{u_addr}, 좌표:({lat},{lng}). {tone_prompt}"
                else:
                    prompt = f"매장:{u_name}, 업종:{cat_label}, 주소:{u_addr}. {tone_prompt}"
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                st.session_state.p_way = res.choices[0].message.content
                save_history(st.session_state.username, st.session_state.store_id, "PLACE", "찾아오시는 길", in_addr, st.session_state.p_way)
                update_checklist_flags(st.session_state.store_id, has_way_guide=1)

        if st.session_state.get("p_way"):
            st.text_area("결과", value=st.session_state.p_way, height=120, key="place_way_out")

        st.markdown("---")
        st.markdown("#### 4. 주차 안내")
        pk_opt = st.radio("주차 여부", ["가능", "불가"], label_visibility="collapsed", key="place_pk_opt")
        pk_detail = ""
        if pk_opt == "가능":
            pk_detail = st.text_input("주차장 상세 위치", placeholder="예: 건물 뒤 3대 가능", key="place_pk_detail")
        if st.button("주차 안내 문구 생성", type="primary", use_container_width=True, key="place_pk_btn"):
            if not client:
                st.error("OpenAI API Key가 필요합니다.")
                return
            with st.spinner("분석 중..."):
                prompt = f"매장:{u_name}, 업종:{cat_label}, 주소:{u_addr}. 주차상태:{pk_opt}, 상세:{pk_detail}. 주차 안내 문구. 간결하고 명확하게."
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                st.session_state.p_parking = res.choices[0].message.content
                save_history(st.session_state.username, st.session_state.store_id, "PLACE", "주차 안내", f"{pk_opt} / {pk_detail}", st.session_state.p_parking)
                update_checklist_flags(st.session_state.store_id, has_parking_guide=1)

        if st.session_state.get("p_parking"):
            st.text_area("결과", value=st.session_state.p_parking, height=80, key="place_pk_out")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("💬 AI 답변")
    st.caption("궁금한 점을 물어보시면 AI가 답변해 드립니다.")

    with st.container(border=True):
        q_input = st.text_input("질문 입력", placeholder="예: 플레이스 순위 올리는 법", key="place_qa_in")
        if st.button("질문하기", type="primary", use_container_width=True, key="place_qa_btn"):
            if q_input.strip():
                if not client:
                    st.error("OpenAI API Key가 필요합니다.")
                    return
                with st.spinner("답변 작성 중..."):
                    prompt = f"네이버 스마트플레이스 전문가로서 답변: {q_input}. 매장:{u_name}. 전문적이고 간결하게."
                    res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.session_state.place_qa_res = res.choices[0].message.content
                    save_history(st.session_state.username, st.session_state.store_id, "QA", "플레이스 Q&A", q_input, st.session_state.place_qa_res)
                    update_checklist_flags(st.session_state.store_id, last_place_qa_at=now_iso())
            else:
                st.error("질문을 입력해 주세요.")

        if st.session_state.get("place_qa_res"):
            st.markdown(f"""
            <div class='qa-box'>
                <div class='header'>💡 AI 답변</div>
                <div>{st.session_state.place_qa_res}</div>
            </div>
            """, unsafe_allow_html=True)

def render_review(u_name, cat_label, u_sig, u_review_url):
    st.subheader("💬 네이버 리뷰 답글 생성기")
    st.caption("고객의 리뷰를 분석하여 상황에 딱 맞는 센스 있는 답글을 남겨보세요.")

    if u_review_url and (u_review_url or "").strip():
        with st.expander("네이버 리뷰 페이지 열기", expanded=False):
            st.info("아래 버튼을 눌러 네이버 리뷰를 확인하고, 복사해서 가져오세요.")
            naver_button("네이버 플레이스 리뷰 바로가기 ➜", u_review_url)

    col1, col2 = st.columns([1, 1])

    with col1:
        with st.container(border=True):
            st.markdown("#### ⚙️ 답글 설정")
            tone = st.selectbox("어떤 말투로 쓸까요?", [
                "🥰 친절하고 감성적으로 (이모지 포함)", "👔 정중하고 전문적으로 (신뢰감)",
                "🤣 유쾌하고 위트있게 (동네 형/누나처럼)", "🛡️ 클레임 대응 (차분하고 공감하며)"
            ], index=0)
            length = st.radio("글 길이", ["짧고 간결하게", "보통", "길고 정성스럽게"], index=1, horizontal=True)
            keywords = st.text_input("꼭 넣고 싶은 말 (선택)", placeholder="예: 다음주 신메뉴 출시 / 단체석 완비")

    with col2:
        with st.container(border=True):
            st.markdown("#### 📝 내용 입력")
            u_rev = st.text_area("손님 리뷰 붙여넣기", height=200, placeholder="손님이 남긴 리뷰 내용을 여기에 복사해서 붙여넣으세요.\n(예: 음식은 맛있는데 주차가 좀 불편해요 ㅠㅠ)", key="rev_in")

            if st.button("✨ AI 맞춤 답글 생성", type="primary", use_container_width=True):
                if not u_rev.strip():
                    st.error("리뷰 내용을 입력해 주세요!")
                else:
                    if not client:
                        st.error("OpenAI API Key가 필요합니다.")
                        return
                    with st.spinner("사장님의 마음을 담아 작성 중... ✍️"):
                        prompt = f"""
                        역할: {cat_label} 매장 '{u_name}'의 센스 있는 사장님.
                        상황: 손님 리뷰에 대한 답글 작성.

                        [매장 정보]
                        - 업종: {cat_label}
                        - 대표메뉴: {u_sig}

                        [손님 리뷰]
                        "{u_rev}"

                        [작성 지침]
                        1. 말투: {tone}
                        2. 길이: {length}
                        3. 필수 포함 내용: {keywords if keywords else "없음 (문맥에 맞게 자연스럽게 마무리)"}
                        4. 고객의 리뷰 내용을 구체적으로 언급하여 '복붙' 느낌이 나지 않게 할 것.
                        """
                        try:
                            res = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": prompt}]
                            )
                            out = res.choices[0].message.content
                            st.session_state.res_rev = out
                            save_history(st.session_state.username, st.session_state.store_id, "REVIEW", "리뷰 답글", u_rev, out)
                            update_checklist_flags(st.session_state.store_id, last_review_reply_at=now_iso())
                            save_todo_event(st.session_state.username, st.session_state.store_id, "review", "리뷰 답글 생성", "DONE")
                            st.success("생성 완료!")
                        except Exception as e:
                            st.error(f"오류 발생: {str(e)}")

    if st.session_state.get("res_rev"):
        st.markdown("---")
        st.markdown("#### 💌 생성된 답글")
        st.info("마음에 들면 복사해서 네이버 답글창에 붙여넣으세요!")
        st.code(st.session_state.res_rev, language="text")

def render_blog(u_name, cat_label, u_ben):  # Added u_ben as arg? No main.py logic was: u_ben = st.text_input. So it's inside.
    st.subheader("체험단 모집")
    # Need to handle inputs inside here as in main.py
    u_ben_input = st.text_input("혜택", placeholder="예: 2인 식사 제공 / 디저트 제공 / 시술 1회 제공", key="blog_in")
    if st.button("공고 생성", type="primary", use_container_width=True, key="blog_btn"):
        if not client:
            st.error("OpenAI API Key가 필요합니다.")
            return
        prompt = f"매장:{u_name}, 업종:{cat_label}, 혜택:{u_ben_input}. 블로그 체험단 모집글. 자연스러운 모집 문구 + 참여 조건 + 방문 안내 포함."
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
        out = res.choices[0].message.content
        st.session_state.res_blo = out
        save_history(st.session_state.username, st.session_state.store_id, "BLOG", "체험단 모집", u_ben_input, out)
        update_checklist_flags(st.session_state.store_id, last_blog_post_at=now_iso())

    if st.session_state.get("res_blo"):
        st.text_area("결과", value=st.session_state.res_blo, height=350, key="blog_out")

def render_insta(u_name, cat_label, u_sig, u_addr, u_insta_url):
    st.subheader("인스타그램 관리")
    if u_insta_url and (u_insta_url or "").strip():
        insta_button("내 인스타그램 바로가기 ➜", u_insta_url)
        st.markdown("<br>", unsafe_allow_html=True)

    u_cap = st.text_input("사진 설명", placeholder="예: 오늘 만든 딸기 생크림 케이크 / 점심 특선 / 회식 추천 세트", key="ins_in")
    if st.button("캡션 생성", type="primary", use_container_width=True, key="ins_btn"):
        if not client:
            st.error("OpenAI API Key가 필요합니다.")
            return
        prompt = f"매장:{u_name}, 업종:{cat_label}, 설명:{u_cap}, 메뉴:{u_sig}, 지역:{u_addr}. 인스타 감성 캡션 1개 + 해시태그 12개."
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
        out = res.choices[0].message.content
        st.session_state.res_ins = out
        save_history(st.session_state.username, st.session_state.store_id, "INSTA", "인스타 캡션", u_cap, out)
        update_checklist_flags(st.session_state.store_id, last_insta_caption_at=now_iso(), has_insta_url=1 if (u_insta_url or "").strip() else 0)
        save_todo_event(st.session_state.username, st.session_state.store_id, "insta", "인스타 캡션 생성", "DONE")

    if st.session_state.get("res_ins"):
        st.text_area("결과", value=st.session_state.res_ins, height=300, key="ins_out")

def render_event(u_name, cat_label, u_addr, u_sig, u_str, u_target):
    st.subheader("이벤트 기획")
    u_goal = st.text_input("목표", placeholder="예: 평일 점심 매출 증대 / 신규 고객 유입 / 리뷰 수 증가", key="evt_goal")
    u_theme = st.text_input("주제/키워드", placeholder="예: 런치 할인 / 회식 세트 / 비오는날 이벤트", key="evt_theme")
    u_period = st.text_input("기간", placeholder="예: 이번 주 금~일 / 2월 한달 / 매주 월~목", key="evt_period")

    if st.button("이벤트 기획 생성", type="primary", use_container_width=True, key="evt_btn"):
        if not client:
            st.error("OpenAI API Key가 필요합니다.")
            return
        prompt = f"""
        매장:{u_name}
        업종:{cat_label}
        주소:{u_addr}
        대표메뉴:{u_sig}
        강점:{u_str}
        타겟:{u_target}

        목표:{u_goal}
        주제:{u_theme}
        기간:{u_period}

        오프라인 매장용 이벤트 기획안을 만들어줘.
        포함: (1) 이벤트 한줄 컨셉 (2) 혜택/구성 (3) 참여 방법 (4) 홍보 문구 2개 (5) 주의사항
        톤: 간결하고 실행가능하게.
        """
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
        out = res.choices[0].message.content
        st.session_state.res_evt = out
        save_history(st.session_state.username, st.session_state.store_id, "EVENT", "이벤트 기획", f"{u_goal} / {u_theme} / {u_period}", out)
        update_checklist_flags(st.session_state.store_id, last_event_plan_at=now_iso())
        save_todo_event(st.session_state.username, st.session_state.store_id, "event", "이벤트 기획 생성", "DONE")

    if st.session_state.get("res_evt"):
        st.text_area("결과", value=st.session_state.res_evt, height=350, key="evt_out")

def render_order():
    ensure_online_items_price_columns()

    # -----------------------------------------------------------
    # [1] 가격 스캔 결과 처리
    # -----------------------------------------------------------
    qp = st.query_params

    if qp.get("price_cancel") == "1":
        try:
            item_id = int(qp.get("item_id"))
            mark_price_sync_fail(item_id)
        except: pass
        st.toast("가격 스캔을 취소했습니다.", icon="🛑")
        st.session_state["order_menu_selection"] = "🌐 온라인 링크"
        st.query_params.clear()
        st.rerun()

    if qp.get("price_done") == "1":
        try:
            item_id = int(qp.get("item_id"))
            nonce = qp.get("nonce") or ""
            price = qp.get("price") or ""
            title = qp.get("title") or ""
            url = qp.get("url") or ""
            p_status = qp.get("status", "FAIL")

            if p_status == "OK":
                set_price_sync_result(item_id, nonce, price, title, url)
                if url and url.startswith("http"):
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("UPDATE online_items SET url=? WHERE id=?", (url, item_id))
                    conn.commit()
                    conn.close()
                st.toast(f"✅ 가격({price}원) 및 링크 업데이트 완료!", icon="🔗")
            else:
                mark_price_sync_fail(item_id)
                st.toast("⚠️ 가격을 읽지 못했습니다.", icon="🚫")
        except Exception as e:
            st.error(f"저장 중 오류: {e}")

        st.session_state["order_menu_selection"] = "🌐 온라인 링크"
        st.query_params.clear()
        time.sleep(0.5)
        st.rerun()

    # -----------------------------------------------------------
    # [2] 네비게이션
    # -----------------------------------------------------------
    st.subheader("🛒 AI 간편 발주 (통합)")
    st.caption("문자 발주와 온라인 구매 링크를 한 번에 정리해드립니다.")

    menu_options = ["⚡ 통합 발주하기", "📱 거래처 관리", "🌐 온라인 링크"]
    default_idx = 0

    if "order_menu_selection" in st.session_state:
        target = st.session_state["order_menu_selection"]
        if target in menu_options:
            default_idx = menu_options.index(target)
        del st.session_state["order_menu_selection"]

    selected_tab = st.radio("메뉴 선택", menu_options, index=default_idx, horizontal=True, label_visibility="collapsed")
    st.markdown("---")

    # ==============================================================================
    # TAB 1: 통합 발주
    # ==============================================================================
    if selected_tab == "⚡ 통합 발주하기":
        suppliers = get_suppliers(st.session_state.store_id)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute("SELECT * FROM online_items WHERE store_id = ? ORDER BY is_fixed DESC, alias ASC", (st.session_state.store_id, ))
            links = [dict(row) for row in c.fetchall()]
        except:
            links = get_online_items(st.session_state.store_id)
        conn.close()

        store_info = get_store(st.session_state.store_id)
        my_store_name = store_info['store_name'] if store_info else "사장"

        if not suppliers and not links:
            st.warning("먼저 '거래처 관리'나 '온라인 링크' 탭에서 데이터를 등록해주세요!")
        else:
            st.markdown("""
            <div class="prompt-box">
                <div class="header">💡 이렇게 입력해보세요</div>
                "<b>참이슬 3박스, 연어 2kg</b>, 그리고 쿠팡에서 <b>위생장갑</b> 링크 찾아줘."
            </div>
            """, unsafe_allow_html=True)

            order_text = st.text_area("주문 내용 입력", height=100, placeholder="예: 참이슬 3박스, 연어 5kg...")

            if st.button("AI 주문서 생성 ✨", type="primary", use_container_width=True):
                if not order_text.strip():
                    st.error("주문할 내용을 입력해주세요.")
                else:
                    if not client:
                         st.error("OpenAI API Key가 필요합니다.")
                         return
                    with st.spinner("🤖 데이터를 분석 중입니다..."):
                        try:
                            sup_list_str = "\n".join([
                                f"- [문자거래처] {s['name']} (취급품목: {s['items']}, 전화: {s['phone']})"
                                for s in suppliers
                            ])

                            link_list_str = "\n".join([
                                f"- [온라인링크] {l['alias']} (쇼핑몰: {l['mall_name']}, "
                                f"가격: {(format(int(l.get('last_confirmed_price', 0)), ',') + '원') if l.get('last_confirmed_price') else '가격미확인'}, "
                                f"URL: {l['url']})"
                                for l in links
                            ])

                            prompt = f"""
                            당신은 자재 발주 관리자입니다.
                            [사용자 주문]
                            {order_text}

                            [등록된 거래처 정보]
                            {sup_list_str}

                            [등록된 온라인 링크 정보]
                            {link_list_str}

                            [지시사항 - 융통성 있게 매칭하세요]
                            1. 사용자의 주문 품목을 '등록된 정보'와 대조하여 매칭하세요.
                            2. **[핵심] 완벽하게 똑같지 않아도 됩니다.** 의미가 통하면 매칭하세요.
                                - 예: '연어' 거래처가 있으면, 사용자가 '연어3', '생연어'라고 써도 매칭 성공!
                            3. **[절대 원칙] 사용자가 입력한 '수량(숫자)'은 절대 삭제하지 마세요.**
                                - '연어3' -> target: '연어 3' (O)
                                - '참이슬 3박스' -> target: '참이슬 3박스' (O)
                            4. JSON Array 형태로만 출력하세요. (설명 금지)
                            예시: [{{"type": "sms", "supplier": "00수산", "target": "연어 3마리", "phone": "..."}}, {{"type": "link", ...}}]
                            """

                            res = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": prompt}]
                            )

                            clean_json = res.choices[0].message.content.strip()
                            if "```" in clean_json:
                                clean_json = clean_json.replace("```json", "").replace("```", "").strip()

                            try:
                                raw_data = json.loads(clean_json)
                            except:
                                raw_data = []

                            order_list = []
                            if isinstance(raw_data, list):
                                for item in raw_data:
                                    if isinstance(item, list): order_list.extend(item)
                                    else: order_list.append(item)
                            elif isinstance(raw_data, dict):
                                if "items" in raw_data and isinstance(raw_data["items"], list):
                                    order_list = raw_data["items"]
                                else:
                                    order_list = [raw_data]

                            st.success("✅ 분류가 완료되었습니다.")

                            if not order_list:
                                st.warning("⚠️ 분류된 내용이 없습니다. (주문 내용을 조금 더 명확하게 써보세요)")

                            for item in order_list:
                                if not isinstance(item, dict): continue
                                safe_item = {k.lower(): v for k, v in item.items()}
                                item_type = safe_item.get('type', 'unknown').lower()

                                with st.container(border=True):
                                    if item_type == 'sms':
                                        target = safe_item.get('target', '품목')
                                        supplier = safe_item.get('supplier', '거래처')
                                        st.subheader(f"[{supplier}] {target}")

                                        content = f"안녕하세요\n{my_store_name}입니다.\n{target} 부탁드립니다."

                                        phone = str(safe_item.get('phone', '')).replace('-', '').strip()
                                        msg_val = st.text_area("내용 확인", value=content, height=100, key=f"sms_{target}_{phone}")

                                        if phone:
                                            encoded_msg = urllib.parse.quote(msg_val)
                                            link = f"sms:{phone}?body={encoded_msg}"
                                            st.markdown(f"""
                                            <div style="text-align: right; margin-top: 10px;">
                                                <a href="{link}" target="_top" style="text-decoration: none !important;">
                                                    <div style="display: inline-block; background-color: #03C75A; color: white !important; padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 16px;">
                                                        📨 문자 보내기
                                                    </div>
                                                </a>
                                            </div>
                                            """, unsafe_allow_html=True)
                                        else:
                                            st.error("⚠️ 전화번호 없음")

                                    elif item_type == 'link':
                                        target = safe_item.get('target', '상품')
                                        mall = safe_item.get('mall', '쇼핑몰')
                                        url = safe_item.get('url', '#')
                                        st.subheader(f"[{mall}] {target}")

                                        matched = next((l for l in links if l['alias'] == target), None)
                                        if matched and matched.get('last_updated'):
                                            try:
                                                from datetime import datetime
                                                last_dt = datetime.fromisoformat(matched.get('last_updated'))
                                                days = (datetime.now() - last_dt).days
                                                if days > 30: st.warning(f"⚠️ {days}일 전 가격")
                                            except: pass

                                        st.caption(f"이동 주소: {url}")
                                        st.markdown(f"""
                                        <div style="text-align: right; margin-top: 10px;">
                                            <a href="{url}" target="_blank" style="text-decoration: none !important;">
                                                <div style="display: inline-block; background-color: #3B82F6; color: white !important; padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 16px;">
                                                    👉 구매하러 가기
                                                </div>
                                            </a>
                                        </div>
                                        """, unsafe_allow_html=True)
                        except Exception as e:
                            if "429" in str(e):
                                st.warning("⚠️ AI 사용 한도가 초과되었습니다. (잠시 후 다시 시도해주세요)")
                            else:
                                st.error(f"오류: {e}")

    # ==============================================================================
    # TAB 2: 거래처 관리
    # ==============================================================================
    elif selected_tab == "📱 거래처 관리":

        st.info("💡 팁: 거래처에서 받은 품목 리스트를 아래에 **복사+붙여넣기** 하세요. (줄바꿈도 자동으로 정리됩니다!)")

        with st.container(border=True):
            st.markdown("#### ➕ 새 거래처 등록")

            if "in_sup_name" not in st.session_state: st.session_state["in_sup_name"] = ""
            if "in_sup_phone" not in st.session_state: st.session_state["in_sup_phone"] = ""
            if "in_sup_items" not in st.session_state: st.session_state["in_sup_items"] = ""

            c1, c2 = st.columns(2)
            new_name = c1.text_input("거래처 이름 (상호)", key="in_sup_name")
            new_phone = c2.text_input("전화번호", key="in_sup_phone", placeholder="010-xxxx-xxxx")

            new_items_raw = st.text_area("취급 품목 (복사 붙여넣기)", 
                                            key="in_sup_items", 
                                            height=100, 
                                            placeholder="예시:\n광어\n우럭\n낙지\n(엔터로 구분해도 됩니다)")

            if st.button("💾 거래처 저장", type="primary", use_container_width=True):
                if not new_name or not new_phone:
                    st.error("이름과 전화번호는 필수입니다.")
                else:
                    with st.spinner("저장 중..."):
                        final_items = new_items_raw.replace("\n", ",").replace(",,", ",")
                        add_supplier(st.session_state.store_id, new_name, new_phone, final_items)
                        st.success(f"'{new_name}' 등록 완료!")
                        time.sleep(1) # Visual feedback
                        st.rerun()

        st.markdown("---")

        suppliers = get_suppliers(st.session_state.store_id)
        if not suppliers:
            st.info("등록된 거래처가 없습니다.")

        for s in suppliers:
            with st.expander(f"🏢 {s['name']} (품목: {s['items']})"):
                with st.form(key=f"edit_sup_form_{s['id']}"):
                    st.caption("📝 거래처 정보 수정")
                    ec1, ec2 = st.columns(2)
                    edit_name = ec1.text_input("이름", value=s['name'])
                    edit_phone = ec2.text_input("번호", value=s['phone'])
                    edit_items = st.text_input("취급품목", value=s['items'])

                    c_save, c_del = st.columns([1, 1])
                    if c_save.form_submit_button("💾 수정 저장", type="primary"):
                        update_supplier(s['id'], edit_name, edit_phone, edit_items)
                        st.success("수정되었습니다.")
                        time.sleep(0.5)
                        st.rerun()

                st.markdown("")
                if st.button("🗑️ 거래처 삭제", key=f"btn_del_sup_{s['id']}"):
                    delete_supplier(s['id'])
                    st.rerun()

    # ==============================================================================
    # TAB 3: 온라인 링크
    # ==============================================================================
    elif selected_tab == "🌐 온라인 링크":

        col_top1, col_top2 = st.columns([1, 1])
        with col_top1:
            if "confirm_delete_all" not in st.session_state:
                st.session_state.confirm_delete_all = False
            if not st.session_state.confirm_delete_all:
                if st.button("🗑️ 목록 전체 삭제", use_container_width=True):
                    st.session_state.confirm_delete_all = True
                    st.rerun()
            else:
                c_del1, c_del2 = st.columns(2)
                if c_del1.button("진짜 삭제?", type="primary", use_container_width=True):
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("DELETE FROM online_items WHERE store_id=?", (st.session_state.store_id,))
                    conn.commit()
                    conn.close()
                    st.session_state.confirm_delete_all = False
                    st.success("삭제 완료")
                    st.rerun()
                if c_del2.button("취소", use_container_width=True):
                    st.session_state.confirm_delete_all = False
                    st.rerun()

        with col_top2:
            if st.button("🧹 중복 링크 정리", type="secondary", use_container_width=True):
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT * FROM online_items WHERE store_id=? ORDER BY id DESC", (st.session_state.store_id,))
                items = [dict(r) for r in c.fetchall()]
                seen = set()
                dels = []
                for it in items:
                    u = (it['url'] or "").strip()
                    k = u if u else it['alias']
                    if k in seen: dels.append(it['id'])
                    else: seen.add(k)
                if dels:
                    for did in dels: c.execute("DELETE FROM online_items WHERE id=?", (did,))
                    conn.commit()
                    st.success(f"{len(dels)}개 정리 완료")
                    time.sleep(1)
                    st.rerun()
                else: st.toast("중복 없음")
                conn.close()

        with st.expander("➕ 엑셀/텍스트 등록", expanded=False):
            with st.form("excel_upload_form"):
                raw_text = st.text_area("내용 입력 (상품명 [탭] 쇼핑몰 [탭] 링크)", height=150)
                if st.form_submit_button("등록"):
                    if raw_text.strip():
                        lines = raw_text.strip().split('\n')
                        cnt = 0
                        for line in lines:
                            parts = line.split('\t')
                            if len(parts) >= 3:
                                add_online_item(st.session_state.store_id, parts[0], parts[1], parts[2])
                                cnt += 1
                        st.success(f"{cnt}개 등록 완료!")
                        st.rerun()

        st.markdown("---")

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute("SELECT * FROM online_items WHERE store_id = ? ORDER BY is_fixed DESC, id DESC", (st.session_state.store_id, ))
            links_db = [dict(row) for row in c.fetchall()]
        except: links_db = []
        conn.close()

        if not links_db: st.info("등록된 링크가 없습니다.")

        for l in links_db:
            with st.container(border=True):
                c_head1, c_head2, c_head3 = st.columns([0.5, 6, 1])

                is_pinned = l.get('is_fixed', 0) == 1
                if is_pinned: c_head1.markdown("📌")
                c_head2.markdown(f"**{l['alias']}** <span style='color:#888; font-size:12px;'>({l['mall_name']})</span>", unsafe_allow_html=True)

                del_key = f"del_mode_{l['id']}"
                if del_key not in st.session_state: st.session_state[del_key] = False

                if not st.session_state[del_key]:
                    if c_head3.button("🗑️", key=f"btn_del_{l['id']}"):
                        st.session_state[del_key] = True
                        st.rerun()
                else:
                    if c_head3.button("확인", key=f"btn_con_{l['id']}", type="primary"):
                        delete_online_item(l['id'])
                        del st.session_state[del_key]
                        st.rerun()

                _last_p = l.get('last_confirmed_price')
                _last_t = l.get('last_confirmed_at')
                _status = (l.get('price_sync_status') or "").upper()

                if _status == 'OK' and _last_p:
                    _fmt_price = f"{int(_last_p):,}"
                    _fmt_date = _last_t[:16].replace('T', ' ') if _last_t else ""
                    st.markdown(f"""
                        <div style="background-color:#1a1a1a; border-left:4px solid #03C75A; padding:10px; margin:10px 0; display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <div style="color:#03C75A; font-weight:bold; font-size:17px;">💰 {_fmt_price}원</div>
                                <div style="color:#666; font-size:11px;">{_fmt_date} 확인</div>
                            </div>
                            <div style="background:#03C75A; color:white; font-size:10px; padding:2px 6px; border-radius:4px;">최신</div>
                        </div>
                    """, unsafe_allow_html=True)
                elif _status == 'PENDING':
                    st.info("⏳ 스캔 중... (창 닫지 마세요)")
                elif _status == 'FAIL':
                    st.warning("⚠️ 스캔 실패")

                c_act1, c_act2 = st.columns([1, 1])
                c_act1.link_button("👉 구매이동", l['url'], use_container_width=True)

                if c_act2.button("💰 가격 스캔", key=f"scan_{l['id']}", use_container_width=True):
                    nonce = set_price_sync_pending(l["id"])
                    st.session_state[f"trigger_scan_{l['id']}"] = nonce
                    st.rerun()

                if f"trigger_scan_{l['id']}" in st.session_state:
                    nonce = st.session_state[f"trigger_scan_{l['id']}"]
                    target_url = l['url']
                    st.markdown(f"""
                        <div class="owners-price-signal" 
                                data-item-id="{l['id']}" 
                                data-nonce="{nonce}" 
                                data-target-url="{target_url}"
                                style="display:none;"></div>
                    """, unsafe_allow_html=True)
                    del st.session_state[f"trigger_scan_{l['id']}"]

                with st.expander("수정"):
                    with st.form(key=f"edit_{l['id']}"):
                        ea = st.text_input("상품명", value=l['alias'])
                        em = st.text_input("쇼핑몰", value=l['mall_name'])
                        eu = st.text_input("URL", value=l['url'])
                        ef = st.checkbox("상단 고정", value=is_pinned)
                        if st.form_submit_button("저장"):
                            conn = sqlite3.connect(DB_PATH)
                            cur = conn.cursor()
                            cur.execute("UPDATE online_items SET alias=?, mall_name=?, url=?, is_fixed=? WHERE id=?", (ea, em, eu, 1 if ef else 0, l['id']))
                            conn.commit()
                            conn.close()
                            st.success("수정됨")
                            st.rerun()
