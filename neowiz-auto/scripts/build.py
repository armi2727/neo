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
    "\uc601\uc0c1": ["\uc601\uc0c1 \uc81c\uc791","\uc601\uc0c1\uc81c\uc791","video","kling","\ud074\ub9c1","sora","higgsfield","seedance","veo","hailuo","\ubaa8\uc158","\uc560\ub2c8\uba54\uc774\uc158"],
    "\ub9ac\uc18c\uc2a4": ["\uac8c\uc784 \ub9ac\uc18c\uc2a4","\ub9ac\uc18c\uc2a4 \uc81c\uc791","\uc2ac\ub86f.*\ub9ac\uc18c\uc2a4","\uc2ec\ubcfc","\uadf8\ub798\ud53d \ub9ac\uc18c\uc2a4"],
    "\uc0ac\uc6b4\ub4dc": ["\uc0ac\uc6b4\ub4dc","\uc74c\uc545","bgm","sound","music","suno","elevenlabs","\uc624\ub514\uc624","\ubcf4\uc774\uc2a4"],
    "\uc790\ub3d9\ud654\ud234": ["\uc790\ub3d9\ud654","automation","\uc2a4\ud06c\ub9bd\ud2b8","claude code","cursor","\ucee4\uc11c","n8n","gitlab ci","ci/cd"],
    "\ud3ec\ud1a0\uc0f5": ["\ud3ec\ud1a0\uc0f5","photoshop","\ud3b8\uc9d1","\ud6c4\ud3b8\uc9d1","weavy","\uc704\ube44","upscayl"],
    "UI\ub514\uc790\uc778": ["ui \ub514\uc790\uc778","ui design","\ubc30\ub108","\ud31d\uc5c5","\ubc84\ud2bc","ux"],
    "Figma": ["figma","\ud53c\uadf8\ub9c8"],
    "R&D\u00b7\ube44\uad50": ["r&d","\ube44\uad50","\ud14c\uc2a4\ud2b8","\ub9ac\uc11c\uce58","research","\ubd84\uc11d","\uac80\ud1a0"],
    "AI\uc81c\uc791\ud234": ["\ud50c\ub7ec\uadf8\uc778","plugin","\ud234 \uc81c\uc791","bluetester","streamlit","page launcher","scheduler","\uac8c\uc784 \uc81c\uc791\uae30","align tool","resource namer"],
    "\uc720\ub2c8\ud2f0": ["unity","\uc720\ub2c8\ud2f0","shader"],
}

TOOL_KEYWORDS = {
    "ChatGPT": ["chatgpt","gpt"],
    "Midjourney": ["midjourney","\ubbf8\ub4dc\uc800\ub2c8"],
    "Gemini": ["gemini","\uc81c\ubbf8\ub098\uc774"],
    "\ub098\ub178\ubc14\ub098\ub098": ["\ub098\ub178\ubc14\ub098\ub098","nanobanana"],
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
    "ElevenLabs": ["elevenlabs"],
    "ComfyUI": ["comfyui"],
    "Tripo 3D": ["tripo"],
    "Sora": ["sora"],
    "Google Flow": ["google flow"],
    "AI \uc774\ubbf8\uc9c0": ["ai \uc774\ubbf8\uc9c0","ai\uc774\ubbf8\uc9c0"],
}

def get_auth():
    return b64encode(f"{EMAIL}:{TOKEN}".encode("utf-8")).decode("ascii")

def api_get(path, params=None, retry=3):
    url = f"{CONFLUENCE_BASE}{path}"
    headers = {"Authorization": f"Basic {get_auth()}", "Accept": "application/json"}
    for attempt in range(retry):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            if r.status_code == 401:
                print(f"  [HTTP 401] \uc778\uc99d \uc624\ub958")
                return None
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt < retry - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  [\uc624\ub958] {e}")
                return None

def fetch_all_pages():
    spaces = ",".join(f'"{s}"' for s in SPACE_TEAM.keys())
    cql = (
        f'space in ({spaces}) AND '
        f'(title ~ "ArtCraft" OR title ~ "Art Craft" OR '
        f'title ~ "AID TF" OR title ~ "AID TFT" OR title ~ "TechCraft") '
        f'AND type = page ORDER BY created DESC'
    )
    results = []
    start = 0
    while True:
        data = api_get("/wiki/rest/api/content/search", {
            "cql": cql,
            "limit": 100,
            "start": start,
            "expand": "content.history.createdBy",
        })
        if not data or not data.get("results"):
            break
        batch = data["results"]
        results.extend(batch)
        print(f"  \ub204\uc801: {len(results)}\uac1c")
        if not data.get("_links", {}).get("next"):
            break
        if len(results) >= 1000:
            break
        start += 100
        time.sleep(0.2)
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
    with open(os.path.join(base, "template_before.html"), encoding="utf-8") as f:
        before = f.read()
    with open(os.path.join(base, "template_after.html"), encoding="utf-8") as f:
        after = f.read()
    after = after.replace("__UPDATED_AT__", updated_at)
    return before + "const PAGES=[\n" + pages_js + "\n];\n" + after

def main():
    print("Confluence \uac80\uc0c9 \uc911...")
    print(f"  EMAIL: {EMAIL[:4]}..." if EMAIL else "  EMAIL: \ube44\uc5b4\uc788\uc74c")
    print(f"  TOKEN: {TOKEN[:4]}..." if TOKEN else "  TOKEN: \ube44\uc5b4\uc788\uc74c")

    raw = fetch_all_pages()
    print(f"  \uc4f0 {len(raw)}\uac1c \uacb0\uacfc")

    # 첫 번째 결과 구조 디버그
    if raw:
        r0 = raw[0]
        print(f"  DEBUG keys: {list(r0.keys())}")
        print(f"  DEBUG content keys: {list(r0.get('content', {}).keys())}")
        print(f"  DEBUG content.id: {r0.get('content', {}).get('id')}")
        print(f"  DEBUG title: {r0.get('title')}")
        print(f"  DEBUG url: {r0.get('url')}")

    pages = []
    seen = set()

    for i, r in enumerate(raw):
        # 실제 API 응답 구조: r.content.id, r.title, r.excerpt, r.lastModified, r.url
        content = r.get("content", {})
        cid = content.get("id")
        if not cid or cid in seen:
            continue
        seen.add(cid)

        title = r.get("title", "") or content.get("title", "")
        excerpt = re.sub(r"<[^>]+>", "", r.get("excerpt", "")).strip()[:150]
        last_mod = (r.get("lastModified") or "")[:10]

        # URL: r.url = "/spaces/1107/pages/..."
        page_url_path = r.get("url", "") or content.get("_links", {}).get("webui", "")
        full_url = CONFLUENCE_BASE + "/wiki" + page_url_path if page_url_path else ""

        # space_key: URL에서 추출
        space_key = ""
        parts = page_url_path.split("/")
        if "spaces" in parts:
            idx2 = parts.index("spaces")
            if idx2 + 1 < len(parts):
                space_key = parts[idx2 + 1]

        # resultGlobalContainer fallback
        if not space_key:
            display_url = r.get("resultGlobalContainer", {}).get("displayUrl", "")
            space_key = display_url.strip("/").split("/")[-1] if display_url else ""

        team = SPACE_TEAM.get(space_key, "\ud37c\ud50c")

        # author
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
            "tools": tools if tools else ["AI \uc774\ubbf8\uc9c0"],
            "views": 100 + i * 3,
            "title": title,
            "url": full_url,
            "space": space_key,
            "date": last_mod,
            "author": author,
            "summary": excerpt,
        })

    print(f"  \ud544\ud130 \ud6c4 {len(pages)}\uac1c \ud398\uc774\uc9c0")

    pages_js = "\n".join(to_js(p) + "," for p in pages)
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = build_html(pages_js, updated_at)

    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"public/index.html \uc644\ub8cc ({len(html)} bytes)")

if __name__ == "__main__":
    main()
