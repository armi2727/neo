#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_pages_v9.py - 빠르고 안정적인 버전
- 본문 개별 호출 없음 (타임아웃/멈춤 없음)
- 전체 페이지 목록 수집 + CQL excerpt 조합
- 누락 없이 전체 수집 보장
"""

import os, re, json, time, sys, ssl
from datetime import datetime
from base64 import b64encode
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError

# Windows SSL 인증서 문제 우회
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

CONFLUENCE_BASE  = "https://neowiz.atlassian.net/wiki"
CONFLUENCE_EMAIL = os.environ.get("CONFLUENCE_EMAIL", "")
CONFLUENCE_TOKEN = os.environ.get("CONFLUENCE_TOKEN", "")
INDEX_PATH       = os.environ.get("INDEX_PATH", "./index.html")

SPACE_TEAM = {
    "1107": "purple",
    "1122": "red",
    "1109": "blue",
    "1234": "brown",
    "1235": "purple",
    "1033": "red",
    "1192": "common",
}

SPACE_TEAM_KO = {
    "1107": "purple",
    "1122": "red",
    "1109": "blue",
    "1234": "brown",
    "1235": "purple",
    "1033": "red",
    "1192": "common",
}

TEAM_NAME = {
    "1107": "\ud37c\ud50c",
    "1122": "\ub808\ub4dc",
    "1109": "\ube14\ub8e8",
    "1234": "\ube0c\ub77c\uc6b4",
    "1235": "\ud37c\ud50c",
    "1033": "\ub808\ub4dc",
    "1192": "\uacf5\uc6a9",
}

TITLE_KEYWORDS = ["artcraft", "art craft", "aid tf", "aid tft", "techcraft"]

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
    "ChatGPT":          ["chatgpt","gpt"],
    "Midjourney":       ["midjourney","\ubbf8\ub4dc\uc800\ub2c8"],
    "Gemini":           ["gemini","\uc81c\ubbf8\ub098\uc774"],
    "\ub098\ub178\ubc14\ub098\ub098": ["\ub098\ub178\ubc14\ub098\ub098","nanobanana","nano banana"],
    "Dzine":            ["dzine"],
    "Kling AI":         ["kling","\ud074\ub9c1"],
    "Google AI Studio": ["google ai studio","ai studio"],
    "Suno":             ["suno"],
    "KREA":             ["krea"],
    "Weavy":            ["weavy"],
    "Claude":           ["claude","\ud074\ub85c\ub4dc"],
    "Higgsfield":       ["higgsfield"],
    "FLUX":             ["flux"],
    "Whisk":            ["whisk"],
    "Veo":              ["veo"],
    "Seedance":         ["seedance"],
    "Dreamina":         ["dreamina"],
    "\uc704\ube44":     ["\uc704\ube44"],
    "Upscayl":          ["upscayl"],
    "Grok":             ["grok"],
    "ElevenLabs":       ["elevenlabs","\uc77c\ub808\ube10\ub7a9\uc2a4"],
    "ComfyUI":          ["comfyui"],
    "Tripo 3D":         ["tripo"],
    "Sora":             ["sora"],
    "Segment Anything": ["segment anything"],
    "Google Flow":      ["google flow"],
    "AI \uc774\ubbf8\uc9c0": ["ai \uc774\ubbf8\uc9c0","ai\uc774\ubbf8\uc9c0"],
}


def make_headers():
    creds = b64encode(f"{CONFLUENCE_EMAIL}:{CONFLUENCE_TOKEN}".encode()).decode()
    return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

def api_get(path, params=None, retry=3):
    url = f"{CONFLUENCE_BASE}{path}"
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers=make_headers())
    for attempt in range(retry):
        try:
            with urlopen(req, timeout=20, context=ssl_ctx) as r:
                return json.loads(r.read())
        except HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 401:
                print("  [HTTP 401] token error")
                return None
            print(f"  [HTTP {e.code}] {path}")
            return None
        except Exception as e:
            wait = 2 ** attempt
            if attempt < retry - 1:
                print(f"  [retry {attempt+1}] {wait}s... ({e})")
                time.sleep(wait)
            else:
                return None
    return None

# 1단계: 전체 페이지 목록 (body 없이 빠르게)
def fetch_space_pages(space_key):
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
        time.sleep(0.2)
    return pages

# 2단계: CQL로 excerpt 수집 (페이지네이션 완전 처리)
def fetch_excerpts(space_key):
    excerpts = {}
    start = 0
    limit = 50
    cql = (
        f'space = "{space_key}" AND '
        f'(title ~ "ArtCraft" OR title ~ "Art Craft" OR title ~ "AID TF" OR '
        f'title ~ "AID TFT" OR title ~ "TechCraft") AND type = page'
    )
    while True:
        data = api_get("/rest/api/content/search", {
            "cql": cql, "limit": limit, "start": start,
        })
        if not data or not data.get("results"):
            break
        for item in data["results"]:
            excerpt = item.get("excerpt", "")
            excerpt = re.sub(r'\s+', ' ', excerpt).strip()[:200]
            excerpts[item["id"]] = excerpt
        if not data.get("_links", {}).get("next"):
            break
        start += limit
        time.sleep(0.2)
    return excerpts

def is_artcraft(title):
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
    return result if result else ["R&D\u00b7\ube44\uad50"]

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

def build_pages_array():
    all_pages = []
    seen_ids = set()

    for space_key, _ in SPACE_TEAM.items():
        team = TEAM_NAME[space_key]
        print(f"\n[{team}] space={space_key} ...")

        space_pages = fetch_space_pages(space_key)
        artcraft = [p for p in space_pages if is_artcraft(p.get("title", ""))]
        new_pages = [p for p in artcraft if p["id"] not in seen_ids]
        for p in new_pages:
            seen_ids.add(p["id"])

        print(f"  -> {len(space_pages)}pages, {len(new_pages)} ArtCraft")

        excerpts = fetch_excerpts(space_key)
        print(f"  -> excerpt {len(excerpts)}")

        for page in new_pages:
            pid = page["id"]
            title = page.get("title", "")
            summary = excerpts.get(pid, "")
            full_text = title + " " + summary

            all_pages.append({
                "team":    team,
                "types":   extract_types(full_text),
                "tools":   extract_tools(full_text),
                "views":   0,
                "title":   title,
                "url":     f"https://neowiz.atlassian.net/wiki/spaces/{space_key}/pages/{pid}",
                "space":   space_key,
                "date":    extract_date(page),
                "author":  extract_author(page),
                "summary": summary[:200],
            })

        print(f"  -> done {len(new_pages)}")

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
        print("\n[warning] PAGES not found")
        return False
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"\n[done] {len(pages)} pages updated")
    return True

if __name__ == "__main__":
    if not CONFLUENCE_EMAIL or not CONFLUENCE_TOKEN:
        print("set CONFLUENCE_EMAIL and CONFLUENCE_TOKEN")
        sys.exit(1)
    print(f"=== update ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===")
    pages = build_pages_array()
    print(f"\ntotal {len(pages)} pages")
    update_index_html(pages)
