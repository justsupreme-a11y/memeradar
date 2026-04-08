"""
밈 키워드 필터
- 소스별로 "이게 밈이다" 신호 키워드 필터링
- True = 밈일 가능성 높음 → 저장
- False = 밈 아닐 가능성 높음 → 버림
"""

# =====================
# 밈 신호 키워드 (있으면 밈)
# =====================

MEME_SIGNALS = [
    # 반응 표현
    "ㅋㅋ", "ㅎㅎ", "ㄷㄷ", "ㅠㅠ", "ㅜㅜ", "ㄹㅇ", "ㅇㅈ", "ㅇㅇ",
    "레전드", "역대급", "실화냐", "미쳤다", "미친거", "대박", "헐", "개웃김",
    "ㅋㅋㅋ", "ㄹㅇㅋㅋ", "진짜로", "실화임", "레전설", "명작",

    # 밈 관련 직접 표현
    "짤", "밈", "드립", "유행", "챌린지", "바이럴", "레전", "짤방",
    "유행어", "신조어", "클리셰", "패러디", "오마주",

    # 커뮤니티 반응
    "난리남", "난리났", "화제", "핫함", "뜨고있", "퍼지고있",
    "모르는사람", "알고보니", "반전", "충격", "경악",

    # 영상/이미지 관련
    "쇼츠", "릴스", "숏폼", "틱톡", "유튜브",
    "영상", "움짤", "gif", "GIF",

    # 해외 밈 신호
    "meme", "viral", "trend", "lol", "lmao", "omg", "wtf",
    "based", "cringe", "ratio", "slay", "no way", "bro",
]

# =====================
# 뉴스/비밈 블랙리스트 (있으면 버림)
# =====================

NEWS_BLACKLIST = [
    # 정치
    "대통령", "국회", "의원", "정당", "선거", "탄핵", "내각",
    "여당", "야당", "민주당", "국민의힘", "정부",

    # 경제/주식
    "주가", "코스피", "나스닥", "환율", "금리", "부동산",
    "아파트", "청약", "주식", "코인", "비트코인",

    # 스포츠 경기 결과
    "득점", "승리", "패배", "결승", "준결승", "시즌",
    "리그", "경기결과", "스코어",

    # 사건/사고
    "사망", "사고", "화재", "지진", "태풍", "홍수",
    "범죄", "체포", "수사", "재판", "판결",

    # 공지/이벤트
    "[공지]", "[안내]", "[이벤트]", "[광고]", "[모집]",
    "공지사항", "이용약관", "개인정보",
]

# =====================
# 소스별 특화 설정
# =====================

SOURCE_CONFIG = {
    "instiz": {
        "require_any": [
            "ㅋㅋ", "ㄷㄷ", "레전드", "실화냐", "미쳤다", "대박",
            "짤", "밈", "드립", "유행", "챌린지", "헐", "개웃김",
            "난리남", "화제", "반전", "충격", "역대급", "레전",
            "쇼츠", "릴스", "틱톡",
        ],
        "min_title_len": 5,
    },
    "theqoo": {
        "require_any": [
            "ㅋㅋ", "ㄷㄷ", "레전드", "실화냐", "미쳤다", "대박",
            "짤", "밈", "드립", "유행", "헐", "개웃김",
            "난리남", "화제", "반전", "충격", "역대급",
            "쇼츠", "릴스", "틱톡", "바이럴",
        ],
        "min_title_len": 5,
    },
    "pannate": {
        "require_any": MEME_SIGNALS,
        "min_title_len": 5,
    },

    # YouTube 3종 — 자체 큐레이션이지만 NEWS_BLACKLIST는 적용
    "youtube_channel_hype":  {"require_any": [], "blacklist": NEWS_BLACKLIST},
    "youtube_meme_ch":       {"require_any": [], "blacklist": NEWS_BLACKLIST},
    "youtube_trending_hype": {"require_any": [], "blacklist": NEWS_BLACKLIST},

    # 패션 매거진 — 자체 큐레이션이지만 NEWS_BLACKLIST 적용
    "hypebeast":    {"require_any": [], "blacklist": NEWS_BLACKLIST},
    "hypebeast_en": {"require_any": [], "blacklist": NEWS_BLACKLIST},
    "gqkorea":      {"require_any": [], "blacklist": NEWS_BLACKLIST},

    # 완전 자체 큐레이션 — 필터 없음
    "gogumafarm":   {"require_any": [], "blacklist": []},
    "kym":          {"require_any": [], "blacklist": []},
    "google_trends": {"require_any": [], "blacklist": []},
}


def is_meme_worthy(title: str, source: str) -> bool:
    """
    밈으로 저장할 가치가 있는지 판단
    True = 저장, False = 버림
    """
    if not title:
        return False

    config = SOURCE_CONFIG.get(source, {
        "require_any":   [],
        "blacklist":     NEWS_BLACKLIST,
        "min_title_len": 3,
    })

    # 최소 길이 체크
    min_len = config.get("min_title_len", 3)
    if len(title.strip()) < min_len:
        return False

    t = title.lower()

    # 블랙리스트 체크 (있으면 버림)
    blacklist = config.get("blacklist", NEWS_BLACKLIST)
    for kw in blacklist:
        if kw.lower() in t:
            return False

    # 필수 키워드 체크 (있어야 저장)
    required = config.get("require_any", [])
    if not required:
        return True  # 필수 키워드 없으면 통과

    for kw in required:
        if kw.lower() in t:
            return True

    return False
