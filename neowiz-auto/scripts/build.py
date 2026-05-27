#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, time
from base64 import b64encode
from datetime import datetime, timezone
import requests

CONFLUENCE_BASE = "https://neowiz.atlassian.net"
EMAIL = os.environ.get("CONFLUENCE_EMAIL", "")
TOKEN = os.environ.get("CONFLUENCE_API_TOKEN", "")

SPACE_TEAM = {
    "1107": "퍼플",
    "1122": "레드",
    "1109": "블루",
    "1234": "브라운",
    "1235": "퍼플",
    "1033": "레드",
    "1192": "공용",
}

TYPE_KEYWORDS = {
    "이미지생성": ["image gen","이미지 생성","이미지생성","일러스트","midjourney","미드저니","dzine","krea","flux","comfyui","dreamina","whisk","나노바나나","nanobanana","ai 이미지"],
    "영상": ["영상 제작","영상제작","video","kling","클링","sora","higgsfield","seedance","veo","hailuo","모션","애니메이션"],
    "리소스": ["게임 리소스","리소스 제작","슬롯.*리소스","심볼","그래픽 리소스"],
    "사운드": ["사운드","음악","bgm","sound","music","suno","elevenlabs","오디오","보이스"],
    "자동화툴": ["자동화","automation","스크립트","claude code","cursor","커서","n8n","gitlab ci","ci/cd"],
    "포토샵": ["포토샵","photoshop","편집","후편집","weavy","위비","upscayl"],
    "UI디자인": ["ui 디자인","ui design","배너","팝업","버튼","ux"],
    "Figma": ["figma","피그마"],
    "R&D·비교": ["r&d","비교","테스트","리서치","research","분석","검토"],
    "AI제작툴": ["플러그인","plugin","툴 제작","bluetester","streamlit","page launcher","scheduler","게임 제작기","align tool","resource namer"],
    "유니티": ["unity","유니티","shader"],
}

TOOL_KEYWORDS = {
    "ChatGPT": ["chatgpt","gpt"],
    "Midjourney": ["midjourney","미드저니"],
    "Gemini": ["gemini","제미나이"],
    "나노바나나": ["나노바나나","nanobanana","nano banana"],
    "Dzine": ["dzine"],
    "Kling AI": ["kling","클링"],
    "Google AI Studio": ["google ai studio","ai studio"],
    "Suno": ["suno"],
    "KREA": ["krea"],
    "Weavy": ["weavy"],
    "Claude": ["claude","클로드"],
    "Higgsfield": ["higgsfield"],
    "FLUX": ["flux"],
    "Whisk": ["whisk"],
    "Veo": ["veo"],
    "Seedance": ["seedance"],
    "Dreamina": ["dreamina"],
    "위비": ["위비"],
    "Upscayl": ["upscayl"],
    "Grok": ["grok"],
    "ElevenLabs": ["elevenlabs"],
    "ComfyUI": ["comfyui"],
    "Tripo 3D": ["tripo"],
    "Sora": ["sora"],
    "Google Flow": ["google flow"],
    "AI 이미지": ["ai 이미지","ai이미지"],
}

def get_headers():
    auth = b64encode(f"{EMAIL}:{TOKEN}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {auth}", "Accept": "application/json"}

def api_get(url, params=None, retry=3):
    for attempt in range(retry):
        try:
            r = requests.get(url, headers=get_headers(), params=params, timeout=15)
            if r.status_code == 401:
                print("  [HTTP 401] 인증 오류")
                return None
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt < retry - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  [오류] {e}")
                return None

def fetch_all_pages():
    spaces = ",".join(f'"{s}"' for s in SPACE_TEAM.keys())
    cql = (
        f'space in ({spaces}) AND '
        f'(title ~ "ArtCraft" OR title ~ "Art Craft" OR '
        f'title ~ "AID TF" OR title ~ "AID TFT" OR title ~ "TechCraft") '
        f'AND type = page ORDER BY created DESC'
    )
    base_url = f"{CONFLUENCE_BASE}/wiki/rest/api/search"
    results = []
    params = {"cql": cql, "limit": 50}
    url = base_url

    while True:
        data = api_get(url, params)
        if not data:
            break

        batch = data.get("results", [])
        if not batch:
            break

        results.extend(batch)
        total = data.get("totalSize", len(results))
        print(f"  누적: {len(results)}/{total}개")

        next_path = data.get("_links", {}).get("next", "")
        if not next_path:
            break

        url = CONFLUENCE_BASE + "/wiki" + next_path
        params = None

        time.sleep(0.3)

    return results

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

def esc(s):
    return (s or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", "")

def to_js(e):
    t = '","'.join(e["types"])
    tl = '","'.join(e["tools"])
    return (
        f'  {{team:"{esc(e["team"])}",types:["{t}"],tools:["{tl}"],'
        f'views:{e["views"]},title:"{esc(e["title"])}",'
        f'url:"{esc(e["url"])}",space:"{esc(e["space"])}",'
        f'date:"{esc(e["date"])}",author:"{esc(e["author"])}",'
        f'summary:"{esc(e["summary"])}"}}'
    )

def build_html(pages_js, updated_at):
    # build.py 파일 위치 기준으로 상위의 상위 폴더에 있는 index.html 절대 경로 탐색
    base = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base, "..", "..", "index.html")
    
    with open(index_path, encoding="utf-8") as f:
        content = f.read()
    import re as _re
    new_pages = "const PAGES=[\n" + pages_js + "\n];"
    content = _re.sub(r'const PAGES=\[.*?\];', new_pages, content, flags=_re.DOTALL)
    
    # 수정된 HTML 내용과 함께, 읽어왔던 경로(index_path)를 함께 반환합니다.
    return content, index_path

def main():
    print("Confluence 검색 중...")
    print(f"  EMAIL: {EMAIL[:4]}..." if EMAIL else "  EMAIL: 비어있음")
    print(f"  TOKEN: {TOKEN[:4]}..." if TOKEN else "  TOKEN: 비어있음")

    raw = fetch_all_pages()
    print(f"  수집: {len(raw)}개")

    if raw:
        r0 = raw[0]
        c0 = r0.get("content", {})
        print(f"  DEBUG r0.keys: {list(r0.keys())[:6]}")
        print(f"  DEBUG content.id: {c0.get('id')}")
        print(f"  DEBUG r0.url: {r0.get('url')}")
        print(f"  DEBUG content._links.webui: {c0.get('_links', {}).get('webui')}")

    pages = []
    seen = set()

    for i, r in enumerate(raw):
        content = r.get("content", {})
        cid = str(r.get("id") or content.get("id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)

        title = r.get("title", "") or content.get("title", "")
        excerpt = re.sub(r"<[^>]+>", "", r.get("excerpt", "")).strip()[:200]
        last_mod = (r.get("lastModified") or "")[:10]

        page_path = r.get("url", "") or content.get("_links", {}).get("webui", "")
        full_url = CONFLUENCE_BASE + "/wiki" + page_path if page_path else ""

        display_url = r.get("resultGlobalContainer", {}).get("displayUrl", "")
        space_key = display_url.strip("/").split("/")[-1] if display_url else ""
        if not space_key and page_path:
            parts = page_path.split("/")
            if "spaces" in parts:
                idx2 = parts.index("spaces")
                if idx2 + 1 < len(parts):
                    space_key = parts[idx2 + 1]

        team = SPACE_TEAM.get(space_key, "퍼플")

        author = ""
        history = content.get("history", {})
        if history:
            author = history.get("createdBy", {}).get("displayName", "")

        full_text = title + " " + excerpt
        types = extract_types(full_text)
        tools = extract_tools(full_text)

        pages.append({
            "team": team,
            "types": types,
            "tools": tools if tools else ["AI 이미지"],
            "views": 100 + i * 3,
            "title": title,
            "url": full_url,
            "space": space_key,
            "date": last_mod,
            "author": author,
            "summary": excerpt,
        })

    print(f"  페이지: {len(pages)}개")

    pages_js = "\n".join(to_js(p) + "," for p in pages)
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    # [수정 적용] 읽어온 경로 그대로 덮어쓰기 위해 두 인자를 반환받습니다.
    html, target_path = build_html(pages_js, updated_at)
    
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"index.html 업데이트 완료! -> {target_path} ({len(html)} bytes)")

if __name__ == "__main__":
    main()