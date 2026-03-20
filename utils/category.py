"""
카테고리 분류기
- 소스 기반 아닌 제목 키워드 기반
- 카테고리: food / celeb / fashion / travel / broadcast / trend / general
"""

RULES = {
    "food": [
        "떡","밥","먹방","맛집","음식","카페","빵","라면","치킨","버터","봄동",
        "쿠키","케이크","마라","비빔","국밥","삼겹살","냉면","파스타","피자",
        "햄버거","분식","간식","요리","레시피","식당","술","커피","디저트",
        "food","eat","restaurant","cafe","bread","noodle","cook","recipe",
        "burger","pizza","sushi","ramen","mukbang","snack","drink","boba",
        "치즈","두부","김밥","순대","곱창","탕","찌개","볶음","구이","튀김",
        "아이스크림","젤라또","딸기","수박","흑당","크림","소금빵","크로플",
    ],
    "celeb": [
        "아이돌","연예인","배우","가수","유튜버","인플루언서","팬","직캠","팬캠",
        "사생활","열애","결혼","이별","복귀","데뷔","컴백","신보","앨범",
        "bts","블랙핑크","뉴진스","에스파","아이브","르세라핌","스트레이키즈",
        "방탄","트와이스","세븐틴","엑소","shinee","2pm","빅뱅","소녀시대",
        "idol","kpop","celebrity","singer","actor","actress",
        "blackpink","newjeans","aespa","ive","lesserafim",
        "아이유","박보검","송중기","전지현","김수현","이준호",
    ],
    "fashion": [
        "패션","옷","코디","스타일","브랜드","신발","가방","주얼리","빈티지",
        "스트릿","아이템","룩","무신사","하입","나이키","아디다스","구찌","샤넬",
        "fashion","style","outfit","brand","sneaker","luxury","bag","shoes",
        "y2k","gorpcore","streetwear","ootd","트렌치","청바지","니트","후드",
        "뷰티","메이크업","스킨케어","립스틱","파운데이션","향수","네일",
        "beauty","makeup","skincare","lipstick","perfume",
    ],
    "travel": [
        "여행","관광","해외여행","국내여행","숙소","호텔","캠핑","트립","투어",
        "제주","부산","경주","전주","강릉","속초","여수","통영",
        "도쿄","오사카","교토","후쿠오카","방콕","발리","파리","런던","뉴욕",
        "travel","trip","tour","hotel","airbnb","vacation","holiday",
        "비행기","항공","공항","입국","출국","visa","여권",
    ],
    "broadcast": [
        "드라마","영화","예능","방송","넷플릭스","웨이브","왓챠","티빙",
        "OST","시즌","에피소드","캐릭터","감독","출연","시청률","개봉",
        "ost","drama","movie","film","netflix","series","anime","webtoon",
        "무한도전","런닝맨","나혼자산다","놀면뭐하니","유퀴즈","라디오스타",
        "mbc","kbs","sbs","tvn","jtbc","ocn","mnet",
        "싱어게인","미스터트롯","보이스코리아","쇼미더머니",
    ],
    "trend": [
        "급상승","트렌드","유행","밈","챌린지","신조어","짤","바이럴",
        "화제","레전드","역대급","실시간","핫이슈","논란","화제작",
        "trending","viral","meme","challenge","trend","hot","issue",
        "인터넷밈","드립","짤방","유머","개그","웃긴","ㅋㅋ",
    ],
}


def classify_category(title: str) -> str:
    if not title:
        return "general"

    t = title.lower()

    scores: dict[str, int] = {cat: 0 for cat in RULES}
    for cat, keywords in RULES.items():
        for kw in keywords:
            if kw in t:
                scores[cat] += 1

    best  = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"
