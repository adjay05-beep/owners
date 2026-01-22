import sqlite3
import streamlit as st
from datetime import datetime
from typing import Optional, Dict, List, Any
import secrets

DB_PATH = "owners_v9.db"

def now_iso():
    return datetime.now().isoformat()

def has_column(conn, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return column in cols

def fix_database_schema():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        # 1. 'online_items' 테이블 확인
        c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='online_items'"
        )
        if c.fetchone():
            c.execute("PRAGMA table_info(online_items)")
            columns = [info[1] for info in c.fetchall()]

            # 2. 날짜 칸 없으면 추가
            if 'last_updated' not in columns:
                c.execute(
                    "ALTER TABLE online_items ADD COLUMN last_updated TEXT")
                now_str = datetime.now().isoformat()
                c.execute(
                    "UPDATE online_items SET last_updated = ? WHERE last_updated IS NULL",
                    (now_str, ))
                st.toast("✅ 장부 업데이트: 날짜 기능 추가")

            # 3. [NEW] '고정(is_fixed)' 칸 없으면 추가
            if 'is_fixed' not in columns:
                try:
                    c.execute("ALTER TABLE online_items ADD COLUMN is_fixed INTEGER DEFAULT 0")
                    c.execute("UPDATE online_items SET is_fixed = 0 WHERE is_fixed IS NULL")
                    conn.commit()
                except sqlite3.OperationalError: pass

                # 4. [NEW] 가격 스캔(B안) 컬럼들 추가
                if 'price_sync_at' not in columns:
                    try:
                        c.execute("ALTER TABLE online_items ADD COLUMN price_sync_at TEXT")
                        conn.commit()
                    except sqlite3.OperationalError: pass

                if 'price_sync_status' not in columns:
                    try:
                        c.execute("ALTER TABLE online_items ADD COLUMN price_sync_status TEXT")
                        conn.commit()
                    except sqlite3.OperationalError: pass

                if 'price_sync_nonce' not in columns:
                    try:
                        c.execute("ALTER TABLE online_items ADD COLUMN price_sync_nonce TEXT")
                        c.execute("UPDATE online_items SET price_sync_nonce = NULL WHERE price_sync_nonce IS NULL")
                        conn.commit()
                    except sqlite3.OperationalError: pass

                if 'last_confirmed_at' not in columns:
                    try:
                        c.execute("ALTER TABLE online_items ADD COLUMN last_confirmed_at TEXT")
                        c.execute("UPDATE online_items SET last_confirmed_at = NULL WHERE last_confirmed_at IS NULL")
                        conn.commit()
                    except sqlite3.OperationalError: pass

                if 'last_confirmed_price' not in columns:
                    try:
                        c.execute("ALTER TABLE online_items ADD COLUMN last_confirmed_price INTEGER")
                        c.execute("UPDATE online_items SET last_confirmed_price = NULL WHERE last_confirmed_price IS NULL")
                        conn.commit()
                    except sqlite3.OperationalError: pass

                if 'last_confirmed_title' not in columns:
                    try:
                        c.execute("ALTER TABLE online_items ADD COLUMN last_confirmed_title TEXT")
                        c.execute("UPDATE online_items SET last_confirmed_title = NULL WHERE last_confirmed_title IS NULL")
                        conn.commit()
                    except sqlite3.OperationalError: pass

                if 'last_confirmed_url' not in columns:
                    try:
                        c.execute("ALTER TABLE online_items ADD COLUMN last_confirmed_url TEXT")
                        c.execute("UPDATE online_items SET last_confirmed_url = NULL WHERE last_confirmed_url IS NULL")
                        conn.commit()
                    except sqlite3.OperationalError: pass

                if 'last_opened_at' not in columns:
                    try:
                        c.execute("ALTER TABLE online_items ADD COLUMN last_opened_at TEXT")
                        c.execute("UPDATE online_items SET last_opened_at = NULL WHERE last_opened_at IS NULL")
                        conn.commit()
                    except sqlite3.OperationalError: pass

    except Exception as e:
        print(f"DB 수리 중 경고: {e}")
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            store_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            store_name TEXT,
            category TEXT,
            sub_category TEXT,
            address TEXT,
            target TEXT,
            signature TEXT,
            strengths TEXT,
            keywords TEXT,
            review_url TEXT,
            insta_url TEXT,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    """)

    # 테이블 구조 보정 (sub_category 없으면 추가)
    if not has_column(conn, "stores", "sub_category"):
        c.execute("ALTER TABLE stores ADD COLUMN sub_category TEXT")

    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            store_id INTEGER,
            feature TEXT,
            title TEXT,
            input_text TEXT,
            output_text TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS store_checklist (
            store_id INTEGER PRIMARY KEY,
            has_keywords INTEGER DEFAULT 0,
            has_review_url INTEGER DEFAULT 0,
            has_insta_url INTEGER DEFAULT 0,
            has_place_desc INTEGER DEFAULT 0,
            has_menu_guide INTEGER DEFAULT 0,
            has_way_guide INTEGER DEFAULT 0,
            has_parking_guide INTEGER DEFAULT 0,
            has_hours INTEGER DEFAULT 0,
            has_phone INTEGER DEFAULT 0,
            has_address INTEGER DEFAULT 0,
            has_news INTEGER DEFAULT 0,
            last_review_reply_at TEXT,
            last_insta_caption_at TEXT,
            last_blog_post_at TEXT,
            last_event_plan_at TEXT,
            last_place_qa_at TEXT
        )
    """)

    # 🔥 [핵심] 여기서 누락된 컬럼들을 강제로 추가합니다!
    if not has_column(conn, "store_checklist", "review_sync_at"):
        c.execute("ALTER TABLE store_checklist ADD COLUMN review_sync_at TEXT")

    if not has_column(conn, "store_checklist", "review_unreplied_count"):
        c.execute(
            "ALTER TABLE store_checklist ADD COLUMN review_unreplied_count INTEGER DEFAULT -1"
        )

    if not has_column(conn, "store_checklist", "review_sync_status"):
        try:
            c.execute("ALTER TABLE store_checklist ADD COLUMN review_sync_status TEXT")
            conn.commit()
        except sqlite3.OperationalError: pass

    if not has_column(conn, "store_checklist", "review_sync_nonce"):
        try:
            c.execute("ALTER TABLE store_checklist ADD COLUMN review_sync_nonce TEXT")
            conn.commit()
        except sqlite3.OperationalError: pass

    # [NEW] 광고/소식 주기 관리용
    if not has_column(conn, "store_checklist", "last_ad_analysis_at"):
        try:
            c.execute("ALTER TABLE store_checklist ADD COLUMN last_ad_analysis_at TEXT")
            conn.commit()
        except sqlite3.OperationalError: pass
    
    if not has_column(conn, "store_checklist", "last_place_news_at"):
        try:
            c.execute("ALTER TABLE store_checklist ADD COLUMN last_place_news_at TEXT")
            conn.commit()
        except sqlite3.OperationalError: pass

    if not has_column(conn, "store_checklist", "has_menu_guide"):
        try:
            c.execute("ALTER TABLE store_checklist ADD COLUMN has_menu_guide INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError: pass

    # [NEW] 비즈니스 감사 항목 (영업시간, 전화번호, 주소, 소식)
    for col in ["has_hours", "has_phone", "has_address", "has_news"]:
        if not has_column(conn, "store_checklist", col):
            try:
                c.execute(f"ALTER TABLE store_checklist ADD COLUMN {col} INTEGER DEFAULT 0")
                conn.commit()
            except sqlite3.OperationalError: pass

    # [NEW] 스캔 시점 기록용 (최초 스캔 여부 판단)
    if not has_column(conn, "store_checklist", "last_scout_at"):
        try:
            c.execute("ALTER TABLE store_checklist ADD COLUMN last_scout_at TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass # Already exists

    c.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            store_id INTEGER,
            group_name TEXT,
            title TEXT,
            content TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS todo_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            store_id INTEGER,
            todo_group TEXT,
            todo_text TEXT,
            status TEXT,      -- DONE / SKIP
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS app_state (
            k TEXT PRIMARY KEY,
            v TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER,
            name TEXT,
            phone TEXT,
            items TEXT,
            created_at TEXT
        )
    """)

    # [기존 suppliers 테이블 생성 코드 아래에 추가]
    c.execute("""
        CREATE TABLE IF NOT EXISTS online_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER,
            alias TEXT,       -- 예: 칵테일새우
            mall_name TEXT,   -- 예: 쿠팡, 배민상회
            url TEXT,         -- 상품 링크
            memo TEXT,        -- 예: 2만원 이하면 사기
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

def set_app_state(key: str, value: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO app_state (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (key, value))
    conn.commit()
    conn.close()

def get_app_state(key: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT v FROM app_state WHERE k=?", (key, ))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# 2. 체크리스트 & DB 도구
def ensure_checklist_row(store_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT store_id FROM store_checklist WHERE store_id=?", (store_id, ))
    if not c.fetchone():
        c.execute("INSERT INTO store_checklist (store_id) VALUES (?)", (store_id, ))
    conn.commit()
    conn.close()

def update_checklist_flags(store_id: int, **flags):
    ensure_checklist_row(store_id)
    cols, vals = [], []
    for k, v in flags.items():
        cols.append(f"{k}=?")
        vals.append(v)
    vals.append(store_id)
    q = f"UPDATE store_checklist SET {', '.join(cols)} WHERE store_id=?"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(q, tuple(vals))
    conn.commit()
    conn.close()

def get_checklist(store_id: int):
    ensure_checklist_row(store_id)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM store_checklist WHERE store_id=?", (store_id, ))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else {}

def set_review_sync_pending(store_id: int) -> str:
    nonce = secrets.token_urlsafe(8)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE store_checklist 
        SET review_sync_status='PENDING', review_sync_at=?, review_sync_nonce=? 
        WHERE store_id=?
    """, (now_iso(), nonce, store_id))
    conn.commit()
    conn.close()
    return nonce

def set_review_sync_result(store_id: int, nonce: str, status: str, unreplied_count: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT review_sync_nonce FROM store_checklist WHERE store_id=?", (store_id,))
    row = c.fetchone()
    if not row or row['review_sync_nonce'] != nonce:
        conn.close()
        return False
    try: cnt = int(unreplied_count)
    except: cnt = -1
    c.execute("""
        UPDATE store_checklist 
        SET review_sync_status=?, review_unreplied_count=?, review_sync_at=? 
        WHERE store_id=?
    """, (status, cnt, now_iso(), store_id))
    conn.commit()
    conn.close()
    return True

# 3. 매장(Store) 관리 도구
def get_user_stores(username):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT store_id, store_name FROM stores WHERE username=? ORDER BY store_id ASC", (username, ))
    rows = c.fetchall()
    conn.close()
    return rows

def get_store_info(username, store_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM stores WHERE store_id=? AND username=?", (store_id, username))
    row = c.fetchone()
    conn.close()
    return row

def get_store(store_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM stores WHERE store_id=?", (store_id, ))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else {}

def refresh_checklist_from_store(username: str, store_id: int):
    store = get_store_info(username, store_id)
    if not store: return
    update_checklist_flags(
        store_id,
        # has_keywords=1 if (store["keywords"] or "").strip() else 0, # DO NOT SYNC: Scanner is truth
        has_review_url=1 if (store["review_url"] or "").strip() else 0,
        has_insta_url=1 if (store["insta_url"] or "").strip() else 0,
    )

def add_store(username: str, store_name: str, category: str, sub_category: str, address: str, target: str, signature: str, strengths: str, keywords: str, review_url: str, insta_url: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO stores (username, store_name, category, sub_category, address, target, signature, strengths, keywords, review_url, insta_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (username, store_name, category, sub_category, address, target, signature, strengths, keywords, review_url, insta_url))
    conn.commit()
    store_id = c.lastrowid
    conn.close()
    ensure_checklist_row(store_id)
    refresh_checklist_from_store(username, store_id)
    return store_id

def update_store(username: str, store_id: int, store_name: str, category: str, sub_category: str, address: str, target: str, signature: str, strengths: str, keywords: str, review_url: str, insta_url: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE stores
        SET store_name=?, category=?, sub_category=?, address=?, target=?, signature=?, strengths=?, keywords=?, review_url=?, insta_url=?
        WHERE store_id=? AND username=?
    """, (store_name, category, sub_category, address, target, signature, strengths, keywords, review_url, insta_url, store_id, username))
    conn.commit()
    changed = (c.rowcount > 0)
    conn.close()
    if changed:
        refresh_checklist_from_store(username, store_id)
    return changed

def save_history(username: str, store_id: int, feature: str, title: str, input_text: str, output_text: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO history (username, store_id, feature, title, input_text, output_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (username, store_id, feature, title, input_text, output_text, now_iso()))
    conn.commit()
    conn.close()

def get_recent_history(username: str, store_id: int, feature: Optional[str], keyword: str, limit: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    where = "WHERE username=? AND store_id=?"
    params = [username, store_id]
    if feature and feature != "ALL":
        where += " AND feature=?"
        params.append(feature)
    if keyword.strip():
        where += " AND (title LIKE ? OR input_text LIKE ? OR output_text LIKE ?)"
        k = f"%{keyword.strip()}%"
        params.extend([k, k, k])
    q = f"SELECT * FROM history {where} ORDER BY id DESC LIMIT ?"
    params.append(limit)
    c.execute(q, tuple(params))
    rows = c.fetchall()
    conn.close()
    return rows

# 4. 거래처(Supplier) 관리 도구
def get_suppliers(store_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM suppliers WHERE store_id=? ORDER BY id DESC", (store_id, ))
    rows = c.fetchall()
    conn.close()
    return rows

def add_supplier(store_id: int, name: str, phone: str, items: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO suppliers (store_id, name, phone, items, created_at) VALUES (?, ?, ?, ?, ?)",
        (store_id, name, phone, items, now_iso()))
    conn.commit()
    conn.close()

def update_supplier(supplier_id: int, name: str, phone: str, items: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE suppliers SET name=?, phone=?, items=? WHERE id=?",
              (name, phone, items, supplier_id))
    conn.commit()
    conn.close()

def delete_supplier(supplier_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM suppliers WHERE id=?", (supplier_id, ))
    conn.commit()
    conn.close()

# 5. 온라인 링크 도구
def get_online_items(store_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM online_items WHERE store_id=?", (store_id, ))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_online_item(store_id, alias, mall_name, url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now_str = datetime.now().isoformat()
    try:
        c.execute(
            "INSERT INTO online_items (store_id, alias, mall_name, url, last_updated) VALUES (?, ?, ?, ?, ?)",
            (store_id, alias, mall_name, url, now_str))
        conn.commit()
    except sqlite3.OperationalError as e:
        if "no column named last_updated" in str(e):
            c.execute("ALTER TABLE online_items ADD COLUMN last_updated TEXT")
            conn.commit()
            c.execute(
                "INSERT INTO online_items (store_id, alias, mall_name, url, last_updated) VALUES (?, ?, ?, ?, ?)",
                (store_id, alias, mall_name, url, now_str))
            conn.commit()
        else: raise e
    conn.close()

def ensure_online_items_price_columns():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        def add_col_if_missing(col_name, ddl):
            try:
                c.execute(f"SELECT {col_name} FROM online_items LIMIT 1")
            except sqlite3.OperationalError:
                c.execute(ddl)
                conn.commit()
        add_col_if_missing("is_fixed", "ALTER TABLE online_items ADD COLUMN is_fixed INTEGER DEFAULT 0")
        add_col_if_missing("last_updated", "ALTER TABLE online_items ADD COLUMN last_updated TEXT")
        add_col_if_missing("mode", "ALTER TABLE online_items ADD COLUMN mode TEXT DEFAULT 'search'")
        add_col_if_missing("query", "ALTER TABLE online_items ADD COLUMN query TEXT")
        add_col_if_missing("price_sync_at", "ALTER TABLE online_items ADD COLUMN price_sync_at TEXT")
        add_col_if_missing("price_sync_status", "ALTER TABLE online_items ADD COLUMN price_sync_status TEXT")
        add_col_if_missing("price_sync_nonce", "ALTER TABLE online_items ADD COLUMN price_sync_nonce TEXT")
        add_col_if_missing("last_opened_at", "ALTER TABLE online_items ADD COLUMN last_opened_at TEXT")
        add_col_if_missing("last_confirmed_at", "ALTER TABLE online_items ADD COLUMN last_confirmed_at TEXT")
        add_col_if_missing("last_confirmed_price", "ALTER TABLE online_items ADD COLUMN last_confirmed_price INTEGER")
        add_col_if_missing("last_confirmed_title", "ALTER TABLE online_items ADD COLUMN last_confirmed_title TEXT")
        add_col_if_missing("last_confirmed_url", "ALTER TABLE online_items ADD COLUMN last_confirmed_url TEXT")
        conn.close()
    except: pass

def mark_price_sync_fail(item_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE online_items SET price_sync_status='FAIL' WHERE id=?", (item_id,))
        conn.commit()
        conn.close()
    except: pass

def set_price_sync_pending(item_id: int) -> str:
    nonce = secrets.token_urlsafe(12)
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE online_items SET price_sync_at=?, price_sync_status='PENDING', price_sync_nonce=? WHERE id=?",
            (now_iso(), nonce, item_id))
        conn.commit()
        conn.close()
    except: pass
    return nonce

def set_price_sync_result(item_id: int, nonce: str, price: Any, title: str, url: str) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT price_sync_nonce FROM online_items WHERE id=?", (item_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return False
        saved = (row["price_sync_nonce"] or "")
        if not saved or not nonce or saved != nonce:
            conn.close()
            return False
        p = None
        try: p = int(str(price).replace(",", "").strip())
        except: p = None
        c.execute("""
            UPDATE online_items
            SET price_sync_at=?, price_sync_status='OK', last_confirmed_at=?,
                last_confirmed_price=?, last_confirmed_title=?, last_confirmed_url=?, last_opened_at=?
            WHERE id=?
            """, (now_iso(), now_iso(), p, (title or "")[:200], (url or "")[:500], now_iso(), item_id))
        conn.commit()
        conn.close()
        return True
    except: return False

def delete_online_item(item_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM online_items WHERE id=?", (item_id, ))
    conn.commit()
    conn.close()

# 6. Todo Helper
def save_todo_event(username: str, store_id: int, todo_group: str, todo_text: str, status: str = "DONE"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO todo_events (username, store_id, todo_group, todo_text, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (username, store_id, todo_group, todo_text, status, now_iso()))
    conn.commit()
    conn.close()

def get_today_done_groups(username: str, store_id: int) -> set:
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT todo_group FROM todo_events
        WHERE username=? AND store_id=? AND status='DONE' AND substr(created_at, 1, 10)=?
    """, (username, store_id, today))
    rows = c.fetchall()
    conn.close()
    return set([r[0] for r in rows])

def apply_todo_done_effect(store_id: int, todo_group: str):
    if todo_group == "review":
        update_checklist_flags(store_id, last_review_reply_at=now_iso())
    elif todo_group == "insta":
        update_checklist_flags(store_id, last_insta_caption_at=now_iso())
    elif todo_group == "blog":
        update_checklist_flags(store_id, last_blog_post_at=now_iso())
    elif todo_group == "event":
        update_checklist_flags(store_id, last_event_plan_at=now_iso())

def mark_task_done(store_id: int, task_column: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Security check: column name whitelist
    allowed = [
        "last_review_reply_at", "last_insta_caption_at", "last_blog_post_at",
        "last_event_plan_at", "last_place_qa_at", "last_place_news_at", "last_ad_analysis_at"
    ]
    if task_column not in allowed:
        return False
        
    now_str = now_iso()
    try:
        c.execute(f"UPDATE store_checklist SET {task_column} = ? WHERE store_id = ?", (now_str, store_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()
