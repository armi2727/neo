# 🤖 NAID — Neowiz AI Design Hub

Confluence에서 AI/디자인 관련 글을 매일 자동으로 수집하여 GitHub Pages에 배포합니다.

## 🚀 설정 방법 (딱 한 번만)

### 1단계 — GitHub Secrets 등록
레포 → **Settings → Secrets and variables → Actions → New repository secret**

| Secret 이름 | 값 |
|---|---|
| `CONFLUENCE_EMAIL` | 네오위즈 이메일 (예: hong@neowiz.com) |
| `CONFLUENCE_API_TOKEN` | Atlassian API Token |

> API Token 발급: https://id.atlassian.com/manage-profile/security/api-tokens

### 2단계 — GitHub Pages 설정
레포 → **Settings → Pages → Source: Deploy from a branch → Branch: gh-pages**

### 3단계 — 첫 실행
레포 → **Actions → 🤖 Confluence AI 페이지 자동 업데이트 → Run workflow**

---

## ⏰ 자동 실행 일정
- **매일 오전 9시 (KST)** 자동 실행
- 수동 실행: Actions 탭 → Run workflow 클릭

## 📁 파일 구조
```
├── .github/workflows/update.yml   ← 자동 실행 스케줄
├── scripts/
│   ├── build.py                   ← Confluence 수집 + HTML 빌드
│   ├── template_before.html       ← HTML 앞부분 템플릿
│   └── template_after.html        ← HTML 뒷부분 템플릿
└── public/
    └── index.html                 ← 자동 생성됨 (커밋 불필요)
```
