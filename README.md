# AIMS · 생산기술혁신센터 AI 플랫폼

**A**I **I**nnovation **M**anufacturing **S**ystem — 센터 업무 카테고리별 AI Agent를 한 곳에 모은 사내 포털.

## 버전

| 버전 | 내용 |
|------|------|
| **V1** | 최초 등록. 로컬(VS Code) 작업본의 렌더링된 페이지 원본을 이 저장소에 복원한 기준점. |

> 로컬 환경에서는 V8까지 진행되었으나, 이 저장소에는 그 최신 결과물을 **V1**(기준선)으로 등록했습니다.
> 이후 이 저장소에서의 변경은 V2, V3… 으로 이어갑니다.

## 파일 구성

```
index.html                포털 화면 전체 (HTML + CSS + JS 단일 파일)
tools/build_preview.py    디자인 미리보기 생성 스크립트
preview/                  빌드 산출물 (git 제외 — 언제든 재생성 가능)
```

## 미리보기 생성

백엔드 없이 화면만 확인할 때 사용합니다.

```bash
python3 tools/build_preview.py          # → preview/aims-preview.html
```

원본에서 래퍼 태그(`<!DOCTYPE>`/`<html>`/`<head>`/`<body>`)를 제거하고, 공유·Q&A·게시판·공지 4개 영역에 샘플 데이터를 주입하는 shim을 덧붙입니다.
**`index.html`은 수정하지 않습니다** — 추출과 append만 수행하며, shim은 원본 로직 대신 전역 로더 함수(`loadShare` 등)만 교체합니다.

`index.html` 하나에 마크업·스타일·스크립트가 모두 들어 있습니다. 스크립트는 3개 블록으로 나뉩니다.

1. **메인 애플리케이션** — 대시보드 그리드, 세션/로그인, 관리자 콘솔, 게시판, Q&A, 공유 섹션, 챗봇, 팝업, 매뉴얼
2. **브랜드 로고 애니메이션** — SVG 오케스트레이션 노드 (허브 ↔ 위성 노드 펄스, 무한 루프)
3. **랜딩 인터랙션 레이어** — 히어로 파티클 네트워크(canvas), 스크롤 리빌, STATS 카운트업, 고정 헤더 상태, 커뮤니티 카드 위임

## 화면 구성 (세로 스크롤 랜딩)

| 섹션 | ID | 내용 |
|------|-----|------|
| Hero | `#secHero` | 파티클 네트워크 배경 + 메인 카피 |
| Our Mission | `#secMission` | 미션 문구 |
| 플랫폼 목적 | `#secWhy` | 가치 3카드 |
| Stats | `#secStats` | 조직/모듈/운영중/준비중 카운트 (STATE에서 자동 계산) |
| Insight | `#secInsight` | 공지사항 · 실시간 인기 모듈 |
| 카테고리별 AI Agent | `#secPlatform` | 대시보드 그리드 (검색·자동완성·펼치기) |
| 자료 업로드 | `#secModules` | 구성원 자료 공유 섹션 |
| 향후계획 | `#secRoadmap` | 2026~2028 로드맵 |
| Community | `#secCommunity` | Q&A · 게시판 진입 카드 |

게시판(`#boardSection`)과 Q&A(`#loungeSection`)는 메인 뷰와 교체되는 별도 섹션입니다.

## 데이터 카테고리

`ORG_ORDER` 상수가 그리드 정렬 순서를 결정하며, 아래 4개 문자열과 정확히 일치해야 합니다.

1. 기술개발 도출 지원
2. 이슈 원인분석
3. MRM 과제 운영
4. 제품 개발 프로세스 개선

각 항목의 `addr`가 비어 있으면 **준비중**, 주소가 있으면 **운영중(LIVE)** 으로 표시됩니다.

## 백엔드 의존성

이 파일은 정적 HTML이지만, 실제 동작에는 같은 경로의 백엔드 API가 필요합니다.
**이 저장소에는 백엔드가 포함되어 있지 않습니다.**

- `data/dashboards.json` — 대시보드 목록. 없으면 `FALLBACK` 상수로 대체되어 화면은 정상 렌더링됩니다.
- `api/*` — 세션(`me`/`login`/`logout`/`register`), 대시보드(`save`/`dash-stats`/`dash-rank`/`dash-access`/`health`), 게시판(`posts`/`post`/`comment`/`attach`), Q&A(`lounge-*`), 공유(`share-*`), 승인(`approve-*`), 팝업(`popup-*`), 매뉴얼(`manual*`) 등

브라우저에서 `index.html`을 직접 열면 API 호출은 모두 실패하지만, `FALLBACK` 데이터로 **레이아웃과 인터랙션은 확인 가능**합니다.

## 남은 작업 (파일 내 TODO)

- `#secWhy` 가치 3카드 — 실제 가치 제안으로 교체
- `#secRoadmap` — 실제 로드맵으로 교체
- `.ih-brand` 슬로건 영역 — 센터 슬로건 확정 후 문구 채우기 (V5에서 비워둔 상태)
- 인프라그룹 ARIA 주소는 V6에서 제거됨 — PTIC 실주소 확보 시 해당 항목 `addr`에 입력
