#!/usr/bin/env python3
"""
update_pages.py — Confluence ArtCraft 페이지 전체 수집 (24~26년)

PowerShell 실행:
    $env:CONFLUENCE_EMAIL='이메일@neowiz.com'
    $env:CONFLUENCE_TOKEN='토큰'
    $env:INDEX_PATH='index.html'
    python update_pages.py
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

# ArtCraft 관련 제목 키워드
TITLE_KEYWORDS = ["artcraft", "art craft", "aid tf", "techcraft"]

# 작업 유형 키워드
TYPE_KEYWORDS = {
    "이미지생성": ["이미지 생성","이미지생성","image gen","일러스트","midjourney","미드저니","dzine","krea","flux","comfyui","dreamina","whisk","나노바나나","nanobanana","ai 이미지","gemini.*이미지","chatgpt.*이미지"],
    "영상":       ["영상 제작","영상제작","영상 생성","video","kling","클링","sora","higgsfield","seedance","veo","hailuo","인트로 영상","모션","애니메이션"],
    "리소스":     ["게임 리소스","리소스 제작","리소스 생성","슬롯.*리소스","심볼","그래픽 리소스"],
    "사운드":     ["사운드","음악","bgm","sound","music","suno","elevenlabs","일레븐랩스","오디오","보이스"],
    "자동화툴":   ["자동화","automation","스크립트","파이프라인","claude code","cursor","커서","n8n","gitlab ci","ci/cd","apps script","자동 생성"],
    "포토샵":     ["포토샵","photoshop","편집","후편집","weavy","위비","upscayl","segment anything"],
    "UI디자인":   ["ui 디자인","ui디자인","ui design","배너","팝업","버튼","인터페이스","ux"],
    "Figma":      ["figma","피그마"],
    "R&D·비교":   ["r&d","r&amp;d","비교","테스트","리서치","research","분석","검토","실험"],
    "AI제작툴":   ["플러그인","plugin","툴 제작","툴을 만","내부 도구","내부도구","bluetester","streamlit","page launcher","scheduler","게임 제작기","poc 구현","웹 앱 제작","자동화 시스템","파일명 생성기","align tool","resource namer"],
    "유니티":     ["unity","유니티","쉐이더","shader"],
}

# 툴 키워드
TOOL_KEYWORDS = {
    "ChatGPT":          ["chatgpt","챗gpt","챗지피티"],
    "Midjourney":       ["midjourney","미드저니"],
    "Gemini":           ["gemini","제미나이","제미니"],
    "나노바나나":        ["나노바나나","nanobanana","nano banana"],
    "Dzine":            ["dzine"],
    "Kling AI":         ["kling","클링"],
    "Google AI Studio": ["google ai studio","구글 ai studio","ai studio"],
    "Suno":             ["suno","수노"],
    "KREA":             ["krea"],
    "Weavy":            ["weavy"],
    "Claude":           ["claude","클로드"],
    "Higgsfield":       ["higgsfield"],
    "FLUX":             ["flux"],
    "Whisk":            ["whisk"],
    "Veo":              ["veo"],
    "Seedance":         ["seedance"],
    "Dreamina":         ["dreamina"],
    "위비":             ["위비"],
    "Upscayl":          ["upscayl"],
    "Grok":             ["grok"],
    "ElevenLabs":       ["elevenlabs","일레븐랩스","11labs"],
    "ComfyUI":          ["comfyui"],
    "Tripo 3D":         ["tripo"],
    "Sora":             ["sora"],
    "Segment Anything": ["segment anything"],
    "Google Flow":      ["google flow"],
    "AI 이미지":        ["ai 이미지","ai이미지"],
}


# ─────────────────────────────────────────────
# Confluence API
# ─────────────────────────────────────────────
def make_headers():
    creds = b64encode(f"{CONFLUENCE_EMAIL}:{CONFLUENCE_TOKEN}".encode()).decode()
    return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

def api_get(path, params=None):
    url = f"{CONFLUENCE_BASE}{path}"
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers=make_headers())
    try:
        with urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except HTTPError as e:
        # 404는 삭제된 페이지 — 조용히 무시
        if e.code != 404:
            print(f"  [HTTP {e.code}] {path}")
        return None
    except Exception as e:
        print(f"  [오류] {e}")
        return None

def fetch_space_pages(space_key):
    """
    스페이스의 모든 페이지를 _links.next 기반으로 끝까지 수집.
    CQL 검색 대신 /rest/api/space/{key}/content 사용 → totalSize 문제 없음.
    """
    pages = []
    path = f"/rest/api/space/{space_key}/content/page"
    params = {
        "limit": 100,
        "expand": "history.createdBy,version",
        "depth": "all",
    }

    while path:
        data = api_get(path, params if "?" not in path else None)
        if not data:
            break
        results = data.get("results", [])
        pages.extend(results)

        # 다음 페이지 링크 확인
        next_link = data.get("_links", {}).get("next", "")
        if next_link:
            # next 링크는 /wiki/rest/api/... 형태 — base 제거
            path = next_link.replace(CONFLUENCE_BASE, "").replace("/wiki", "")
            params = None  # params는 next URL에 이미 포함됨
        else:
            break
        time.sleep(0.1)

    return pages

def is_artcraft_page(title):
    """제목에 ArtCraft 관련 키워드가 있는지 확인."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in TITLE_KEYWORDS)


# ─────────────────────────────────────────────
# 메타데이터 추출
# ─────────────────────────────────────────────
def extract_types(text):
    found = []
    text_lower = text.lower()
    for type_key, keywords in TYPE_KEYWORDS.items():
        for kw in keywords:
            if re.search(kw, text_lower):
                found.append(type_key)
                break
    seen = set()
    result = [t for t in found if not (t in seen or seen.add(t))]
    return result if result else ["R&D·비교"]

def extract_tools(text):
    found = []
    text_lower = text.lower()
    for tool_name, keywords in TOOL_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                found.append(tool_name)
                break
    seen = set()
    return [t for t in found if not (t in seen or seen.add(t))]

def extract_author(page):
    try:
        return page["history"]["createdBy"]["displayName"]
    except:
        return ""

def extract_date(page):
    try:
        return page["history"]["createdDate"][:10]
    except:
        return ""


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
def build_pages_array():
    all_pages = []
    seen_ids = set()

    for space_key, team in SPACE_TEAM.items():
        print(f"\n[{team}] space={space_key} 전체 수집 중...")
        all_space_pages = fetch_space_pages(space_key)
        print(f"  → 전체 {len(all_space_pages)}개 중 ArtCraft 필터링...")

        count = 0
        for page in all_space_pages:
            page_id = page["id"]
            if page_id in seen_ids:
                continue

            title = page.get("title", "")
            if not is_artcraft_page(title):
                continue

            seen_ids.add(page_id)
            page_url = f"https://neowiz.atlassian.net/wiki/spaces/{space_key}/pages/{page_id}"

            # 제목만으로 types/tools 파싱 (빠름, 타임아웃 없음)
            full_text = title
            types   = extract_types(full_text)
            tools   = extract_tools(full_text)
            author  = extract_author(page)
            date    = extract_date(page)

            all_pages.append({
                "team":    team,
                "types":   types,
                "tools":   tools,
                "views":   0,
                "title":   title,
                "url":     page_url,
                "space":   space_key,
                "date":    date,
                "author":  author,
                "summary": "",
            })
            count += 1

        print(f"  → ArtCraft 페이지 {count}개 추가")

    # 날짜 최신순 정렬
    all_pages.sort(key=lambda p: p["date"], reverse=True)
    return all_pages


def pages_to_js(pages):
    def esc(s):
        return str(s).replace("\\","\\\\").replace('"','\\"').replace("\n"," ").replace("\r","")
    lines = []
    for p in pages:
        types_js = "[" + ",".join(f'"{t}"' for t in p["types"]) + "]"
        tools_js = "[" + ",".join(f'"{t}"' for t in p["tools"]) + "]"
        line = (
            f'  {{team:"{esc(p["team"])}",types:{types_js},tools:{tools_js},'
            f'views:{p["views"]},title:"{esc(p["title"])}",'
            f'url:"{esc(p["url"])}",space:"{p["space"]}",'
            f'date:"{p["date"]}",author:"{esc(p["author"])}",'
            f'summary:"{esc(p["summary"])}"}}'
        )
        lines.append(line)
    return "const PAGES=[\n" + ",\n".join(lines) + "\n];"


def update_index_html(pages):
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    new_pages_js = pages_to_js(pages)
    new_content = re.sub(r'const PAGES=\[.*?\];', new_pages_js, content, flags=re.DOTALL)
    if new_content == content:
        print("\n⚠️  PAGES 배열을 찾지 못했습니다.")
        return False
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"\n✅ {INDEX_PATH} 업데이트 완료 — {len(pages)}개 페이지")
    return True


if __name__ == "__main__":
    if not CONFLUENCE_EMAIL or not CONFLUENCE_TOKEN:
        print("❌ 환경변수 CONFLUENCE_EMAIL, CONFLUENCE_TOKEN 을 설정해주세요.")
        sys.exit(1)

    print(f"=== ArtCraft 페이지 자동 업데이트 ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===")
    print(f"대상: {INDEX_PATH}")

    pages = build_pages_array()
    print(f"\n총 {len(pages)}개 페이지 수집 완료")
    update_index_html(pages)
