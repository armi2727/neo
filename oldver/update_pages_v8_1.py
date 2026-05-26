#!/usr/bin/env python3
"""
update_pages_v8.py — 누락 없는 완전 수집 버전

PowerShell 실행:
    $env:CONFLUENCE_EMAIL='이메일@neowiz.com'
    $env:CONFLUENCE_TOKEN='토큰'
    $env:INDEX_PATH='index.html'
    python update_pages_v8.py
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

SPACE_TEAM = {
    "1107": "퍼플",
    "1122": "레드",
    "1109": "블루",
    "1234": "브라운",
    "1235": "퍼플",
    "1033": "레드",
    "1192": "공용",
}

TITLE_KEYWORDS = ["artcraft", "art craft", "aid tf", "aid tft", "techcraft"]

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
# API
# ─────────────────────────────────────────────
def make_headers():
    creds = b64encode(f"{CONFLUENCE_EMAIL}:{CONFLUENCE_TOKEN}".encode()).decode()
    return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

def api_get(path, params=None, max_retry=5):
    """실패 시 최대 max_retry번 재시도. 성공하면 데이터 반환, 최종 실패 시 None 반환."""
    url = f"{CONFLUENCE_BASE}{path}"
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers=make_headers())
    for attempt in range(max_retry):
        try:
            with urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except HTTPError as e:
            if e.code == 404:
                return None  # 삭제된 페이지 — 조용히 무시
            print(f"  [HTTP {e.code}] {path}")
            return None
        except Exception as e:
            wait = 2 ** attempt  # 1, 2, 4, 8, 16초 지수 백오프
            if attempt < max_retry - 1:
                print(f"  [재시도 {attempt+1}/{max_retry}] {wait}초 대기... ({e})")
                time.sleep(wait)
            else:
                return None  # 최종 실패 → None 반환 (누락으로 기록)
    return None

# ─────────────────────────────────────────────
# 1단계: 전체 페이지 목록 수집 (body 없이)
# ─────────────────────────────────────────────
def fetch_space_pages(space_key):
    """스페이스 전체 페이지 목록을 끝까지 수집."""
    pages = []
    path = f"/rest/api/space/{space_key}/content/page"
    params = {
        "limit": 100,
        "expand": "history.createdBy,version",
        "depth": "all",
        "orderby": "history.createdDate desc",
    }
    while True:
        data = api_get(path, params if "?" not in path else None)
        if not data:
            break
        pages.extend(data.get("results", []))
        next_link = data.get("_links", {}).get("next", "")
        if next_link:
            path = next_link.replace(CONFLUENCE_BASE, "").replace("/wiki", "")
            params = None
        else:
            break
        time.sleep(0.3)
    return pages

# ─────────────────────────────────────────────
# 2단계: 본문 수집 (실패 시 무한 재시도)
# ─────────────────────────────────────────────
def fetch_page_summary(page_id):
    """페이지 본문 앞부분 수집. export_view 사용 (텍스트 전용, 가벼움)."""
    data = api_get(f"/rest/api/content/{page_id}", {
        "expand": "body.export_view",
    })
    if not data:
        return None  # 실패 신호
    raw = data.get("body", {}).get("export_view", {}).get("value", "")
    text = re.sub(r'<[^>]+>', ' ', raw)
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:300]

def fetch_summaries_with_retry(page_ids):
    """
    실패한 페이지를 모아서 전부 성공할 때까지 무한 재시도.
    단 한 페이지도 누락 없이 수집.
    """
    results = {}
    remaining = list(page_ids)
    round_num = 0

    while remaining:
        round_num += 1
        failed = []
        print(f"  → 본문 수집 중... ({len(remaining)}개, {round_num}라운드)")

        for i, page_id in enumerate(remaining):
            summary = fetch_page_summary(page_id)
            if summary is None:
                failed.append(page_id)
            else:
                results[page_id] = summary

            if (i + 1) % 50 == 0:
                print(f"     {i+1}/{len(remaining)} 처리 (실패: {len(failed)}개)")
            time.sleep(0.3)

        if failed:
            wait = min(10 * round_num, 60)  # 최대 60초까지 대기 증가
            print(f"  → {round_num}라운드: 성공 {len(remaining)-len(failed)}개, 실패 {len(failed)}개 → {wait}초 후 재시도")
            remaining = failed
            time.sleep(wait)
        else:
            print(f"  → 전체 {len(page_ids)}개 수집 완료! (누락 없음)")
            break

    return results

# ─────────────────────────────────────────────
# 메타데이터 추출
# ─────────────────────────────────────────────
def is_artcraft_page(title):
    t = title.lower()
    return any(kw in t for kw in TITLE_KEYWORDS)

def extract_types(text):
    found = []
    tl = text.lower()
    for key, kws in TYPE_KEYWORDS.items():
        if any(re.search(kw, tl) for kw in kws):
            found.append(key)
    seen = set()
    result = [t for t in found if not (t in seen or seen.add(t))]
    return result if result else ["R&D·비교"]

def extract_tools(text):
    found = []
    tl = text.lower()
    for name, kws in TOOL_KEYWORDS.items():
        if any(kw in tl for kw in kws):
            found.append(name)
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
        print(f"\n[{team}] space={space_key} 수집 중...")

        # 1단계: 전체 목록 (빠름)
        space_pages = fetch_space_pages(space_key)
        artcraft_pages = [p for p in space_pages if is_artcraft_page(p.get("title", ""))]
        
        # 중복 제거
        new_pages = [p for p in artcraft_pages if p["id"] not in seen_ids]
        for p in new_pages:
            seen_ids.add(p["id"])
        
        print(f"  → 전체 {len(space_pages)}개 중 ArtCraft {len(new_pages)}개 발견")

        if not new_pages:
            continue

        # 2단계: 본문 수집 (누락 없이)
        page_ids = [p["id"] for p in new_pages]
        summaries = fetch_summaries_with_retry(page_ids)

        # 데이터 조립
        for page in new_pages:
            page_id = page["id"]
            title   = page.get("title", "")
            summary = summaries.get(page_id, "")
            full_text = title + " " + summary

            all_pages.append({
                "team":    team,
                "types":   extract_types(full_text),
                "tools":   extract_tools(full_text),
                "views":   0,
                "title":   title,
                "url":     f"https://neowiz.atlassian.net/wiki/spaces/{space_key}/pages/{page_id}",
                "space":   space_key,
                "date":    extract_date(page),
                "author":  extract_author(page),
                "summary": summary[:200],
            })

        print(f"  → {len(new_pages)}개 완료")

    all_pages.sort(key=lambda p: p["date"], reverse=True)
    return all_pages

def pages_to_js(pages):
    def esc(s):
        return str(s).replace("\\","\\\\").replace('"','\\"').replace("\n"," ").replace("\r","")
    lines = []
    for p in pages:
        types_js = "[" + ",".join(f'"{t}"' for t in p["types"]) + "]"
        tools_js = "[" + ",".join(f'"{t}"' for t in p["tools"]) + "]"
        lines.append(
            f'  {{team:"{esc(p["team"])}",types:{types_js},tools:{tools_js},'
            f'views:{p["views"]},title:"{esc(p["title"])}",'
            f'url:"{esc(p["url"])}",space:"{p["space"]}",'
            f'date:"{p["date"]}",author:"{esc(p["author"])}",'
            f'summary:"{esc(p["summary"])}"}}'
        )
    return "const PAGES=[\n" + ",\n".join(lines) + "\n];"

def update_index_html(pages):
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    new_js = pages_to_js(pages)
    new_content = re.sub(r'const PAGES=\[.*?\];', new_js, content, flags=re.DOTALL)
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
