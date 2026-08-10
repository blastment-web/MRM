# MAPS · 생산기술혁신센터 AI 플랫폼

**M**anufacturing **A**I agent **P**latform & **S**hared-dashboard — 센터 업무 카테고리별 AI Agent를 한 곳에 모은 사내 포털.

## 버전

| 버전 | 내용 |
|------|------|
| **V1** | 최초 등록. 로컬(VS Code) 작업본의 렌더링된 페이지 원본을 이 저장소에 복원한 기준점. |
| **V2** | 4메뉴 구조 개편 · TOP5 신설 · Agent 카드 재설계 |
| **V3** | 로컬 V11 작업본으로 동기화 (대시보드 3패널 · 화면 높이 자동 맞춤) |
| **V12~V15** | 전폭 레이아웃 · 4화면 여백 정리 · 히어로 강화 · 카드 확대 · 디자인 조정 변수 |
| **MAPS V1** | 위 결과를 확정한 스냅샷. `releases/MAPS-V1/` 폴더. |
| **MAPS V2** | 브랜드 AIMS → MAPS · 막대차트 높이 연동 버그 수정 · TOP5 즐겨찾기 위치 · AI Agent 등록 버튼 연결. `releases/MAPS-V2/`. |
| **MAPS V3** | AI 매니저 추천을 챗봇 3단계 위저드로 이전 · 공지 더보기/글쓰기 정상화 · 푸터 커뮤니티 링크 연결 · 톱니바퀴를 설정 패널로 · 맨 위로 버튼 · 하단 고정 검색/채팅 바. `releases/MAPS-V3/`. |
| **MAPS V4-1** | V3 + 공통 수정 7건(등록 모달 개편 · 파우치/각형기술그룹 · MAPS 태그라인 · 준비중 아이콘 · 카탈로그 등록 버튼 · 공지 4건/[공지]만). **히어로는 V3 별자리 유지.** `releases/MAPS-V4-1/`. |
| **MAPS V4-2** | V4-1 + 히어로를 **배경 영상**으로 교체하고 첫 화면(히어로만) / 대시보드(3패널) 두 화면으로 분리. `releases/MAPS-V4-2/`. |

> 로컬 환경에서는 V8까지 진행되었으나, 이 저장소에는 그 최신 결과물을 **V1**(기준선)으로 등록했습니다.
> 이후 이 저장소에서의 변경은 V2, V3… 으로 이어갑니다.

## 파일 구성

```
index.html                포털 화면 전체 (HTML + CSS + JS 단일 파일)
tools/build_preview.py    디자인 미리보기 생성 스크립트
tools/build_v4.py         V3 → V4-1 / V4-2 생성 스크립트
tools/build_standalone.py 단독 실행용 사본 생성 스크립트
tools/serve_local.py      리허설용 로컬 서버 (Range 지원 — 영상 구간 반복에 필수)
tools/demo_data.py        위 두 빌더가 공유하는 데모 데이터 (공지·공유·Q&A·게시판)
releases/MAPS-V1/         확정 버전 스냅샷
releases/MAPS-V2/         확정 버전 스냅샷
releases/MAPS-V3/         확정 버전 스냅샷 + index.standalone.html
releases/MAPS-V4-1/       확정 버전 스냅샷 (최신 · 별자리 히어로) + index.standalone.html
releases/MAPS-V4-2/       확정 버전 스냅샷 (최신 · 영상 히어로) + index.standalone.html
docs/기능-사양-작성법.md   AI 매니저 추천·Agent 등록·챗봇 기능 지시 방법
docs/사내-공유-및-서버화-가이드.md  URL 공유·서버화 선택지 비교 + 원격 데스크톱 성능 대응
docs/온프레미스-서버-구축-절차.md   PC 1대 서버 구성 실행 절차 (사양·IT 신청·설치·백업)
docs/로컬-PC-리허설-체크리스트.md   새 PC 전에 지금 PC 로 시험하는 절차
preview/                  빌드 산출물 (git 제외 — 언제든 재생성 가능)
```

## 파일 하나만 남에게 건넬 때

사내가 아닌 PC · 다른 네트워크에서 `index.html` 을 그냥 열면 배경 별자리 · 스크롤 리빌 ·
로고 펄스 · 대시보드 카운트업이 죽고, 자료공유 · 게시판 · Q&A 는 빈 채로 남는다.
OS 의 감속모션 설정(회사 PC 기본값)에 걸리는 게이트와, 응답하지 않는 `api/*` 요청에
화면이 묶이는 문제 때문이다. 이때는 아래로 만든 사본을 건넨다.

```bash
python3 tools/build_v4.py                                  # V3 → V4-1 / V4-2
python3 tools/build_standalone.py <입력> <출력>            # 단독 실행용 사본
```

**로컬에서 켠 것과 화면·기능이 같아지는 것이 목표**다. 두 빌더 모두 입력 원본은 읽기만 한다.
고치는 항목과 Chromium 실측 비교는 각 릴리스의 `README.md` 참고.

## 화면을 보면서 직접 조정하기

미리보기에는 **디자인 조정 패널**(왼쪽 아래 `🎛 디자인 조정`)이 붙어 있습니다.
슬라이더로 좌우 여백 · 히어로 크기 · 카드 글자 크기 등을 바꾸면 화면에 바로 반영되고,
`설정값 복사` 를 누르면 아래 한 줄이 나옵니다.

```css
:root{--gut:150px;--hero-scale:1.20;--card-scale:1.15}
```

이 줄을 `index.html` 의 V15 블록 `:root{...}` 기본값에 넣으면 그대로 확정됩니다.
패널은 `tools/build_preview.py` 의 shim 에만 있고 `index.html` 에는 들어가지 않습니다.

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
3. **랜딩 인터랙션 레이어** — 히어로 배경(V4-1 파티클 canvas / V4-2 영상), 스크롤 리빌, STATS 카운트업, 고정 헤더 상태, 커뮤니티 카드 위임

## 화면 구성 (세로 스크롤 랜딩)

| 섹션 | ID | 내용 |
|------|-----|------|
| 대시보드(Hero) | `#secHome` | 메인 카피 + 현황·차트·공지 3패널. 배경은 V4-1 파티클 / V4-2 영상 |
| 대시보드 (V4-2 전용) | `#secDash` | V4-2 에서 3패널이 이 섹션으로 분리됨 |
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
