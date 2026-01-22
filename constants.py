from typing import Dict, Tuple, Any

# =========================
# PROFILE / PLACE REQUIRED FIELDS (실제 DB 컬럼 기준)
# =========================
PLACE_REQUIRED_FIELDS = [
    ("address", "주소"),
    ("signature", "대표 메뉴/서비스"),
    ("strengths", "강점"),
    ("keywords", "플레이스 키워드"),
    ("review_url", "네이버 리뷰 URL"),
    ("insta_url", "인스타그램 URL"),
]

# =========================
# 1) 업종/세부업종 (UX 정리)
# =========================
MAIN_CATEGORIES = ["음식점/카페", "미용/뷰티", "헬스/필라테스", "학원/교육", "기타"]

SUBCATS_FOOD_CAFE = [
    "카페/디저트", "한식", "중식", "일식", "고깃집", "술집/포차", "배달/테이크아웃 중심", "기타(직접입력)"
]

# =========================
# 2) 업종 프로필(확장 구조)
# =========================
DEFAULT_PROFILE = {
    "score_weights": {
        "address": 10,
        "signature": 10,
        "strengths": 10,
        "keywords": 10,
        "review_url": 10,
        "insta_url": 10,
        "activity_review": 15,
        "activity_insta": 10,
        "activity_blog": 7,
        "activity_event": 8,
        "activity_review_sync": 10,  # 24시간 이내 OK면 +10점
        "penalty_review_sync_over_24h": 8,  # 24시간 초과면 -8점
    },
    "todo_rules": [
        ("missing_keywords", "플레이스 키워드 5개 생성해서 등록하기"),
        ("missing_review_url", "네이버 리뷰 URL 입력하기(리뷰 답글 관리 편해짐)"),
        ("no_review_activity", "리뷰 답글 1개라도 작성하기(신뢰도/전환에 도움)"),
        ("no_insta_activity", "인스타 게시물 1개용 캡션 생성해 두기"),
        ("missing_strengths", "강점/특징 3줄 정리하기(상세설명 품질 상승)"),
        ("no_event_activity", "이번 달 이벤트 아이디어 1개 생성해두기"),
    ],
    "templates": {
        "예약/문의": [
            ("전화 문의 응대", "안녕하세요, {store_name}입니다. 무엇을 도와드릴까요?"),
            ("영업시간 안내", "영업시간은 {hours}입니다. 방문 전 확인 부탁드립니다."),
            ("단체 예약 안내", "단체 예약은 {rule} 기준으로 가능합니다. 인원/시간을 알려주시면 확인해드리겠습니다."),
        ],
        "리뷰/클레임": [
            ("리뷰 감사(기본)", "방문해주셔서 감사합니다. 다음 방문도 만족드릴 수 있도록 준비하겠습니다."),
            ("불만 리뷰 응대",
             "불편을 드려 죄송합니다. 말씀해주신 부분은 확인 후 개선하겠습니다. 가능하시면 자세한 상황을 알려주시면 더 정확히 조치하겠습니다."
             ),
            ("재방문 유도", "소중한 의견 감사합니다. 다음 방문 때 더 좋은 경험 드릴 수 있도록 하겠습니다."),
        ],
        "운영 공지": [
            ("재료 소진/조기 마감",
             "금일 재료 소진으로 조기 마감합니다. 이용에 불편을 드려 죄송하며 다음 영업일에 뵙겠습니다."),
            ("휴무 안내", "휴무일은 {closed_days}입니다. 방문 전 참고 부탁드립니다."),
            ("웨이팅 안내", "현재 웨이팅이 발생할 수 있습니다. 현장 접수 후 순서대로 안내드립니다."),
        ],
    }
}

CATEGORY_PROFILES = {
    "음식점/카페": {
        "score_weights": {
            **DEFAULT_PROFILE["score_weights"],
            "activity_review_sync": 10,
            "signature": 12,
            "review_url": 12,
            "activity_review": 18,
            "activity_insta": 8,
        },
        "todo_rules": [
            ("missing_keywords", "플레이스 키워드 5개 생성해서 등록하기(#지역 #메뉴 #분위기)"),
            ("missing_review_url", "네이버 리뷰 URL 입력하기(리뷰 답글 관리 필수)"),
            ("no_review_activity", "리뷰 답글 작성하기(최소 1개)"),
            ("missing_signature", "대표 메뉴/시그니처 3개를 명확히 정리하기"),
            ("no_event_activity", "이번 달 프로모션 1개 기획하기(점심/회식/단체 등)"),
            ("no_insta_activity", "메뉴 사진 1개용 인스타 캡션 생성하기"),
        ],
        "templates": {
            "예약/웨이팅": [
                ("단체 예약 안내",
                 "단체 예약은 {rule} 기준으로 가능합니다. 인원/시간을 알려주시면 확인해드리겠습니다."),
                ("웨이팅 안내", "현재 웨이팅이 발생할 수 있습니다. 현장 접수 후 순서대로 안내드립니다."),
                ("라스트오더 안내", "라스트오더는 {last_order}입니다. 방문 전 참고 부탁드립니다."),
            ],
            "운영 공지": [
                ("재료 소진/조기 마감",
                 "금일 재료 소진으로 조기 마감합니다. 이용에 불편을 드려 죄송하며 다음 영업일에 뵙겠습니다."),
                ("메뉴 변경 안내", "일부 메뉴는 재료 수급에 따라 변동될 수 있습니다. 양해 부탁드립니다."),
                ("주차 안내(불가)", "주차 공간이 마련되어 있지 않습니다. 인근 유료주차장 이용 부탁드립니다."),
            ],
            "리뷰/클레임": [
                ("리뷰 감사(메뉴 언급)",
                 "방문해주셔서 감사합니다. {signature} 관련 의견도 참고하겠습니다. 다음 방문도 만족드릴 수 있도록 준비하겠습니다."
                 ),
                ("불만 리뷰 응대(대기/서비스)",
                 "불편을 드려 죄송합니다. 대기/응대 과정은 확인 후 개선하겠습니다. 가능하시면 방문 시간대와 상황을 알려주시면 더 정확히 조치하겠습니다."
                 ),
            ],
        }
    },
    "미용/뷰티": DEFAULT_PROFILE,
    "헬스/필라테스": DEFAULT_PROFILE,
    "학원/교육": DEFAULT_PROFILE,
    "기타": DEFAULT_PROFILE,
}

SUBCATEGORY_PROFILES: Dict[Tuple[str, str], Dict[str, Any]] = {
    ("음식점/카페", "카페/디저트"): {
        "todo_rules": [
            ("missing_keywords", "플레이스 키워드 5개 생성(#카페 #디저트 #분위기 #테이크아웃)"),
            ("no_insta_activity", "디저트/음료 사진 1개용 인스타 캡션 생성하기"),
            ("no_review_activity", "리뷰 답글 작성하기(최소 1개)"),
        ],
        "templates": {
            "운영 공지": [
                ("테이크아웃 안내", "테이크아웃 가능합니다. 방문하셔서 주문하시면 준비해드리겠습니다."),
                ("디저트 소진 안내", "금일 디저트는 조기 소진될 수 있습니다. 방문 전 문의 부탁드립니다."),
            ]
        }
    },
    ("음식점/카페", "고깃집"): {
        "score_weights": {
            "activity_review": 20,
            "signature": 14
        },
        "todo_rules": [
            ("missing_signature", "대표 메뉴(부위/세트) 3개를 명확히 정리하기"),
            ("no_event_activity", "회식/단체용 프로모션 1개 기획하기"),
            ("no_review_activity", "리뷰 답글 작성하기(최소 1개)"),
        ],
        "templates": {
            "예약/웨이팅": [
                ("회식/단체 문의 응대",
                 "단체(회식) 예약 가능합니다. 인원/시간/예산을 알려주시면 빠르게 안내드리겠습니다."),
                ("자리/룸 안내",
                 "좌석/룸 여부는 시간대에 따라 달라질 수 있습니다. 방문 전 문의 주시면 확인해드리겠습니다."),
            ],
            "운영 공지": [
                ("콜키지 안내", "콜키지 정책은 {rule} 기준으로 운영됩니다. 자세한 내용은 문의 부탁드립니다."),
            ]
        }
    },
    ("음식점/카페", "술집/포차"): {
        "todo_rules": [
            ("missing_keywords", "플레이스 키워드 5개 생성(#술집 #안주 #2차 #분위기 #단체)"),
            ("no_event_activity", "요일별/시간대별 이벤트(예: 해피아워) 1개 기획하기"),
        ],
        "templates": {
            "운영 공지": [
                ("신분증 확인 안내", "주류 주문 시 신분증 확인을 요청드릴 수 있습니다. 양해 부탁드립니다."),
                ("라스트오더 안내", "라스트오더는 {last_order}입니다. 방문 전 참고 부탁드립니다."),
            ]
        }
    },
    ("음식점/카페", "배달/테이크아웃 중심"): {
        "todo_rules": [
            ("missing_signature", "배달 베스트 메뉴 3개를 명확히 정리하기"),
            ("missing_keywords", "플레이스 키워드 5개 생성(#배달 #포장 #빠른픽업 #메뉴)"),
            ("no_insta_activity", "포장/배달 대표 메뉴 이미지용 캡션 생성하기"),
        ],
        "templates": {
            "운영 공지": [
                ("포장 소요시간 안내",
                 "포장은 주문 상황에 따라 {minutes}분 정도 소요될 수 있습니다. 양해 부탁드립니다."),
                ("배달 지연 안내", "현재 주문이 몰려 배달이 지연될 수 있습니다. 최대한 빠르게 준비하겠습니다."),
            ]
        }
    },
}

STYLES = """
<style>
/* -------------------------------------------------------------------------- */
/*                                 FONT IMPORT                                */
/* -------------------------------------------------------------------------- */
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");

/* -------------------------------------------------------------------------- */
/*                               ROOT VARIABLES                               */
/* -------------------------------------------------------------------------- */
:root {
    --primary: #3B82F6;       /* Blue-500 */
    --primary-dark: #2563EB;  /* Blue-600 */
    --secondary: #64748B;     /* Slate-500 */
    --bg-color: #F8FAFC;      /* Slate-50 */
    --surface: #FFFFFF;       /* White */
    --text-main: #1E293B;     /* Slate-800 */
    --text-sub: #475569;      /* Slate-600 */
    --border: #E2E8F0;        /* Slate-200 */
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    --radius: 0.75rem;        /* 12px */
}

/* -------------------------------------------------------------------------- */
/*                                GLOBAL RESET                                */
/* -------------------------------------------------------------------------- */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Pretendard Variable", "Pretendard", Roboto, system-ui, sans-serif !important;
    color: var(--text-main);
    line-height: 1.6;
}

/* App Background */
.stApp {
    background-color: #F1F5F9; /* Slate-100 */
}

/* Global High-Contrast Text Policy */
p, span, div, li, label, .stMarkdown, [data-testid="stCaptionItem"], [data-testid="stWidgetLabel"] {
    color: var(--text-main) !important;
    line-height: 1.6;
}

/* Fix for Dark UI components (Boxes) - RE-OVERRIDE to Light */
.qa-box *, .guide-box *, .prompt-box *, .stButton button[kind="primary"] {
    color: #F1F5F9 !important;
}
.qa-box .header, .prompt-box .header {
    color: #FFD700 !important;
}

/* -------------------------------------------------------------------------- */
/*                                 COMPONENTS                                 */
/* -------------------------------------------------------------------------- */

/* --- Headings --- */
h1, h2, h3 {
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    color: var(--text-main) !important;
}

/* --- Buttons (stButton) --- */
/* --- Buttons (stButton) --- */
.stButton > button {
    border: 1px solid var(--border) !important;
    background-color: var(--surface) !important;
    color: var(--text-main) !important;
    border-radius: var(--radius) !important;
    padding: 0.5rem 1rem !important;
    font-weight: 600 !important;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s ease-in-out;
}

.stButton > button:hover {
    border-color: var(--primary) !important;
    color: var(--primary) !important;
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
}

.stButton > button:active {
    transform: translateY(0);
}

/* Primary Button Override */
.stButton > button[kind="primary"] {
    background-color: var(--primary) !important;
    color: white !important;
    border: none !important;
}

.stButton > button[kind="primary"]:hover {
    background-color: var(--primary-dark) !important;
    color: white !important;
    box-shadow: var(--shadow-md);
}

/* --- Inputs (Text, Number, Select) --- */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text-main) !important;
    box-shadow: none !important;
}

.stTextInput > div > div > input:focus,
.stSelectbox > div > div > div:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
}

/* --- Expanders --- */
.streamlit-expanderHeader {
    background-color: var(--surface) !important;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
}

/* --- Metrics / Stats --- */
[data-testid="stMetricValue"] {
    font-family: 'Pretendard', sans-serif;
    font-weight: 700;
}

/* -------------------------------------------------------------------------- */
/*                               CUSTOM CLASSES                               */
/* -------------------------------------------------------------------------- */

/* Card Container */
.app-card {
    background-color: #ffffff;
    padding: 1.5rem;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    border-top: 5px solid var(--primary); /* Blue Top Border */
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    margin-bottom: 1rem;
    transition: transform 0.2s;
}
.app-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.card-header {
    font-size: 1.125rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: var(--text-main);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Custom Link Button (Naver, Insta style) */
a.custom-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    padding: 0.75rem 1rem;
    font-weight: 600;
    border-radius: var(--radius);
    text-decoration: none;
    transition: all 0.2s;
    box-shadow: var(--shadow-sm);
}

a.btn-naver {
    background-color: #03C75A;
    color: white !important;
}
a.btn-naver:hover { background-color: #02b351; box-shadow: var(--shadow-md); }

a.btn-primary {
    background-color: var(--primary);
    color: white !important;
}
a.btn-primary:hover { background-color: var(--primary-dark); box-shadow: var(--shadow-md); }

a.btn-outline {
    background-color: white;
    border: 1px solid var(--border);
    color: var(--text-main) !important;
}
a.btn-outline:hover {
    border-color: var(--primary);
    color: var(--primary) !important;
}

/* Status Badges */
.badge {
    padding: 0.25rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-red { background-color: #FEE2E2; color: #DC2626; }
.badge-green { background-color: #DCFCE7; color: #16A34A; }
.badge-gray { background-color: #F1F5F9; color: #475569; }

/* Custom Content Boxes (Stable Dark Backgrounds for AI text) */
.qa-box, .guide-box, .prompt-box {
    background-color: #1E293B !important; /* Fixed Dark Background */
    color: #F1F5F9 !important; /* Fixed Light Text */
    padding: 1.25rem;
    border-radius: var(--radius);
    border: 1px solid #334155;
    margin: 1rem 0;
    box-shadow: var(--shadow-sm);
}

.qa-box .header, .prompt-box .header {
    color: #FFD700 !important;
    font-weight: 700;
    margin-bottom: 0.5rem;
}

.guide-box {
    border-top: 4px solid #FFD700;
    background-color: #1e293b !important;
}

/* Premium Segmented Control (Navigation - Button Version) */
.segmented-nav {
    display: flex;
    background-color: #E2E8F0;
    border-radius: 14px;
    padding: 4px;
    margin-bottom: 24px;
    gap: 4px;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
}

/* Base style for buttons inside segmented nav */
.segmented-nav div[data-testid="stColumn"] button {
    width: 100% !important;
    border: none !important;
    background-color: transparent !important;
    color: #64748B !important;
    font-weight: 700 !important;
    padding: 10px 0 !important;
    border-radius: 10px !important;
    transition: all 0.25s ease !important;
    height: auto !important;
    min-height: unset !important;
    box-shadow: none !important;
}

/* Active Button Highlight */
.segmented-nav div[data-testid="stColumn"].active-tab button {
    background-color: white !important;
    color: #3B82F6 !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
}

.segmented-nav div[data-testid="stColumn"] button:hover {
    background-color: rgba(255, 255, 255, 0.5) !important;
}

</style>
"""
