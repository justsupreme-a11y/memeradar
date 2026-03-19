"""
카테고리 자동 분류
제목 키워드 기반으로 F&B / 패션 / 셀럽 / 일반 분류
"""

FB_KEYWORDS = [
    "떡", "밥", "먹방", "맛집", "음식", "카페", "빵", "라면", "치킨",
    "버터", "봄동", "비빔", "쿠키", "케이크", "스무디", "마라",
    "food", "eat", "restaurant", "cafe", "bread", "noodle",
]

FASHION_KEYWORDS = [
    "패션", "옷", "코디", "스타일", "브랜드", "신발", "가방", "주얼리",
    "빈티지", "스트릿", "아이템", "룩", "무신사", "지큐", "맥심",
    "fashion", "style", "outfit", "brand", "sneaker", "luxury",
    "y2k", "gorpcore", "normcore", "streetwear",
]

CELEB_KEYWORDS = [
    "아이돌", "연예인", "배우", "가수", "유튜버", "크리에이터", "인플루언서",
    "드라마", "영화", "앨범", "콘서트", "직캠", "팬캠",
    "idol", "celeb", "celebrity", "actor", "singer", "kpop",
    "bts", "blackpink", "newjeans", "aespa", "ive",
]


def classify_category(title: str) -> str:
    title_lower = title.lower()

    fb_score      = sum(1 for kw in FB_KEYWORDS      if kw in title_lower)
    fashion_score = sum(1 for kw in FASHION_KEYWORDS if kw in title_lower)
    celeb_score   = sum(1 for kw in CELEB_KEYWORDS   if kw in title_lower)

    scores = {
        "fb":      fb_score,
        "fashion": fashion_score,
        "celeb":   celeb_score,
    }

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"
