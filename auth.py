import sqlite3
import os
import hashlib
import hmac
import base64
from database import DB_PATH

def _is_hashed_password(stored: str) -> bool:
    # base64(salt16 + dk32) 형태면 보통 64~80자 사이
    if not stored or len(stored) < 40:
        return False
    try:
        raw = base64.b64decode(stored.encode("utf-8"))
        return len(raw) >= 48  # salt(16) + dk(32)
    except Exception:
        return False

def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, 120_000)
    return base64.b64encode(salt + dk).decode("utf-8")

def verify_password(pw: str, stored: str) -> bool:
    raw = base64.b64decode(stored.encode("utf-8"))
    salt, dk = raw[:16], raw[16:]
    new_dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, 120_000)
    return hmac.compare_digest(dk, new_dk)

def username_exists(username: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username=?", (username, ))
    ok = c.fetchone() is not None
    conn.close()
    return ok

def create_user(username: str, password: str) -> bool:
    if username_exists(username):
        return False
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
              (username, hash_password(password)))
    conn.commit()
    conn.close()
    return True

def verify_user(username: str, password: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username=?", (username, ))
    row = c.fetchone()

    if not row:
        conn.close()
        return False

    stored = row[0] or ""
    return verify_password(password, stored)

def seed_admin():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT username, password FROM users WHERE username='admin'")
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                  ("admin", hash_password("1234")))
    else:
        # 혹시 평문이면 자동 해시로 교체
        stored = row[1] or ""
        if not _is_hashed_password(stored):
            c.execute("UPDATE users SET password=? WHERE username='admin'",
                      (hash_password(stored or "1234"), ))

    c.execute("SELECT store_id FROM stores WHERE username='admin'")
    if not c.fetchone():
        c.execute(
            """
            INSERT INTO stores (username, store_name, category, sub_category, address, target, signature, strengths, keywords, review_url, insta_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            ("admin", "영일만", "음식점/카페", "한식", "서울 동작구 남부순환로271길 27",
             "직장인 회식, 로컬 찐단골, 소주파", "자연산 막회, 과메기, 물회",
             "가성비 최고, 웨이팅 맛집, 신선한 자연산, 노포 감성", "사당 맛집, 사당역 횟집, 사당 막회, 사당 과메기",
             "https://new.smartplace.naver.com/bizes/place/8073311/reviews?bookingBusinessId=925655&menu=visitor",
             "https://www.instagram.com"))
        c.execute(
            """
            INSERT INTO stores (username, store_name, category, sub_category, address, target, signature, strengths, keywords, review_url, insta_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("admin", "두번째매장(샘플)", "음식점/카페", "카페/디저트", "서울 강남구 테헤란로 123",
              "점심 직장인, 테이크아웃", "시그니처 커피, 샌드위치", "빠른 제공, 깔끔한 매장, 좌석 여유",
              "강남 카페, 테헤란로 커피, 점심 맛집", "", "https://www.instagram.com"))

    conn.commit()
    conn.close()
