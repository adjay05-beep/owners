import streamlit as st
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from constants import CATEGORY_PROFILES, DEFAULT_PROFILE, SUBCATEGORY_PROFILES

def get_missing_fields(row, fields):
    """sqlite3.Row / dict 모두 안전하게 처리"""
    d = dict(row) if not isinstance(row, dict) else row
    missing = []
    for key, label in fields:
        v = d.get(key)
        if v is None:
            missing.append(label)
            continue
        if isinstance(v, str) and v.strip() == "":
            missing.append(label)
            continue
        if isinstance(v, (list, dict)) and len(v) == 0:
            missing.append(label)
            continue
    return missing

def deep_merge_profile(base: Dict[str, Any],
                       override: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "score_weights": dict(base.get("score_weights", {})),
        "todo_rules": list(base.get("todo_rules", [])),
        "templates": {
            k: list(v)
            for k, v in base.get("templates", {}).items()
        },
    }
    if "score_weights" in override:
        out["score_weights"].update(override["score_weights"])
    if "todo_rules" in override:
        out["todo_rules"] = list(override["todo_rules"]) + [
            x for x in out["todo_rules"] if x not in override["todo_rules"]
        ]
    if "templates" in override:
        for group, items in override["templates"].items():
            if group not in out["templates"]:
                out["templates"][group] = []
            out["templates"][group] = list(items) + out["templates"][group]
    return out

def get_profile(category: str, sub_category: str) -> Dict[str, Any]:
    base = CATEGORY_PROFILES.get(category, DEFAULT_PROFILE)
    merged = deep_merge_profile(DEFAULT_PROFILE,
                                base if base is not DEFAULT_PROFILE else {})
    if sub_category:
        ov = SUBCATEGORY_PROFILES.get((category, sub_category))
        if ov:
            merged = deep_merge_profile(merged, ov)
    return merged

def custom_link_button(text, url, css_class="", inline_style=""):
    st.markdown(f"""
    <a href="{url}" target="_blank" class="custom-btn {css_class}" style="{inline_style}">
        {text}
    </a>
    """, unsafe_allow_html=True)

def naver_button(text, url):
    custom_link_button(text, url, css_class="btn-naver")

def insta_button(text, url):
    grad = "background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%); color: white;"
    custom_link_button(text, url, inline_style=grad)

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def days_since(iso_str):
    if not iso_str:
        return 9999
    try:
        # iso_str can be YYYY-MM-DDTHH:MM:SS or just YYYY-MM-DD
        if "T" in iso_str:
            dt = datetime.fromisoformat(iso_str)
        else:
            # fallback
            dt = datetime.strptime(iso_str, "%Y-%m-%d")
        diff = datetime.now() - dt
        return diff.days
    except:
        return 9999

def get_naver_coordinates(address, client_id, client_secret):
    if not client_id or not client_secret:
        return None, None, "API 키 미설정"

    headers = {
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret
    }
    url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
    params = {"query": address}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=8)
        if response.status_code != 200:
            return None, None, f"Error {response.status_code}"
        data = response.json()
        if data.get("addresses"):
            return data["addresses"][0]["x"], data["addresses"][0]["y"], None
        return None, None, "주소 검색 결과 없음"
    except Exception as e:
        return None, None, f"통신 오류: {str(e)}"
