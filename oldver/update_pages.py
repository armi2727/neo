#!/usr/bin/env python3
"""
update_pages.py
Confluence ArtCraft 페이지를 긁어와 index.html의 PAGES 배열을 자동 갱신합니다.

사용법:
    python update_pages.py

환경변수 (필수):
    CONFLUENCE_TOKEN  — Confluence API 토큰
                        발급: https://id.atlassian.com/manage-profile/security/api-tokens

    CONFLUENCE_EMAIL  — Atlassian 계정 이메일

환경변수 (선택):
    INDEX_PATH        — 갱신할 index.html 경로 (기본값: ./index.html)
"""

import os, re, json, time, sys
from datetime import datetime
from base64 import b64encode
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
CONFLUENCE_BASE  = "https://neowiz.atlassian.net/wiki"
CONFLUENCE_EMAIL = os.environ.get("CONFLUENCE_EMAIL", "")
CONFLUENCE_TOKEN = os.environ.get("CONFLUENCE_TOKEN", "")
INDEX_PATH       = os.environ.get("INDEX_PATH", "./index.html")

# 스페이스 → 팀 매핑
SPACE_TEAM = {
    "1107": "퍼플",
    "1122": "레드",
    "1109": "블루",
    "1234": "브라운",
    "1235": "퍼플",
    "1033": "레드",
    "1192": "공용",
}

# ArtCraft 페이지가 있는 스페이스 목록
TARGET_SPACES = list(SPACE_TEAM.keys())

# 작업 유형 키워드 → type 매핑 (본문/제목에서 파싱)
TYPE_KEYWORDS = {
    "이미지생성": [
        "이미지 생성", "이미지생성", "image gen", "이미지 제작", "일러스트",
        "midjourney", "미드저니", "dzine", "krea", "flux", "stable diffusion",
        "comfyui", "dreamina", "whisk", "nanobanana", "나노바나나", "gemini.*이미지",
        "chatgpt.*이미지", "ai 이미지", "이미지.*ai",
    ],
    "영상": [
        "영상 제작", "영상제작", "영상 생성", "video", "kling", "sora", "higgsfield",
        "seedance", "veo", "hailuo", "인트로 영상", "모션", "애니메이션",
        "영상.*ai", "ai.*영상",
    ],
    "리소스": [
        "게임 리소스", "리소스 제작", "리소스 생성", "슬롯.*리소스", "심볼",
        "게임리소스", "그래픽 리소스",
    ],
    "사운드": [
        "사운드", "음악", "bgm", "sound", "music", "suno", "elevenlabs",
        "일레븐랩스", "오디오", "보이스",
    ],
    "자동화툴": [
        "자동화", "automation", "스크립트", "파이프라인", "claude code",
        "cursor", "커서", "n8n", "gitlab ci", "ci/cd", "apps script",
        "자동 생성", "자동화 툴", "자동화툴",
    ],
    "포토샵": [
        "포토샵", "photoshop", "편집", "후편집", "ai 이미지 편집",
        "weavy", "위비", "upscayl", "segment anything",
    ],
    "UI디자인": [
        "ui 디자인", "ui디자인", "ui design", "배너", "팝업", "버튼",
        "인터페이스", "ux", "ui.*제작", "배너.*제작",
    ],
    "Figma": [
        "figma", "피그마",
    ],
    "R&D·비교": [
        "r&d", "r&amp;d", "비교", "테스트", "리서치", "research",
        "분석", "검토", "qa", "실험",
    ],
    "AI제작툴": [
        "플러그인", "plugin", "툴 제작", "툴을 만", "내부 도구", "내부도구",
        "bluetester", "streamlit", "page launcher", "scheduler",
        "게임 제작기", "poc 구현", "웹 앱 제작", "자동화 시스템",
        "파일명 생성기", "align tool", "resource namer",
    ],
    "유니티": [
        "unity", "유니티", "쉐이더", "shader",
    ],
}

# 툴 키워드 → tools 배열 값 매핑
TOOL_KEYWORDS = {
    "ChatGPT":          ["chatgpt", "챗gpt", "챗지피티", "chat gpt", "gpt-4", "gpt4"],
    "Midjourney":       ["midjourney", "미드저니"],
    "Gemini":           ["gemini", "제미나이", "제미니"],
    "나노바나나":        ["나노바나나", "nanobanana", "nano banana"],
    "Dzine":            ["dzine"],
    "Kling AI":         ["kling", "클링"],
    "Google AI Studio": ["google ai studio", "구글 ai studio", "ai studio"],
    "Suno":             ["suno", "수노"],
    "KREA":             ["krea", "크레아"],
    "Weavy":            ["weavy"],
    "Claude":           ["claude", "클로드", "claude code"],
    "Higgsfield":       ["higgsfield"],
    "FLUX":             ["flux", "플럭스"],
    "Whisk":            ["whisk"],
    "Veo":              ["veo"],
    "Seedance":         ["seedance"],
    "Dreamina":         ["dreamina"],
    "위비":             ["위비"],
    "Upscayl":          ["upscayl"],
    "Grok":             ["grok"],
    "ElevenLabs":       ["elevenlabs", "일레븐랩스", "11labs"],
    "ComfyUI":          ["comfyui", "컴피ui"],
    "Tripo 3D":         ["tripo"],
    "Sora":             ["sora"],
    "Segment Anything": ["segment anything"],
    "Google Flow":      ["google flow"],
    "AI 이미지":        ["ai 이미지", "ai이미지"],
}


# ─────────────────────────────────────────────
# Confluence API 헬퍼
# ─────────────────────────────────────────────
def make_auth_header():
    creds = b64encode(f"{CONFLUENCE_EMAIL}:{CONFLUENCE_TOKEN}".encode()).decode()
    return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

def api_get(path, params=None):
    url = f"{CONFLUENCE_BASE}{path}"
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers=make_auth_header())
    try:
        with urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except HTTPError as e:
        print(f"  [HTTP {e.code}] {url}")
        return None

def fetch_all_pages(space_key, label="ArtCraft"):
    """스페이스에서 ArtCraft 레이블/제목 페이지를 CQL로 전체 수집."""
    pages = []
    start = 0
    limit = 50
    cql = (
        f'space = "{space_key}" AND '
        f'(title ~ "ArtCraft" OR title ~ "Art Craft" OR title ~ "AID TF" OR title ~ "TechCraft") '
        f'AND type = page ORDER BY lastmodified DESC'
    )
    while True:
        data = api_get("/rest/api/content/search", {
            "cql": cql,
            "limit": limit,
            "start": start,
            "expand": "history.createdBy,version,metadata.properties.likes",
        })
        if not data or not data.get("results"):
            break
        pages.extend(data["results"])
        if start + limit >= data.get("totalSize", 0):
            break
        start += limit
        time.sleep(0.2)  # rate limit 방지
    return pages

def fetch_page_body(page_id):
    """페이지 본문(plain text) 가져오기."""
    data = api_get(f"/rest/api/content/{page_id}", {
        "expand": "body.export_view,version",
    })
    if not data:
        return ""
    body = data.get("body", {}).get("export_view", {}).get("value", "")
    # HTML 태그 제거
    body = re.sub(r'<[^>]+>', ' ', body)
    body = re.sub(r'&[a-z]+;', ' ', body)
    return body.lower()

def get_views(page_id):
    """조회수 가져오기."""
    data = api_get(f"/rest/api/content/{page_id}/history/latest/details", {
        "expand": "views",
    })
    if data:
        return data.get("views", {}).get("count", 0)
    return 0


# ─────────────────────────────────────────────
# 메타데이터 추출
# ─────────────────────────────────────────────
def extract_types(text):
    """본문 텍스트에서 작업 유형 추출."""
    found = []
    text_lower = text.lower()
    for type_key, keywords in TYPE_KEYWORDS.items():
        for kw in keywords:
            if re.search(kw, text_lower):
                found.append(type_key)
                break
    # 중복 제거 및 정렬
    seen = set()
    result = []
    for t in found:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result if result else ["R&D·비교"]  # 기본값

def extract_tools(text):
    """본문 텍스트에서 사용 툴 추출."""
    found = []
    text_lower = text.lower()
    for tool_name, keywords in TOOL_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                found.append(tool_name)
                break
    seen = set()
    result = []
    for t in found:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result

def extract_summary(body_text, max_len=150):
    """본문에서 요약 추출 (앞 150자)."""
    # 줄바꿈/공백 정리
    text = re.sub(r'\s+', ' ', body_text).strip()
    return text[:max_len]

def extract_author(page):
    """작성자 이름 추출."""
    try:
        return page["history"]["createdBy"]["displayName"]
    except:
        return ""

def extract_date(page):
    """생성일 추출 (YYYY-MM-DD)."""
    try:
        dt = page["history"]["createdDate"][:10]
        return dt
    except:
        return datetime.now().strftime("%Y-%m-%d")


# ─────────────────────────────────────────────
# 메인 처리
# ─────────────────────────────────────────────
def build_pages_array():
    all_pages = []
    seen_urls = set()

    for space_key, team in SPACE_TEAM.items():
        print(f"\n[{team}] space={space_key} 수집 중...")
        pages = fetch_all_pages(space_key)
        print(f"  → {len(pages)}개 발견")

        for page in pages:
            url = f"https://neowiz.atlassian.net/wiki/spaces/{space_key}/pages/{page['id']}/{page.get('title','').replace(' ','+')}"
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # 본문 가져오기 (types/tools 추출용)
            print(f"  파싱: {page['title'][:50]}")
            body = fetch_page_body(page["id"])
            title_lower = page["title"].lower()
            full_text = title_lower + " " + body

            types = extract_types(full_text)
            tools = extract_tools(full_text)
            author = extract_author(page)
            date = extract_date(page)
            summary = extract_summary(body)
            views = get_views(page["id"])

            all_pages.append({
                "team": team,
                "types": types,
                "tools": tools,
                "views": views,
                "title": page["title"],
                "url": f"https://neowiz.atlassian.net/wiki/spaces/{space_key}/pages/{page['id']}",
                "space": space_key,
                "date": date,
                "author": author,
                "summary": summary,
            })
            time.sleep(0.15)  # rate limit

    return all_pages

def pages_to_js(pages):
    """Python 리스트를 JS PAGES 배열 문자열로 변환."""
    def escape(s):
        return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", "")

    lines = []
    for p in pages:
        types_js = "[" + ",".join(f'"{t}"' for t in p["types"]) + "]"
        tools_js = "[" + ",".join(f'"{t}"' for t in p["tools"]) + "]"
        line = (
            f'  {{team:"{escape(p["team"])}",types:{types_js},tools:{tools_js},'
            f'views:{p["views"]},title:"{escape(p["title"])}",'
            f'url:"{escape(p["url"])}",space:"{p["space"]}",'
            f'date:"{p["date"]}",author:"{escape(p["author"])}",'
            f'summary:"{escape(p["summary"])}"}}'
        )
        lines.append(line)
    return "const PAGES=[\n" + ",\n".join(lines) + "\n];"

def update_index_html(pages):
    """index.html의 PAGES 배열을 교체."""
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    new_pages_js = pages_to_js(pages)

    # PAGES 배열 교체
    pattern = r'const PAGES=\[.*?\];'
    new_content = re.sub(pattern, new_pages_js, content, flags=re.DOTALL)

    if new_content == content:
        print("\n⚠️  PAGES 배열을 찾지 못했습니다. index.html 구조를 확인해주세요.")
        return False

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"\n✅ {INDEX_PATH} 업데이트 완료 — {len(pages)}개 페이지")
    return True


# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if not CONFLUENCE_EMAIL or not CONFLUENCE_TOKEN:
        print("❌ 환경변수 CONFLUENCE_EMAIL, CONFLUENCE_TOKEN 을 설정해주세요.")
        print("\n발급 방법:")
        print("  1. https://id.atlassian.com/manage-profile/security/api-tokens 접속")
        print("  2. 'Create API token' 클릭 → 토큰 복사")
        print("\n실행 예시:")
        print("  CONFLUENCE_EMAIL=your@email.com CONFLUENCE_TOKEN=your_token python update_pages.py")
        sys.exit(1)

    print(f"=== ArtCraft 페이지 자동 업데이트 ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===")
    print(f"대상: {INDEX_PATH}")

    pages = build_pages_array()
    print(f"\n총 {len(pages)}개 페이지 수집 완료")

    update_index_html(pages)
