from datetime import datetime
import streamlit as st
from typing import Optional, List, Dict
from utils import get_profile, days_since, get_missing_fields
from constants import PLACE_REQUIRED_FIELDS
from database import get_today_done_groups

def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except:
        return None

def activity_points(ts: Optional[str], weight: int) -> int:
    """
    최근성 점수:
    - 7일 이내: 100%
    - 30일 이내: 50%
    - 그 외/없음: 0%
    """
    d = days_since(ts)
    if d is None:
        return 0
    if d <= 7:
        return weight
    if d <= 30:
        return max(1, int(weight * 0.5))
    return 0

def calc_operating_score(store_row, checklist_row):
    sub = (store_row["sub_category"] or "").strip()
    prof = get_profile(store_row["category"], sub)
    w = prof["score_weights"]

    score = 0
    # 1. 기본 프로필 점수 (빈칸이면 0점, 채워져 있으면 점수)
    score += w["address"] if (store_row["address"] or "").strip() else 0
    score += w["signature"] if (store_row["signature"] or "").strip() else 0
    score += w["strengths"] if (store_row["strengths"] or "").strip() else 0
    score += w["keywords"] if (store_row["keywords"] or "").strip() else 0
    score += w["review_url"] if (store_row["review_url"] or "").strip() else 0
    score += w["insta_url"] if (store_row["insta_url"] or "").strip() else 0

    # 2. 활동 점수 (최근 활동 여부)
    score += activity_points(checklist_row["last_review_reply_at"],
                             w["activity_review"])
    score += activity_points(checklist_row["last_insta_caption_at"],
                             w["activity_insta"])
    score += activity_points(checklist_row["last_blog_post_at"],
                             w["activity_blog"])
    score += activity_points(checklist_row["last_event_plan_at"],
                             w["activity_event"])

    # 3. [핵심] 리뷰 동기화 및 미답변 감점 로직
    sync_at = checklist_row["review_sync_at"]
    sync_status = (checklist_row["review_sync_status"] or "").upper()
    unreplied = checklist_row["review_unreplied_count"]

    dt_sync = _parse_iso(sync_at)

    # 동기화 기록이 없거나 24시간이 지났으면 감점
    if not dt_sync:
        score -= w.get("penalty_review_sync_over_24h", 0)
    else:
        over_24h = (datetime.now() - dt_sync).total_seconds() > 24 * 3600
        if over_24h:
            score -= w.get("penalty_review_sync_over_24h", 0)
        elif sync_status == "OK":
            # 동기화 성공 점수 부여
            score += w.get("activity_review_sync", 0)

            # 🔥 [매운맛] 미답변 개수에 따른 감점 폭격
            if isinstance(unreplied, int):
                if unreplied == 0:
                    score += 5  # 보너스
                elif 1 <= unreplied <= 5:
                    score += 0  # 봐줌
                elif 6 <= unreplied <= 20:
                    score -= 5  # 주의
                elif 21 <= unreplied <= 100:
                    score -= 15  # 위험
                elif unreplied > 100:
                    score -= 30  # 심각 (905개면 여기서 -30점)

    # 0점~100점 사이로 제한
    return max(0, min(score, 100))

def get_score_risks(store_row, checklist_row):
    risks = []

    # 데이터 안전하게 가져오기
    ck = dict(checklist_row) if checklist_row else {}

    # 1. 활동 공백 리스크
    d_review = days_since(ck.get("last_review_reply_at"))
    d_insta = days_since(ck.get("last_insta_caption_at"))

    if d_review is None:
        risks.append(
            ("HIGH", "리뷰 답글 기록이 없습니다. (첫 답글 작성 추천)", "REVIEW", "답글 쓰러가기"))
    elif d_review > 30:
        risks.append(("HIGH", f"리뷰 답글이 {d_review}일째 없습니다. (점수 하락 원인)",
                      "REVIEW", "답글 쓰러가기"))

    if d_insta is None:
        risks.append(("MID", "인스타 캡션 생성 기록이 없습니다.", "INSTA", "캡션 만들기"))

    # 2. 필수 정보 누락
    if not (store_row["review_url"] or "").strip():
        risks.append(("MID", "리뷰 URL 미입력 (동기화 불가)", "STORE_EDIT", "입력하기"))

    # 3. [핵심] 미답변 리뷰 개수 (무조건 숫자로 변환해서 검사)
    raw_unreplied = ck.get("review_unreplied_count")
    try:
        # 글자든 숫자든 무조건 정수(int)로 변환 시도
        val = int(str(raw_unreplied).replace(',', ''))
    except:
        val = -1

    # 변환된 숫자(val)로 검사
    if val > 100:
        risks.append(
            ("HIGH", f"🚨 미답변 리뷰가 {val}개나 쌓여있습니다! (심각)", "REVIEW", "답글 달러 가기"))
    elif val > 20:
        risks.append(("HIGH", f"미답변 리뷰가 {val}개입니다. 빠른 관리가 필요합니다.", "REVIEW",
                      "답글 달러 가기"))
    elif val > 5:
        risks.append(
            ("MID", f"미답변 리뷰 {val}개가 기다리고 있습니다.", "REVIEW", "답글 달러 가기"))

    # 4. 동기화 날짜 체크
    sync_at = ck.get("review_sync_at")
    dt_sync = _parse_iso(sync_at)
    if not dt_sync:
        risks.append(("MID", "리뷰 동기화 기록이 없습니다.", "DASHBOARD", "동기화 하기"))
    else:
        # 24시간 지났는지 확인
        if (datetime.now() - dt_sync).total_seconds() > 24 * 3600:
            risks.append(("HIGH", "리뷰 데이터가 오래되었습니다. 다시 동기화해주세요.", "DASHBOARD",
                          "동기화 하기"))

    # 5. 프로필 핵심값 누락
    missing = get_missing_fields(store_row, PLACE_REQUIRED_FIELDS)
    if len(missing) >= 3:
        risks.append(("HIGH", "프로필 핵심값이 많이 비어 있습니다.", "STORE_EDIT", "채우러 가기"))

    # 정렬 (심각한 게 위로)
    order = {"HIGH": 0, "MID": 1, "LOW": 2}
    risks.sort(key=lambda x: order[x[0]])

    return risks

def today_todos(store_row, checklist_row, username):
    """
    중복 제거 + '바로가기'용 target page 포함
    return: [{"group":"review","text":"...","page":"REVIEW"}, ...]
    """
    sub = (store_row["sub_category"] or "").strip()
    prof = get_profile(store_row["category"], sub)
    rules = prof["todo_rules"]

    todos = []
    added_groups = set()

    def add(group: str, text: str, page: str):
        if group in added_groups:
            return
        added_groups.add(group)
        todos.append({"group": group, "text": text, "page": page})

    # 긴급 먼저
    d_review = days_since(checklist_row["last_review_reply_at"])
    if d_review is None or d_review > 30:
        add("review", "⚠️ 리뷰 답글을 오늘 1개 작성하세요 (점수/신뢰도 영향 큼)", "REVIEW")

    d_insta = days_since(checklist_row["last_insta_caption_at"])
    if d_insta is None or d_insta > 30:
        add("insta", "인스타 캡션 1개 생성해 게시물 준비하세요", "INSTA")

    group_map = {
        "missing_keywords": ("keywords", "PLACE"),
        "missing_review_url": ("review_url", "STORE_EDIT"),
        "missing_insta_url": ("insta_url", "STORE_EDIT"),
        "missing_strengths": ("strengths", "STORE_EDIT"),
        "missing_signature": ("signature", "STORE_EDIT"),
        "no_review_activity": ("review", "REVIEW"),
        "no_insta_activity": ("insta", "INSTA"),
        "no_blog_activity": ("blog", "BLOG"),
        "no_event_activity": ("event", "EVENT"),
    }

    def cond(name: str) -> bool:
        if name == "missing_keywords":
            return not (store_row["keywords"] or "").strip()
        if name == "missing_review_url":
            return not (store_row["review_url"] or "").strip()
        if name == "missing_insta_url":
            return not (store_row["insta_url"] or "").strip()
        if name == "missing_strengths":
            return not (store_row["strengths"] or "").strip()
        if name == "missing_signature":
            return not (store_row["signature"] or "").strip()
        if name == "no_review_activity":
            return not bool(checklist_row["last_review_reply_at"])
        if name == "no_insta_activity":
            return not bool(checklist_row["last_insta_caption_at"])
        if name == "no_blog_activity":
            return not bool(checklist_row["last_blog_post_at"])
        if name == "no_event_activity":
            return not bool(checklist_row["last_event_plan_at"])
        return False

    done_groups = get_today_done_groups(username,
                                        store_row["store_id"])

    for key, text in rules:
        if cond(key):
            grp, page = group_map.get(key, ("etc", "DASHBOARD"))
            # 🔥 오늘 이미 완료한 그룹이면 추천 제외
            if grp in done_groups:
                continue
            add(grp, text, page)

    return todos[:3]

def pick_top_action(store_row, checklist_row, username):
    """
    오늘의 1가지를 결정한다.
    - HIGH 위험이 있으면 그 중 첫 번째를 반환
    - 없으면 pick_top_action() 결과를 반환

    반환 형태:
    - risks에서 고른 경우: (level, msg, page, label)
    - pick_top_action이 dict면 dict 그대로 반환
    """
    risks = get_score_risks(store_row, checklist_row)

    # risks: [(level, msg, page, label), ...]
    high_risks = [r for r in risks if r and r[0] == "HIGH"]
    if high_risks:
        return high_risks[0]  # (level, msg, page, label)

    # 위험요인이 없으면: 점수 높으면 유지 메시지
    score = calc_operating_score(store_row, checklist_row)
    if score >= 90:
        return {
            "title": "오늘의 1가지: 유지 관리",
            "desc": "현재 운영 상태가 매우 좋아요. 오늘은 유지 관리만 해도 충분합니다.",
            "page": "DASHBOARD",
            "reason": "최근 활동/필수 입력이 안정적으로 유지되고 있어요."
        }

    # 기본 fallback: 추천 3 중 첫 번째
    todos = today_todos(store_row, checklist_row, username)
    if todos:
        t = todos[0]
        return {"title": "오늘의 1가지", "desc": t["text"], "page": t["page"]}

    return None

def calc_az_progress(store_row, checklist_row) -> dict:
    """
    반환:
    {
      "progress": 0~100(int),
      "done": int,
      "total": int,
      "items": [(label:str, done:bool, prio:int), ...]
    }
    prio 숫자가 작을수록 우선순위 높음
    """
    s = dict(store_row) if not isinstance(store_row, dict) else store_row
    ck = dict(checklist_row) if not isinstance(checklist_row,
                                               dict) else checklist_row

    def has_text(key: str) -> bool:
        return bool((s.get(key) or "").strip())

    def has_ts(key: str) -> bool:
        return bool(ck.get(key))

    items = []

    # ---- 프로필 필수(우선순위 높음) ----
    items.append(("프로필: 주소 입력", has_text("address"), 1))
    items.append(("프로필: 대표메뉴/서비스 입력", has_text("signature"), 1))
    items.append(("프로필: 강점 입력", has_text("strengths"), 1))

    # ---- 채널 연결(우선순위 중) ----
    items.append(("리뷰: 리뷰 URL 입력", has_text("review_url"), 2))
    items.append(("인스타: 인스타 URL 입력", has_text("insta_url"), 2))

    # ---- 플레이스 기본(우선순위 중) ----
    items.append(("플레이스: 키워드 등록", has_text("keywords"), 2))
    items.append(("플레이스: 상세설명 생성", bool(ck.get("has_place_desc")), 3))
    items.append(("플레이스: 찾아오는 길 생성", bool(ck.get("has_way_guide")), 3))
    items.append(("플레이스: 주차 안내 생성", bool(ck.get("has_parking_guide")), 3))

    # ---- 활동(우선순위 상황에 따라) ----
    items.append(("리뷰: 답글 1개 생성", has_ts("last_review_reply_at"), 2))
    items.append(("인스타: 캡션 1개 생성", has_ts("last_insta_caption_at"), 3))
    items.append(("마케팅: 체험단 공고 1개 생성", has_ts("last_blog_post_at"), 4))
    items.append(("이벤트: 기획안 1개 생성", has_ts("last_event_plan_at"), 4))

    total = len(items)
    done = sum(1 for _, d, _ in items if d)
    progress = int((done / total) * 100) if total else 0

    return {"progress": progress, "done": done, "total": total, "items": items}
