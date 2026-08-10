# 리허설 꾸러미 — 지금 쓰는 PC 를 잠깐 서버로

새 PC 를 들여오기 **전에** 지금 PC 로 "URL 하나로 동료에게 공유" 가 되는지만
확인하기 위한 최소 도구다. Python 도, 새로 설치할 프로그램도 없다.
Windows 에 이미 들어 있는 **IIS** 를 배치 파일로 켜고 끈다.

## 전달할 폴더 만들기

이 폴더의 파일 3개 + 화면 파일 1개를 한 폴더에 모아 압축해서 건넨다.

```bash
mkdir -p "MAPS-실험"
cp releases/MAPS-V4-1/index.standalone.html "MAPS-실험/index.html"
cp tools/rehearsal/1_서버켜기.bat tools/rehearsal/2_서버끄기.bat tools/rehearsal/읽어보세요.txt "MAPS-실험/"
```

`index.html` **이름이 중요하다.** IIS 가 기본 문서로 찾는 이름이고,
배치 파일도 그 이름을 복사한다.

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
| 2 | 같은 폴더에 `index.html` 이 있는지 확인 |
| 3 | `dism /online /enable-feature` 를 **기능마다 한 번씩** |
| 4 | `index.html` → `C:\inetpub\wwwroot\` 복사 (기존 파일은 `.maps-backup` 로 백업) |
| 5 | `netsh advfirewall` 로 인바운드 TCP 80 허용 (`MAPS-Rehearsal-HTTP-80`) |
| 6 | `sc config` + `net start w3svc` |
| 확인 | `curl` 로 `http://localhost/` 를 호출해 200 인지 보고, `ipconfig` 에서 사내 IP 를 찍는다 |

`2_서버끄기.bat` 는 4·5·6 을 되돌린다. **IIS 기능 자체는 끄지 않는다** —
끄면 재부팅을 요구할 수 있어 오히려 번거롭다.

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
| `index.html` (V4-1 standalone) | 헤드리스 Chromium 확인 — 별자리 히어로 렌더(잉크 0.85%), 카테고리 4, 공지 3, 게시판 8행, **외부 요청 0건 · JS 오류 0건** |
| **Windows 에서의 실제 실행** | **검증 못 함.** 이 저장소를 만든 환경은 Linux 다 |

마지막 항목 때문에 로직을 발명하지 않고 표준 명령만 조합했고, 단계마다 OK/실패를 찍어
**어디서 멈췄는지 바로 보이게** 했다. 막혔을 때 쓸 수동 클릭 절차는
[`docs/로컬-PC-리허설-체크리스트.md`](../../docs/로컬-PC-리허설-체크리스트.md) 경로 A 에 있다.
