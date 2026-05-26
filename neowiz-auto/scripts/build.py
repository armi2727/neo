#!/usr/bin/env python3
"""
Confluence에서 AI/디자인 관련 글을 긁어서 index.html을 자동 생성하는 스크립트.
"""
import os, re, json, requests
from base64 import b64encode
from datetime import datetime, timezone

CONFLUENCE_BASE = "https://neowiz.atlassian.net"
EMAIL = os.environ["CONFLUENCE_EMAIL"]
TOKEN = os.environ["CONFLUENCE_API_TOKEN"]
AUTH = b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}", "Accept": "application/json"}

SKIP_TITLE = [
    '회의록','주간회의','주간 회의','월간','월간보고','리더회의',
    '일일지표','일일 지표','지표 이슈','지표 공유','지표 검토',
    '부스팅 이벤트 보상','보상 지급','계약 체결','마케팅 계획','마케팅 성과',
    '인수인계','온보딩','채용','스프린트 계획','릴리즈노트','릴리즈 노트',
    '요구사항 정의','기능 정의서','복사용 템플릿','업무 공유','업무공유',
    'by n8n','gemini bot','n8n gemini',
    '블루리더','레드개발팀','퍼플리더','사업실 회의',
]

AI_WORK_KW = [
    'ai 이미지','이미지 생성','stable diffusion','midjourney','미드저니',
    '나노바나나','nano banana','chatgpt','gemini','google ai studio',
    'suno','kling','higgsfield','seedance','weavy','위비','dzine','krea',
    'pix ai','runway','veo','sora','tripo','생성형 ai','ai 툴','ai tool',
    'ai를 활용','ai로 제작','ai 생성','ai 활용','artcraft','art craft',
    'aid tf','claude ai','cursor ide','claude code','google flow',
    'see through','comfyui','eleven','codex','plan craft',
    'streamlit','cortex code','프로젝트 협업 요약','n8n','craft camp',
    'ai 캐릭터','ai 게이트웨이','ai 기획서','ai 브리핑',
]

def should_skip(title):
    tl = title.lower()
    return any(kw.lower() in tl for kw in SKIP_TITLE)

def has_ai_work(title, excerpt):
    tx = (title + ' ' + (excerpt or '')).lower()
    return any(k in tx for k in AI_WORK_KW)

def classify(title, excerpt, space_name, space_key):
    tx = (title + ' ' + (excerpt or '')).lower()
    team = '공용'
    if space_name in ['레드사업실','마케팅실'] or space_key in ['1122','1033']: team = '레드'
    elif space_name in ['퍼플사업실','오렌지사업실'] or space_key in ['1107','1235']: team = '퍼플'
    elif space_name == '블루사업실' or space_key == '1109': team = '블루'
    elif space_name == '브라운사업실' or space_key == '1234': team = '브라운'
    elif space_key in ['1227','1266','1168','1031']: team = '올림포스'
    types = []
    if any(k in tx for k in ['suno','음악','sound','bgm','사운드','음향','music','google flow']): types.append('사운드')
    if any(k in tx for k in ['자동화 툴','플러그인','스크립트','앱 제작','앱 빌드','운영툴','자동화','liteui','resource namer','align tool','exporter','codex','streamlit','n8n','생성기']): types.append('자동화툴')
    if any(k in tx for k in ['영상','video','animation','sprite','연출','이펙트','모션','업스케일','fx','kling','seedance','runway','veo','sora','higgsfield','루프']): types.append('영상')
    if any(k in tx for k in ['포토샵','photoshop','합성','편집','스케일업','see through','comfy']): types.append('포토샵')
    if any(k in tx for k in ['figma','피그마']): types.append('Figma')
    if any(k in tx for k in [' ui ',' ux ','팝업 디자인','배너 디자인','ui/ux','쉐이더','tmp','roundmaker','shapefeather']): types.append('UI디자인')
    if any(k in tx for k in ['r&d','테스트','비교','후기','사용기','실험','실패기','탐구','vs.','알파','브리핑']): types.append('R&D·비교')
    if any(k in tx for k in ['심볼','슬롯','원화','게임 리소스','리소스 제작']): types.append('리소스')
    if any(k in tx for k in ['이미지','image','생성','컨셉','시안','캐릭터','배경','화풍','썸네일','아바타']): types.append('이미지생성')
    types = list(dict.fromkeys(types))[:2]
    if not types: types = ['이미지생성']
    tools = []
    for kw, t in [('suno','Suno'),('gemini','Gemini'),('gpt','ChatGPT'),('chatgpt','ChatGPT'),
                  ('나노바나나','나노바나나'),('nano banana','나노바나나'),
                  ('midjourney','Midjourney'),('미드저니','Midjourney'),
                  ('kling','Kling AI'),('클링','Kling AI'),('claude','Claude'),
                  ('stable diffusion','Stable Diffusion'),('google ai studio','Google AI Studio'),
                  ('google flow','Google Flow'),('dzine','Dzine'),('krea','KREA'),
                  ('seedance','Seedance'),('weavy','Weavy'),('위비','위비'),
                  ('runway','Runway'),('higgsfield','Higgsfield'),('eleven','ElevenLabs'),
                  ('grok','Grok'),('tripo','Tripo 3D'),('veo','Veo'),('sora','Sora'),
                  ('cursor','Cursor'),('codex','Codex'),('streamlit','Streamlit'),('n8n','n8n')]:
        if kw in tx and t not in tools: tools.append(t)
    if not tools: tools = ['AI 이미지']
    return team, types[:2], tools[:3]

def search_confluence(cql, limit=50):
    url = f"{CONFLUENCE_BASE}/wiki/rest/api/search"
    params = {"cql": cql, "limit": limit, "excerpt": 150, "expand": "content.history"}
    results = []
    start = 0
    while True:
        params["start"] = start
        res = requests.get(url, headers=HEADERS, params=params)
        res.raise_for_status()
        data = res.json()
        batch = data.get("results", [])
        results.extend(batch)
        total = data.get("totalSize", 0)
        start += len(batch)
        if start >= total or not batch: break
        if start >= 500: break
    return results

def fetch_all_pages():
    spaces = '"1107","1122","1109","1234","1235","1033"'
    queries = [
        # 제목 기반
        f'(title ~ "AID TF" OR title ~ "ArtCraft" OR title ~ "Art Craft") AND type = page ORDER BY created DESC',
        # 본문 AI 툴 기반 — 최근 2주 (오늘 올린 글 포함)
        f'space in ({spaces}) AND type = page AND (text ~ "Midjourney" OR text ~ "나노바나나" OR text ~ "Dzine" OR text ~ "KREA" OR text ~ "ChatGPT" OR text ~ "Gemini" OR text ~ "Suno" OR text ~ "Kling AI" OR text ~ "Higgsfield" OR text ~ "Seedance" OR text ~ "Weavy" OR text ~ "Stable Diffusion") AND created >= now("-14d") ORDER BY created DESC',
        # 본문 AI 키워드 — 최근 2주
        f'space in ({spaces}) AND type = page AND (text ~ "AI 이미지" OR text ~ "이미지 생성" OR text ~ "생성형 AI" OR text ~ "AI 활용" OR text ~ "AI 툴" OR text ~ "Claude AI" OR text ~ "Google AI Studio") AND created >= now("-14d") ORDER BY created DESC',
        # 2025-09-01 이후 ~ 2주 전 (DESC + ASC 양방향)
        f'space in ({spaces}) AND type = page AND (text ~ "Midjourney" OR text ~ "나노바나나" OR text ~ "Dzine" OR text ~ "KREA" OR text ~ "ChatGPT" OR text ~ "Gemini" OR text ~ "Suno" OR text ~ "Kling AI" OR text ~ "Higgsfield" OR text ~ "Seedance") AND created >= "2025-09-01" AND created < now("-14d") ORDER BY created DESC',
        f'space in ({spaces}) AND type = page AND (text ~ "Midjourney" OR text ~ "나노바나나" OR text ~ "Dzine" OR text ~ "KREA" OR text ~ "ChatGPT" OR text ~ "Gemini" OR text ~ "Suno" OR text ~ "Kling AI" OR text ~ "Higgsfield" OR text ~ "Seedance") AND created >= "2025-09-01" AND created < now("-14d") ORDER BY created ASC',
        f'space in ({spaces}) AND type = page AND (text ~ "AI 이미지" OR text ~ "이미지 생성" OR text ~ "생성형 AI" OR text ~ "AI 활용" OR text ~ "Google AI Studio" OR text ~ "Weavy") AND created >= "2025-09-01" AND created < now("-14d") ORDER BY created DESC',
        f'space in ({spaces}) AND type = page AND (text ~ "AI 이미지" OR text ~ "이미지 생성" OR text ~ "생성형 AI" OR text ~ "AI 활용" OR text ~ "Google AI Studio" OR text ~ "Weavy") AND created >= "2025-09-01" AND created < now("-14d") ORDER BY created ASC',
        # 2025-09-01 이전 (24년, 25년 초)
        f'space in ({spaces}) AND type = page AND (text ~ "Midjourney" OR text ~ "나노바나나" OR text ~ "ChatGPT" OR text ~ "Gemini" OR text ~ "AI 이미지" OR text ~ "이미지 생성" OR text ~ "생성형 AI" OR text ~ "AI 활용") AND created < "2025-09-01" ORDER BY created DESC',
        f'space in ({spaces}) AND type = page AND (text ~ "Midjourney" OR text ~ "나노바나나" OR text ~ "ChatGPT" OR text ~ "Gemini" OR text ~ "AI 이미지" OR text ~ "이미지 생성" OR text ~ "생성형 AI" OR text ~ "AI 활용") AND created < "2025-09-01" ORDER BY created ASC',
    ]
    all_results = []
    seen_ids = set()
    for cql in queries:
        for r in search_confluence(cql, limit=50):
            cid = r.get("content", {}).get("id", "")
            if not cid or cid in seen_ids: continue
            title = r.get("content", {}).get("title", "")
            if should_skip(title): continue
            excerpt = re.sub(r"<[^>]+>", "", r.get("excerpt", "")).strip()[:150]
            if not has_ai_work(title, excerpt): continue
            seen_ids.add(cid)
            all_results.append(r)
        print(f"  누적: {len(all_results)}개")
    return all_results

def parse_page(r, idx):
    c = r.get("content", {})
    title = c.get("title", "")
    webui = c.get("_links", {}).get("webui", "")
    full_url = CONFLUENCE_BASE + "/wiki" + webui
    space_key = r.get("resultGlobalContainer", {}).get("displayUrl", "").split("/")[-1]
    space_name = r.get("resultGlobalContainer", {}).get("title", "")
    last_mod = (r.get("lastModified") or "")[:10]
    author = c.get("history", {}).get("createdBy", {}).get("displayName", "")
    excerpt = re.sub(r"<[^>]+>", "", r.get("excerpt", "")).strip()[:150]
    team, types, tools = classify(title, excerpt, space_name, space_key)
    return {"team": team, "types": types, "tools": tools, "views": 100 + idx * 3,
            "title": title, "url": full_url, "space": space_key, "date": last_mod,
            "author": author, "summary": excerpt}

def esc(s):
    return (s or '').replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", "")

def to_js(e):
    t = '","'.join(e["types"]); tl = '","'.join(e["tools"])
    return (f'  {{team:"{e["team"]}",types:["{t}"],tools:["{tl}"],views:{e["views"]},'
            f'title:"{esc(e["title"])}",url:"{e["url"]}",'
            f'space:"{e["space"]}",date:"{e["date"]}",author:"{esc(e["author"])}",'
            f'summary:"{esc(e["summary"])}"}},')

def build_html(pages_js, updated_at):
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "template_before.html")) as f: before = f.read()
    with open(os.path.join(base, "template_after.html")) as f: after = f.read()
    after = after.replace("__UPDATED_AT__", updated_at)
    return before + "const PAGES=[\n" + pages_js + "\n];\n" + after

def main():
    print("🔍 Confluence 검색 중...")
    results = fetch_all_pages()
    print(f"  총 {len(results)}개 결과")
    pages = []
    seen_urls = set()
    for i, r in enumerate(results):
        p = parse_page(r, i)
        if p and p["url"] not in seen_urls:
            seen_urls.add(p["url"])
            pages.append(p)
    print(f"  필터 후 {len(pages)}개 페이지")
    pages_js = "\n".join(to_js(p) for p in pages)
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = build_html(pages_js, updated_at)
    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w") as f: f.write(html)
    print(f"✅ public/index.html 생성 완료 ({len(html)} bytes)")

if __name__ == "__main__":
    main()
