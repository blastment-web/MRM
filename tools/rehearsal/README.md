# 리허설 꾸러미 — 지금 쓰는 PC 를 잠깐 서버로

새 PC 를 들여오기 **전에** 지금 PC 로 "URL 하나로 동료에게 공유" 가 되는지만
확인하기 위한 최소 도구다. Python 도, 새로 설치할 프로그램도 없다.
Windows 에 이미 들어 있는 **IIS** 를 배치 파일로 켜고 끈다.

## 전달할 폴더 만들기

이 폴더의 배치·안내 4개 + 화면 파일 3개 + `data/` + `agents/` 를 한 폴더에 모아 압축해서 건넨다.

```bash
mkdir -p "MAPS-실험/data"
cp releases/MAPS-V4-1/index.standalone.html "MAPS-실험/index-v4-1.html"
cp releases/MAPS-V4-2/index.standalone.html "MAPS-실험/index-v4-2.html"
cp tools/rehearsal/선택화면.html tools/rehearsal/*.bat tools/rehearsal/읽어보세요.txt "MAPS-실험/"
cp -r tools/rehearsal/agents "MAPS-실험/"
python3 tools/make_dashboards_json.py --out "MAPS-실험/data/dashboards.json" \
        --live "공정 조건 최적화 Agent" --addr "http://localhost/agents/sample-agent/"
```

**파일 이름이 곧 주소다.** `index-<이름>.html` 하나가 `http://IP/<이름>/` 하나가 된다.
사용자가 자기 PC 의 다른 버전을 넣고 배치를 다시 돌리면 주소가 늘어난다 — 배치를 고칠
필요가 없다. 그래서 파일명을 **소문자**로 맞춰 두었다(슬러그가 그대로 URL 이 된다).

선택 화면 이름에 `index-` 를 붙이지 않는 이유도 같다. 붙이면 저 규칙에 걸려
선택 화면 자체가 주소로 만들어진다.

압축할 때는 파일 이름에 **UTF-8 플래그(범용 비트 11)** 를 세워야 한다.
안 그러면 Windows 탐색기에서 한글 파일명이 깨진다. `zip` 기본 동작은 플래그를
세우지 않으므로 파이썬 `zipfile` 로 `flag_bits |= 0x800` 을 주고 묶는다.

## 인코딩

- `*.bat` — **CP949**. UTF-8 로 저장하면 cmd 창에서 한글 안내문이 전부 깨져
  배치의 존재 이유가 사라진다. 고칠 때도 CP949 를 유지할 것
- `읽어보세요.txt` — UTF-8 + BOM (메모장이 바로 읽는다)
- 줄바꿈은 셋 다 **CRLF**

## 1_서버켜기.bat 가 하는 일

| 단계 | 명령 |
|---|---|
| 1 | `net session` 으로 관리자 권한 확인 |
| 2 | `선택화면.html` · `data\dashboards.json` 과 **`index-*.html` 이 최소 1개** 있는지 확인 |
| 3 | `dism /online /enable-feature` 를 **기능마다 한 번씩** |
| 4 | 선택 화면 → `wwwroot\index.html`, **`index-*.html` 마다 폴더 하나**, `data/` 는 각 폴더에, `agents/` 는 루트에 한 벌, 선택 화면이 읽을 `versions.js` 생성 |
| 5 | `netsh advfirewall` 로 인바운드 TCP 80 허용 (`MAPS-Rehearsal-HTTP-80`) |
| 6 | `sc config` + `net start w3svc` |
| 확인 | `curl` 로 선택 화면과 **각 버전 주소**를 호출해 200 인지 찍고, `ipconfig` 로 살아 있는 주소를 전부 찍는다 |

`3_에이전트연결.bat` 은 남이 만든 HTML 을 `agents/<폴더>/index.html` 로 올리고
붙여넣을 `"addr"` 한 줄을 실제 IP 로 찍어 준 뒤, `start /wait notepad` 로
`dashboards.json` 을 열고 **메모장이 닫히면 올라가 있는 모든 화면 폴더에 반영**한다.
편집 대상은 꾸러미 폴더의 원본이다 — `wwwroot` 쪽을 고치게 하면
`1_서버켜기.bat` 을 다시 돌릴 때 덮여 사라진다.

`2_서버끄기.bat` 는 4·5·6 을 되돌린다. **IIS 기능 자체는 끄지 않는다** —
끄면 재부팅을 요구할 수 있어 오히려 번거롭다.

## 파일 이름이 곧 주소다

```
index-v4-1.html   →   http://10.x.x.x/v4-1/
index-v4-2.html   →   http://10.x.x.x/v4-2/
index-v5.html     →   http://10.x.x.x/v5/      (파일만 넣고 배치 재실행)
http://10.x.x.x/  →   선택 화면
```

배포하면서 `versions.js` 를 함께 써 두어 **선택 화면 카드도 자동으로 늘어난다.**
`v4-1` · `v4-2` 는 제목·설명·썸네일을 아는 카드로, 처음 보는 이름은 일반 카드로 나온다.
`versions.js` 가 없으면 두 장으로 폴백해 배치를 안 돌린 상태에서도 깨지지 않는다.

> 설명문을 파일(`index-v5.txt` 같은)로 받아 카드에 넣는 방안은 일부러 뺐다.
> 그 안의 `&`·`>`·`"` 하나에 `versions.js` 가 깨지면 **선택 화면이 통째로 죽는다.**

**`agents/` 를 버전 폴더 안에 넣지 않는 것이 이 구조의 핵심이다.** `dashboards.json` 의
`addr` 은 전체 URL 이라 버전과 무관하게 열린다. 자료 실물이 한 벌이면 두 버전이 같은 것을
가리키고 올릴 때도 한 번만 올리면 된다.

앱이 **상대 경로로 읽는 것은 `data/dashboards.json` 하나뿐**이고 루트 절대경로(`/…`) 참조는
0건이라, 화면 파일을 하위 폴더로 옮겨도 깨지는 링크가 없다. 그 한 파일만 두 폴더에 복사한다.
원본은 꾸러미 폴더의 파일 하나이므로 두 사본이 어긋날 수 없다.

> **이전 구조에서 왜 바꿨나.** `index.html` 한 개를 갈아 끼우는 방식이었고, 서버가 읽는
> 것은 `wwwroot` 의 **복사본**이라 배치를 다시 돌리기 전까지 응답 바이트가 바뀌지 않았다.
> 여기에 브라우저 캐시와 탐색기 확장자 숨김(`index.html.html`)까지 겹쳐 원인이 셋인데
> 증상은 하나였다. 폴더를 나누면서 이 문제군이 통째로 사라져 `3_화면바꾸기.bat` 을 없앴다.

> **배치 문법 함정 하나.** `if 조건 명령 && set ...` 은 쓰면 안 된다.
> `if` 가 거짓이면 명령이 실행되지 않고 **직전 errorlevel 이 남아 `&&` 가 통과**한다.

## AI Agent 를 연결한다는 것 — 데이터 한 줄이다

```js
function isLive(it){ return it.addr && it.addr.trim()!=="" && !it.prep }   // index.html:2453
```

`loadData()` 는 `data/dashboards.json` 을 먼저 찾고 없으면 코드 안 `FALLBACK` 으로
대체한다. 그러니 이 파일을 서버에 놓는 순간부터 **카드 목록의 원본은 이 파일**이고,
연결이란 해당 항목의 `addr` 을 채우는 일이다. 백엔드는 이걸 자동화할 뿐 필수가 아니다.

세 가지를 실측으로 확인했다 (`serve_local.py` + 헤드리스 Chromium).

| 확인 | 결과 |
|---|---|
| 백엔드 없이 카드가 켜지나 | 켜진다. `● 사용 가능`, 헤더 `6개 · 운영 1` |
| `api/health` 가 없으면 "접속장애" 로 뜨나 | **안 뜬다.** 실패가 `catch(e){}` 로 삼켜져 `HEALTH` 가 빈 객체로 남고 `state` 가 `"ok"` 로 기본값 처리된다 |
| 카드를 누르면 올린 페이지가 열리나 | 열린다. `href` 가 그대로 `agents/<폴더>/` 로 잡힌다 |

**`addr` 에는 반드시 전체 URL 을 넣어야 한다.**

```js
function normAddr(a){ return /^https?:\/\//i.test(a) ? a : "http://"+a }   // index.html:2455
```

`"agents/foo/"` 를 넣으면 `http://agents/foo/` 가 되어 깨진다.
`make_dashboards_json.py` 의 `--addr` 는 이걸 미리 막는다.

## 카드를 누르면 팝업으로 열린다

같은 서버의 `/agents/` 자료는 새 탭이 아니라 화면 안 팝업으로 뜬다.
링크를 만드는 렌더러가 3곳(카탈로그 카드 · TOP5 · 인기 모듈)이라 각각 고치는 대신
**document 캡처 단계에서 한 번 가로챈다.** 다른 서버 주소는 새 탭 그대로 둔다 —
남의 서버는 대개 프레이밍을 거부하고, 교차 출처라 그 실패를 감지할 방법이 없어
흰 화면만 남기 때문이다. 항목의 `"open":"popup"|"tab"` 으로 강제할 수 있다.

**샌드박스로 격리해서 띄운다.** `allow-same-origin` 을 주지 않아 불투명 출처가 된다.
공격 페이지를 실제로 올려 확인한 결과다.

```
parent.document        → 차단됨 (SecurityError)
parent.document.cookie → 차단됨 (SecurityError)
document.cookie        → 차단됨 (SecurityError)
localStorage           → 차단됨 (SecurityError)
window.origin          → null
```

대가로 그 페이지는 **옆 파일을 `fetch` 로 못 읽고 `localStorage` 도 못 쓴다.**
업로더에게 **단일 HTML 파일**을 요청해야 하는 이유이고, 그 제약이 문제가 되면
새 PC 에서 **업로드 영역을 다른 포트의 사이트로 분리**하면 된다 —
진짜 다른 출처가 되어 `allow-same-origin` 을 켜도 MAPS 에는 닿지 못한다.

## 설계 판단 두 가지

**`appcmd set vdir` 로 사이트 경로를 옮기지 않는다.**
바탕화면·다운로드 폴더에는 `IIS_IUSRS` 읽기 권한이 없어 **401.3** 이 나기 쉽다.
기본 폴더로 복사하면 권한 문제도 `appcmd` 경로 문제도 생기지 않는다.

**`dism` 에 `IIS-WebServerRole` 하나만 넘기면 안 된다.**
`/all` 은 지정한 기능의 **상위** 기능만 켠다. 하위인 `IIS-StaticContent`(정적 파일 핸들러)와
`IIS-DefaultDocument`(기본 문서)가 빠져 404/403 이 난다. 그래서 기능을 나열하되,
이름 하나가 틀려도 전체가 죽지 않도록 **`for` 로 한 기능씩** 호출하고
마지막에 `sc query w3svc` 로 결과만 확인한다.

## 검증 상태

| 항목 | 상태 |
|---|---|
| 배치 파일 문법 · 인코딩 · CRLF | 검토 완료 |
| `index-V4-1.html` | 헤드리스 Chromium 확인 — 별자리 히어로 렌더(잉크 0.85%), 카테고리 4, 공지 3, 게시판 8행, **외부 요청 0건 · JS 오류 0건** |
| `index-V4-2.html` | 헤드리스 Chromium 확인 — `#secHome` 1600×900 히어로 전용 / `#secDash` 3패널 분리, `#secDash` 링크 3개, JS 오류 0건. **영상 재생은 확인 못 함** — 이 환경에서 `lgensol.com` 이 차단되어 `fail()` 이 영상을 숨긴다(설계된 폴백). 외부 요청 1건이 바로 그 영상이다 |
| **Agent 연결 경로** | `serve_local.py` 로 실제 서빙해 헤드리스 Chromium 으로 확인 — 대상 카드 `● 사용 가능`, `href` 정확, 클릭 시 올린 페이지가 200 으로 열림, JS 오류 0건 |
| **Agent 팝업** | V4-1 · V4-2 각각 **28개 항목 전부 통과 · JS 오류 0건**. 샌드박스 격리는 공격 페이지를 실제로 올려 확인했다 — `parent.document` · 쿠키 · `localStorage` 모두 `SecurityError`, `window.origin` 은 `null` |
| **주소 분리 구조** | 새 폴더 구조 그대로 서빙해 **20개 항목 전부 통과** — 주소별 200, 선택 화면 링크 이동, 버전이 서로 섞이지 않음(`#pxNet` / `#heroVideo`), 모두 카드 LIVE·팝업·딥링크 정상, 같은 `/agents/` 한 벌을 가리킴 |
| **버전 자동 추가** | V3 를 세 번째 화면으로 넣어 **15개 항목 전부 통과** — 선택 화면 카드 3장(V3 는 일반 카드), 각 카드 이동, `versions.js` 제거 시 2장 폴백·오류 0, 세 버전 모두 같은 자료를 가리킴. **팝업이 없는 옛 버전(V3)도 정상 동작**하며 카드는 새 탭으로 열린다 |
| `선택화면.html` | 외부 참조 0건 · 링크 전부 상대 경로 (`localhost` 로 열든 `10.x.x.x` 로 열든 동작) |
| **Windows 에서의 실제 실행** | **검증 못 함.** 이 저장소를 만든 환경은 Linux 다 |

마지막 항목 때문에 로직을 발명하지 않고 표준 명령만 조합했고, 단계마다 OK/실패를 찍어
**어디서 멈췄는지 바로 보이게** 했다. 막혔을 때 쓸 수동 클릭 절차는
[`docs/로컬-PC-리허설-체크리스트.md`](../../docs/로컬-PC-리허설-체크리스트.md) 경로 A 에 있다.
