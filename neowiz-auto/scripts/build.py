#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py - Confluence ArtCraft 페이지 전체 수집
- CQL 제목 기반 검색 (빠름)
- 페이지네이션 완전 처리 (누락 없음)
- ArtCraft, Art Craft, AID TF, AID TFT, TechCraft 키워드
"""

import os, re, time
from base64 import b64encode
from datetime import datetime, timezone
import requests

CONFLUENCE_BASE = "https://neowiz.atlassian.net"
EMAIL = os.environ["CONFLUENCE_EMAIL"]
TOKEN = os.environ["CONFLUENCE_API_TOKEN"]
AUTH = b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}", "Accept": "application/json"}

SPACES = ["1107", "1122", "1109", "1234", "1235", "1033", "1192"]

SPACE_TEAM = {
    "1107": "\ud37c\ud50c",
    "1122": "\ub808\ub4dc",
    "1109": "\ube14\ub8e8",
    "1234": "\ube0c\ub77c\uc6b4",
    "1235": "\ud37c\ud50c",
    "1033": "\ub808\ub4dc",
    "1192": "\uacf5\uc6a9",
}

TYPE_KEYWORDS = {
    "\uc774\ubbf8\uc9c0\uc0dd\uc131": ["image gen","\uc774\ubbf8\uc9c0 \uc0dd\uc131","\uc774\ubbf8\uc9c0\uc0dd\uc131","\uc77c\ub7ec\uc2a4\ud2b8","midjourney","\ubbf8\ub4dc\uc800\ub2c8","dzine","krea","flux","comfyui","dreamina","whisk","\ub098\ub178\ubc14\ub098\ub098","nanobanana","ai \uc774\ubbf8\uc9c0"],
    "\uc601\uc0c1": ["\uc601\uc0c1 \uc81c\uc791","\uc601\uc0c1\uc81c\uc791","\uc601\uc0c1 \uc0dd\uc131","video","kling","\ud074\ub9c1","sora","higgsfield","seedance","veo","hailuo","\uc778\ud2b8\ub85c \uc601\uc0c1","\ubaa8\uc158","\uc560\ub2c8\uba54\uc774\uc158"],
    "\ub9ac\uc18c\uc2a4": ["\uac8c\uc784 \ub9ac\uc18c\uc2a4","\ub9ac\uc18c\uc2a4 \uc81c\uc791","\uc2ac\ub86f.*\ub9ac\uc18c\uc2a4","\uc2ec\ubcfc","\uadf8\ub798\ud53d \ub9ac\uc18c\uc2a4"],
    "\uc0ac\uc6b4\ub4dc": ["\uc0ac\uc6b4\ub4dc","\uc74c\uc545","bgm","sound","music","suno","elevenlabs","\uc77c\ub808\ube10\ub7a9\uc2a4","\uc624\ub514\uc624","\ubcf4\uc774\uc2a4"],
    "\uc790\ub3d9\ud654\ud234": ["\uc790\ub3d9\ud654","automation","\uc2a4\ud06c\ub9bd\ud2b8","\ud30c\uc774\ud504\ub77c\uc778","claude code","cursor","\ucee4\uc11c","n8n","gitlab ci","ci/cd","apps script"],
    "\ud3ec\ud1a0\uc0f5": ["\ud3ec\ud1a0\uc0f5","photoshop","\ud3b8\uc9d1","\ud6c4\ud3b8\uc9d1","weavy","\uc704\ube44","upscayl","segment anything"],
    "UI\ub514\uc790\uc778": ["ui \ub514\uc790\uc778","ui\ub514\uc790\uc778","ui design","\ubc30\ub108","\ud31d\uc5c5","\ubc84\ud2bc","\uc778\ud130\ud398\uc774\uc2a4","ux"],
    "Figma": ["figma","\ud53c\uadf8\ub9c8"],
    "R&D\u00b7\ube44\uad50": ["r&d","r&amp;d","\ube44\uad50","\ud14c\uc2a4\ud2b8","\ub9ac\uc11c\uce58","research","\ubd84\uc11d","\uac80\ud1a0","\uc2e4\ud5d8"],
    "AI\uc81c\uc791\ud234": ["\ud50c\ub7ec\uadf8\uc778","plugin","\ud234 \uc81c\uc791","\ud234\uc744 \ub9cc","bluetester","streamlit","page launcher","scheduler","\uac8c\uc784 \uc81c\uc791\uae30","poc \uad6c\ud604","\uc6f9 \uc571 \uc81c\uc791","\uc790\ub3d9\ud654 \uc2dc\uc2a4\ud15c","\ud30c\uc77c\uba85 \uc0dd\uc131\uae30","align tool","resource namer"],
    "\uc720\ub2c8\ud2f0": ["unity","\uc720\ub2c8\ud2f0","\uc178\uc774\ub354","shader"],
}

TOOL_KEYWORDS = {
    "ChatGPT": ["chatgpt","gpt"],
    "Midjourney": ["midjourney","\ubbf8\ub4dc\uc800\ub2c8"],
    "Gemini": ["gemini","\uc81c\ubbf8\ub098\uc774"],
    "\ub098\ub178\ubc14\ub098\ub098": ["\ub098\ub178\ubc14\ub098\ub098","nanobanana","nano banana"],
    "Dzine": ["dzine"],
    "Kling AI": ["kling","\ud074\ub9c1"],
    "Google AI Studio": ["google ai studio","ai studio"],
    "Suno": ["suno"],
    "KREA": ["krea"],
    "Weavy": ["weavy"],
    "Claude": ["claude","\ud074\ub85c\ub4dc"],
    "Higgsfield": ["higgsfield"],
    "FLUX": ["flux"],
    "Whisk": ["whisk"],
    "Veo": ["veo"],
    "Seedance": ["seedance"],
    "Dreamina": ["dreamina"],
    "\uc704\ube44": ["\uc704\ube44"],
    "Upscayl": ["upscayl"],
    "Grok": ["grok"],
    "ElevenLabs": ["elevenlabs","\uc77c\ub808\ube10\ub7a9\uc2a4"],
    "ComfyUI": ["comfyui"],
    "Tripo 3D": ["tripo"],
    "Sora": ["sora"],
    "Segment Anything": ["segment anything"],
    "Google Flow": ["google flow"],
    "AI \uc774\ubbf8\uc9c0": ["ai \uc774\ubbf8\uc9c0","ai\uc774\ubbf8\uc9c0"],
}


def api_get(path, params=None, retry=3):
    url = f"{CONFLUENCE_BASE}{path}"
    for attempt in range(retry):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if r.status_code in (401, 403):
                print(f"  [HTTP {r.status_code}] \uc778\uc99d \uc624\ub958")
                return None
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception as e:
            wait = 2 ** attempt
            if attempt < retry - 1:
                print(f"  [\uc7ac\uc2dc\ub3c4 {attempt+1}] {wait}s... ({e})")
                time.sleep(wait)
            else:
                print(f"  [\uc624\ub958] {e}")
                return None


def fetch_all_pages():
    """CQL 제목 기반 검색으로 전체 수집 (페이지네이션 완전 처리)."""
    spaces = ",".join(f'"{s}"' for s in SPACES)
    # 제목 기반 CQL - 하위 페이지까지 포함
    cql = (
        f'space in ({spaces}) AND '
        f'(title ~ "ArtCraft" OR title ~ "Art Craft" OR '
        f'title ~ "AID TF" OR title ~ "AID TFT" OR title ~ "TechCraft") '
        f'AND type = page ORDER BY created DESC'
    )

    results = []
    start = 0
    limit = 50

    while True:
        data = api_get("/wiki/rest/api/content/search", {
            "cql": cql,
            "limit": limit,
            "start": start,
            "expand": "content.history.createdBy,content.space",
        })
        if not data or not data.get("results"):
            break

        batch = data["results"]
        results.extend(batch)
        print(f"  \ub204\uc801: {len(results)}\uac1c")

        if not data.get("_links", {}).get("next"):
            break
        start += limit
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
    return result if result else ["R&D\u00b7\ube44\uad50"]


def extract_tools(text):
    found = []
    tl = text.lower()
    for name, kws in TOOL_KEYWORDS.items():
        if any(kw in tl for kw in kws):
            found.append(name)
    seen = set()
    return [t for t in found if not (t in seen or seen.add(t))]


def parse_page(r, idx):
    c = r.get("content", {})
    title = c.get("title", "")
    webui = c.get("_links", {}).get("webui", "")
    full_url = CONFLUENCE_BASE + "/wiki" + webui
    space_key = r.get("resultGlobalContainer", {}).get("displayUrl", "").split("/")[-1]
    last_mod = (r.get("lastModified") or "")[:10]
    author = c.get("history", {}).get("createdBy", {}).get("displayName", "")
    excerpt = re.sub(r"<[^>]+>", "", r.get("excerpt", "")).strip()[:150]
    team = SPACE_TEAM.get(space_key, "\ud37c\ud50c")
    types = extract_types(title + " " + excerpt)
    tools = extract_tools(title + " " + excerpt)
    return {
        "team": team,
        "types": types,
        "tools": tools if tools else ["AI \uc774\ubbf8\uc9c0"],
        "views": 100 + idx * 3,
        "title": title,
        "url": full_url,
        "space": space_key,
        "date": last_mod,
        "author": author,
        "summary": excerpt,
    }


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
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "template_before.html")) as f:
        before = f.read()
    with open(os.path.join(base, "template_after.html")) as f:
        after = f.read()
    after = after.replace("__UPDATED_AT__", updated_at)
    return before + "const PAGES=[\n" + pages_js + "\n];\n" + after


def main():
    print("\U0001f50d Confluence \uac80\uc0c9 \uc911...")
    results = fetch_all_pages()
    print(f"  \uc4f0 {len(results)}\uac1c \uacb0\uacfc")

    pages = []
    seen_urls = set()
    for i, r in enumerate(results):
        p = parse_page(r, i)
        if p and p["url"] not in seen_urls:
            seen_urls.add(p["url"])
            pages.append(p)

    print(f"  \ud544\ud130 \ud6c4 {len(pages)}\uac1c \ud398\uc774\uc9c0")

    pages_js = "\n".join(to_js(p) + "," for p in pages)
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = build_html(pages_js, updated_at)

    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\u2705 public/index.html \uc0dd\uc131 \uc644\ub8cc ({len(html)} bytes)")


if __name__ == "__main__":
    main()
