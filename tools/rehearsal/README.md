# 리허설 꾸러미 — 지금 쓰는 PC 를 잠깐 서버로

새 PC 를 들여오기 **전에** 지금 PC 로 "URL 하나로 동료에게 공유" 가 되는지만
확인하기 위한 최소 도구다. Python 도, 새로 설치할 프로그램도 없다.
Windows 에 이미 들어 있는 **IIS** 를 배치 파일로 켜고 끈다.

## 전달할 폴더 만들기

이 폴더의 배치·안내 5개 + 화면 파일 3개 + `data/` + `agents/` 를 한 폴더에 모아 압축해서 건넨다.

```bash
mkdir -p "MAPS-실험"
cp releases/MAPS-V4-1/index.standalone.html "MAPS-실험/index-V4-1.html"
cp releases/MAPS-V4-2/index.standalone.html "MAPS-실험/index-V4-2.html"
cp releases/MAPS-V4-2/index.standalone.html "MAPS-실험/index.html"
cp tools/rehearsal/*.bat tools/rehearsal/읽어보세요.txt "MAPS-실험/"
cp -r tools/rehearsal/agents "MAPS-실험/"
mkdir -p "MAPS-실험/data"
python3 tools/make_dashboards_json.py --out "MAPS-실험/data/dashboards.json" \
        --live "공정 조건 최적화 Agent" --addr "http://localhost/agents/sample-agent/"
```

`index.html` **이름이 중요하다.** IIS 가 기본 문서로 찾는 이름이고,
배치 파일도 그 이름을 복사한다.
버전별 원본을 `index-V4-1.html` · `index-V4-2.html` 로 같이 넣는 이유는,
`index.html` 을 덮어써도 원본이 남아야 `3_화면바꾸기.bat` 이 되돌릴 수 있어서다.

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
| 2 | 같은 폴더에 `index.html` 이 있는지 확인 + **어느 버전인지 판정해 출력** + `index.html.html` 경고 |
| 3 | `dism /online /enable-feature` 를 **기능마다 한 번씩** |
| 4 | `index.html` → `C:\inetpub\wwwroot\` 복사 (기존 파일은 `.maps-backup` 로 백업) |
| 5 | `netsh advfirewall` 로 인바운드 TCP 80 허용 (`MAPS-Rehearsal-HTTP-80`) |
| 6 | `sc config` + `net start w3svc` |
| 확인 | `curl` 로 `http://localhost/?v=난수` 를 호출해 200 인지 보고, **응답 바이트에서 버전을 판정**해 찍고, `ipconfig` 에서 사내 IP 를 찍는다 |

`3_화면바꾸기.bat` 은 `1` 또는 `2` 를 받아 해당 버전을 폴더와 `wwwroot` 양쪽에 복사하고
캐시를 피한 주소로 브라우저를 다시 연다.

`4_에이전트연결.bat` 은 남이 만든 HTML 을 `agents/<폴더>/index.html` 로 올리고
붙여넣을 `"addr"` 한 줄을 실제 IP 로 찍어 준 뒤, `start /wait notepad` 로
`dashboards.json` 을 열고 **메모장이 닫히면 그 파일을 `wwwroot` 로 반영**한다.
편집 대상은 꾸러미 폴더의 원본이다 — `wwwroot` 쪽을 고치게 하면
`1_서버켜기.bat` 을 다시 돌릴 때 덮여 사라진다.

`2_서버끄기.bat` 는 4·5·6 을 되돌린다. **IIS 기능 자체는 끄지 않는다** —
끄면 재부팅을 요구할 수 있어 오히려 번거롭다.

## 화면이 안 바뀌는 문제 — 왜 생기고, 어떻게 잡았나

**서버가 읽는 파일은 `C:\inetpub\wwwroot\index.html` 이라는 복사본이다.**
폴더의 `index.html` 을 바꿔도 배치를 다시 돌려 복사하기 전까지 응답 바이트는 그대로다.
여기에 브라우저 캐시와 탐색기의 확장자 숨김(`index.html.html`)까지 겹치면
원인이 셋인데 화면은 하나라 사용자가 짚을 수가 없다.

그래서 배치가 **서버 응답 바이트를 직접 받아 판정**한다. 폴더의 파일이 아니라 응답을 본다.

```
서버가 지금 내보내는 화면 : V4-2 영상 히어로
```

판정은 `V4-1 = id="pxNet"` / `V4-2 = id="heroVideo"` 두 표식으로 한다.
두 파일은 크기 차이가 **2KB 안팎**(365,780 / 368,098)이라 탐색기 눈대중으로는 구분이 안 된다.

브라우저 캐시는 `web.config` 대신 **주소에 `?v=난수` 를 붙여** 피한다.
`web.config` 는 설정 섹션이 잠겨 있으면 **500.19** 로 사이트 전체를 죽인다 —
리허설 도구가 가질 실패 모드가 아니다. 동료에게 줄 주소는 쿼리 없이 따로 찍는다.

> **배치 문법 함정 하나.** `if 조건 명령 && set ...` 은 쓰면 안 된다.
> `if` 가 거짓이면 명령이 실행되지 않고 **직전 errorlevel 이 남아 `&&` 가 통과**한다.
> 버전 판정에 이 형태를 쓰면 V4-2 를 감지하고도 V4-1 로 덮어쓴다.
> `if` 없이 `findstr ... && set` 두 줄을 나란히 두는 방식으로 피했다.

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
| **Windows 에서의 실제 실행** | **검증 못 함.** 이 저장소를 만든 환경은 Linux 다 |

마지막 항목 때문에 로직을 발명하지 않고 표준 명령만 조합했고, 단계마다 OK/실패를 찍어
**어디서 멈췄는지 바로 보이게** 했다. 막혔을 때 쓸 수동 클릭 절차는
[`docs/로컬-PC-리허설-체크리스트.md`](../../docs/로컬-PC-리허설-체크리스트.md) 경로 A 에 있다.
