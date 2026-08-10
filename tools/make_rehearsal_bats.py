# -*- coding: utf-8 -*-
"""리허설용 배치 파일 생성.

배치 파일은 반드시 CP949(한국어 Windows ANSI 코드페이지)로 저장한다.
UTF-8 로 저장하면 cmd 창에서 한글이 전부 깨져 안내문 자체가 쓸모없어진다.
"""
from pathlib import Path

OUT = Path("/home/user/MRM/tools/rehearsal")
OUT.mkdir(parents=True, exist_ok=True)

START = r"""@echo off
setlocal enabledelayedexpansion
title MAPS 실험 서버 켜기

set "WWW=%SystemDrive%\inetpub\wwwroot"
set "LOG=%TEMP%\maps-iis-setup.log"
set "GOT=%TEMP%\maps-served.html"
set "SRC=%~dp0index.html"
set "RULE=MAPS-Rehearsal-HTTP-80"

echo.
echo ==============================================================
echo    MAPS 실험 서버 켜기
echo ==============================================================
echo.

rem ---------------- 1. 관리자 권한 ----------------
net session >nul 2>&1
if errorlevel 1 goto NOADMIN
echo   [1/6] 관리자 권한 ............ OK

rem ---------------- 2. 보여줄 파일 ----------------
if not exist "%SRC%" goto NOFILE
set "VER=V4-1 별자리 히어로"
findstr /m /c:"heroVideo" "%SRC%" >nul 2>&1 && set "VER=V4-2 영상 히어로"
echo   [2/6] index.html 확인 ........ OK  -  %VER%

rem 탐색기가 확장자를 숨기면 index.html 이 index.html.html 로 만들어진다.
rem 그러면 예전 index.html 이 그대로 남아 화면이 안 바뀐다. 여기서 잡는다.
if exist "%~dp0index.html.html" (
    echo.
    echo   [주의] 이 폴더에 index.html.html 이 있습니다.
    echo          탐색기의 "확장자 숨김" 때문에 생긴 이름입니다.
    echo          이름을 index 로만 바꿔야 실제 파일명이 index.html 이 됩니다.
    echo          지금 상태로는 예전 화면이 그대로 올라갑니다.
    echo.
)
echo         폴더 안의 HTML 파일 :
for /f "delims=" %%H in ('dir /b "%~dp0*.html" 2^>nul') do echo            %%H

rem ---------------- 3. IIS 켜기 ----------------
sc query w3svc >nul 2>&1
if not errorlevel 1 goto IISOK
echo   [3/6] IIS 켜는 중 ............ 처음이면 1~3분 걸립니다. 그대로 기다려 주세요.
echo MAPS IIS setup > "%LOG%"
for %%F in (IIS-WebServerRole IIS-WebServer IIS-CommonHttpFeatures IIS-StaticContent IIS-DefaultDocument IIS-HttpErrors IIS-RequestFiltering IIS-WebServerManagementTools IIS-ManagementConsole) do (
    echo ---- %%F >> "%LOG%"
    dism /online /enable-feature /featurename:%%F /all /norestart >> "%LOG%" 2>&1
)
sc query w3svc >nul 2>&1
if errorlevel 1 goto NOIIS
echo         IIS ................... 설치 완료
goto IISDONE
:IISOK
echo   [3/6] IIS .................... 이미 켜져 있음
:IISDONE

rem ---------------- 4. 화면 파일 배치 ----------------
if not exist "%WWW%" mkdir "%WWW%" >nul 2>&1
if exist "%WWW%\index.html" if not exist "%WWW%\index.html.maps-backup" copy /y "%WWW%\index.html" "%WWW%\index.html.maps-backup" >nul
copy /y "%SRC%" "%WWW%\index.html" >nul
if errorlevel 1 goto NOCOPY
for %%S in ("%WWW%\index.html") do echo   [4/6] 화면 파일 배치 ......... OK  -  %%~zS 바이트  %%~tS

rem 대시보드 목록(data)과 올려 둔 Agent(agents)도 같이 올린다. 없으면 조용히 넘어간다.
if exist "%~dp0data\dashboards.json" (
    xcopy "%~dp0data" "%WWW%\data" /e /i /y >nul 2>&1
    echo         data\dashboards.json .. OK
)
if exist "%~dp0agents" (
    xcopy "%~dp0agents" "%WWW%\agents" /e /i /y >nul 2>&1
    echo         agents\ ............... OK
)

rem ---------------- 5. 방화벽 ----------------
netsh advfirewall firewall delete rule name="%RULE%" >nul 2>&1
netsh advfirewall firewall add rule name="%RULE%" dir=in action=allow protocol=TCP localport=80 profile=any >nul 2>&1
if errorlevel 1 goto FWFAIL
echo   [5/6] 방화벽 TCP 80 열기 ..... OK
goto FWDONE
:FWFAIL
echo   [5/6] 방화벽 ................. 실패 - 나만 볼 수 있고 동료는 못 봅니다
:FWDONE

rem ---------------- 6. 웹 서비스 기동 ----------------
sc config w3svc start= auto >nul 2>&1
net start w3svc >nul 2>&1
if exist "%windir%\system32\inetsrv\appcmd.exe" "%windir%\system32\inetsrv\appcmd.exe" start site "Default Web Site" >nul 2>&1
echo   [6/6] 웹 서비스 기동 ......... OK
echo.

rem ---------------- 서버가 실제로 무엇을 내보내는지 확인 ----------------
rem 폴더의 파일이 아니라 "서버가 응답한 바이트" 를 보고 판정한다.
rem 화면이 안 바뀌는 문제는 여기서 바로 드러난다.
set "CODE="
set "SRVVER="
del /f /q "%GOT%" >nul 2>&1
if exist "%SystemRoot%\System32\curl.exe" (
    for /f %%C in ('curl -s -o "%GOT%" -m 10 -w "%%{http_code}" "http://localhost/?v=%RANDOM%" 2^>nul') do set "CODE=%%C"
)
rem 두 표식은 서로 배타적이다 - V4-1 에는 pxNet 만, V4-2 에는 heroVideo 만 있다.
rem `if ... && set` 은 if 가 거짓일 때 직전 errorlevel 로 && 가 통과해 버리므로 쓰지 않는다.
if exist "%GOT%" (
    findstr /m /c:"pxNet" "%GOT%" >nul 2>&1 && set "SRVVER=V4-1 별자리 히어로"
    findstr /m /c:"heroVideo" "%GOT%" >nul 2>&1 && set "SRVVER=V4-2 영상 히어로"
)

echo --------------------------------------------------------------
if "!CODE!"=="200" echo   자체 확인 : 서버가 정상 응답합니다.
if defined CODE if not "!CODE!"=="200" echo   자체 확인 : 응답 코드 !CODE! - 아래 문제 해결을 보세요.
if not defined CODE echo   자체 확인 : 건너뜀 - 브라우저에서 직접 확인하세요.
if defined SRVVER echo   서버가 지금 내보내는 화면 : !SRVVER!
echo.
echo   내 PC 에서  :  http://localhost/       화면이 안 바뀌면 Ctrl+F5
echo.
echo   동료에게    :
set "MYIP="
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=*" %%B in ("%%A") do (
        echo                  http://%%B/
        if not defined MYIP set "MYIP=%%B"
    )
)
if not defined MYIP echo                  사내 IP 를 찾지 못했습니다 - 네트워크 연결을 확인하세요
echo.
echo   여러 줄이 나오면 보통 10. 으로 시작하는 것이 사내 주소입니다.
echo   그 주소를 옆자리 동료에게 그대로 전달하세요. 그게 이번 실험의 핵심입니다.
echo --------------------------------------------------------------

rem 주소 뒤의 ?v= 는 브라우저 캐시를 피하려는 것이다. 서버는 이 값을 무시한다.
start "" "http://localhost/?v=%RANDOM%"

if "!CODE!"=="200" goto END
if not defined CODE goto END
echo.
echo   [문제 해결] 지금 80번 포트를 쓰고 있는 프로그램:
netstat -ano | findstr ":80 " | findstr LISTENING
echo.
echo   여기에 IIS 가 아닌 다른 프로그램이 보이면 그 프로그램이 80번을 먼저
echo   차지한 것입니다. 그 프로그램을 잠시 종료한 뒤 이 배치를 다시 실행하세요.
goto END

:NOADMIN
echo   [중단] 관리자 권한이 없습니다.
echo.
echo   이 파일을 마우스 우클릭 하고 "관리자 권한으로 실행" 을 눌러 주세요.
echo   그냥 더블클릭하면 아무것도 되지 않습니다.
goto END

:NOFILE
echo   [중단] 같은 폴더에 index.html 이 없습니다.
echo.
echo   이 배치 파일과 index.html 이 반드시 같은 폴더에 있어야 합니다.
echo   지금 폴더 : %~dp0
goto END

:NOIIS
echo   [중단] IIS 를 켜지 못했습니다.
echo.
echo   자세한 기록 : %LOG%
echo   회사 정책으로 Windows 기능 설치가 막혀 있을 수 있습니다.
echo   그럴 때는 읽어보세요.txt 의 "자동이 안 될 때" 를 따라 주세요.
goto END

:NOCOPY
echo   [중단] 화면 파일을 복사하지 못했습니다.
echo   대상 폴더 : %WWW%
goto END

:END
echo.
pause
"""

SWAP = r"""@echo off
setlocal
title MAPS 화면 바꾸기

set "WWW=%SystemDrive%\inetpub\wwwroot"

echo.
echo ==============================================================
echo    MAPS 화면 바꾸기
echo ==============================================================
echo.

net session >nul 2>&1
if errorlevel 1 goto NOADMIN

echo    1  -  V4-1   별자리 히어로   (외부 통신 없음)
echo    2  -  V4-2   영상 히어로     (영상을 사내 홈페이지에서 받아옵니다)
echo.
set "PICK="
set /p "PICK=1 또는 2 를 넣고 Enter, 취소는 그냥 Enter : "

if "%PICK%"=="1" (
    set "NEW=%~dp0index-V4-1.html"
    set "VER=V4-1 별자리 히어로"
)
if "%PICK%"=="2" (
    set "NEW=%~dp0index-V4-2.html"
    set "VER=V4-2 영상 히어로"
)
if not defined NEW goto CANCEL
if not exist "%NEW%" goto NOSRC

copy /y "%NEW%" "%~dp0index.html" >nul
copy /y "%NEW%" "%WWW%\index.html" >nul
if errorlevel 1 goto FAIL

echo.
echo   바꿨습니다 : %VER%
echo.
echo   브라우저가 곧 열립니다. 이미 열려 있던 창은 Ctrl+F5 로 새로고침하세요.
echo   동료에게 준 http://내IP/ 주소는 그대로 쓰면 됩니다.
start "" "http://localhost/?v=%RANDOM%"
goto END

:CANCEL
echo.
echo   취소했습니다. 아무것도 바꾸지 않았습니다.
goto END

:NOSRC
echo.
echo   [중단] 이 폴더에 %NEW% 가 없습니다.
echo   index-V4-1.html 과 index-V4-2.html 이 이 폴더에 있어야 합니다.
goto END

:FAIL
echo.
echo   [중단] 복사하지 못했습니다. 서버를 먼저 켜야 합니다.
echo   1_서버켜기.bat 을 우클릭 하고 "관리자 권한으로 실행" 하세요.
goto END

:NOADMIN
echo   [중단] 관리자 권한이 없습니다.
echo   이 파일을 마우스 우클릭 하고 "관리자 권한으로 실행" 을 눌러 주세요.

:END
echo.
pause
"""

STOP = r"""@echo off
setlocal
title MAPS 실험 서버 끄기

set "WWW=%SystemDrive%\inetpub\wwwroot"
set "RULE=MAPS-Rehearsal-HTTP-80"

echo.
echo ==============================================================
echo    MAPS 실험 서버 끄기 - 실험 흔적을 되돌립니다
echo ==============================================================
echo.

net session >nul 2>&1
if errorlevel 1 goto NOADMIN

netsh advfirewall firewall delete rule name="%RULE%" >nul 2>&1
echo   [1/4] 방화벽 규칙 삭제 ....... OK

net stop w3svc >nul 2>&1
sc config w3svc start= demand >nul 2>&1
echo   [2/4] 웹 서비스 중지 ......... OK

if exist "%WWW%\index.html" del /f /q "%WWW%\index.html" >nul 2>&1
if exist "%WWW%\data" rd /s /q "%WWW%\data" >nul 2>&1
if exist "%WWW%\agents" rd /s /q "%WWW%\agents" >nul 2>&1
echo   [3/4] 배치한 파일 삭제 ....... OK  (원본은 꾸러미 폴더에 그대로 있습니다)

if exist "%WWW%\index.html.maps-backup" goto RESTORE
echo   [4/4] 복원할 원본 없음 ....... OK
goto DONE
:RESTORE
move /y "%WWW%\index.html.maps-backup" "%WWW%\index.html" >nul 2>&1
echo   [4/4] 원래 있던 파일 복원 .... OK

:DONE
echo.
echo   되돌렸습니다. 동료가 열어 둔 주소도 이제 열리지 않습니다.
echo.
echo   ※ IIS 기능 자체는 켜 둔 채로 남겨 두었습니다.
echo      끄면 재부팅을 요구할 수 있어 오히려 번거롭기 때문입니다.
echo      완전히 지우려면 제어판 - 프로그램 - Windows 기능 켜기/끄기 에서
echo      "인터넷 정보 서비스" 체크를 해제하세요.
goto END

:NOADMIN
echo   [중단] 관리자 권한이 없습니다.
echo   이 파일을 마우스 우클릭 하고 "관리자 권한으로 실행" 을 눌러 주세요.

:END
echo.
pause
"""

CONNECT = r"""@echo off
setlocal
title MAPS - AI Agent 연결

set "WWW=%SystemDrive%\inetpub\wwwroot"
set "JSON=%~dp0data\dashboards.json"

echo.
echo ==============================================================
echo    AI Agent 한 건 연결하기
echo ==============================================================
echo.

net session >nul 2>&1
if errorlevel 1 goto NOADMIN
if not exist "%JSON%" goto NOJSON

echo   동료에게 받은 HTML 을 이 서버에 올리고,
echo   대시보드 카드에 붙일 주소 한 줄을 만들어 드립니다.
echo.

set "SLUG="
set /p "SLUG=1) 폴더 이름을 영문/숫자로 (예: yield-check) : "
if not defined SLUG goto CANCEL

set "SRCF="
set /p "SRCF=2) HTML 파일을 이 창에 끌어다 놓고 Enter : "
if not defined SRCF goto CANCEL
rem 끌어다 놓으면 경로에 따옴표가 함께 들어온다. 그대로 두면 따옴표가 겹친다.
set SRCF=%SRCF:"=%
if not exist "%SRCF%" goto NOSRC

if not exist "%~dp0agents\%SLUG%" mkdir "%~dp0agents\%SLUG%" >nul 2>&1
if not exist "%WWW%\agents\%SLUG%" mkdir "%WWW%\agents\%SLUG%" >nul 2>&1
copy /y "%SRCF%" "%~dp0agents\%SLUG%\index.html" >nul
copy /y "%SRCF%" "%WWW%\agents\%SLUG%\index.html" >nul
if errorlevel 1 goto FAIL

set "MYIP="
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=*" %%B in ("%%A") do if not defined MYIP set "MYIP=%%B"
)
if not defined MYIP set "MYIP=localhost"

echo.
echo   올렸습니다.  http://%MYIP%/agents/%SLUG%/
echo.
echo   --------------------------------------------------------
echo   아래 한 줄을 드래그해서 복사하세요 (마우스로 선택 후 Enter)
echo.
echo       "addr":"http://%MYIP%/agents/%SLUG%/"
echo.
echo   --------------------------------------------------------
echo.
echo   아무 키나 누르면 메모장이 열립니다.
echo   연결할 Agent 를 찾아  "addr": ""  부분을 위 줄로 바꾸고
echo   저장한 다음 메모장을 닫으세요.
echo.
pause

start /wait notepad "%JSON%"

if not exist "%WWW%\data" mkdir "%WWW%\data" >nul 2>&1
copy /y "%JSON%" "%WWW%\data\dashboards.json" >nul
echo.
echo   반영했습니다. 브라우저가 열리면 카드가 켜져 있어야 합니다.
echo   이미 열려 있던 창은 Ctrl+F5 로 새로고침하세요.
start "" "http://localhost/?v=%RANDOM%"
start "" "http://%MYIP%/agents/%SLUG%/"
goto END

:CANCEL
echo.
echo   취소했습니다. 아무것도 바꾸지 않았습니다.
goto END

:NOSRC
echo.
echo   [중단] 그런 파일이 없습니다 : %SRCF%
echo   탐색기에서 HTML 파일을 이 검은 창으로 끌어다 놓으면 경로가 정확히 입력됩니다.
goto END

:NOJSON
echo   [중단] 이 폴더에 data\dashboards.json 이 없습니다.
echo   꾸러미를 통째로 압축 해제했는지 확인하세요.
goto END

:FAIL
echo.
echo   [중단] 복사하지 못했습니다.
goto END

:NOADMIN
echo   [중단] 관리자 권한이 없습니다.
echo   이 파일을 마우스 우클릭 하고 "관리자 권한으로 실행" 을 눌러 주세요.

:END
echo.
pause
"""

README_TXT = """MAPS 실험 - 지금 쓰는 PC 를 잠깐 서버로 만들어 보기
====================================================

■ 3단계면 끝납니다

  1. 이 폴더의  1_서버켜기.bat  을 마우스 우클릭 -> "관리자 권한으로 실행"
     (그냥 더블클릭하면 안 됩니다. 반드시 우클릭입니다.)

  2. 검은 창에 나온  http://10.x.x.x/  주소를 옆자리 동료에게 전달

  3. 실험이 끝나면  2_서버끄기.bat  을 같은 방식으로 실행

  화면 버전 바꾸기는 3_화면바꾸기.bat, AI Agent 연결은 4_에이전트연결.bat 입니다.


■ 화면을 다른 버전으로 바꾸려면  ★ 여기가 헷갈리는 지점입니다

  가장 쉬운 방법 :
     3_화면바꾸기.bat  을 우클릭 -> "관리자 권한으로 실행" -> 1 또는 2 입력

  직접 바꾸고 싶다면 :
     (1) 이 폴더의 index.html 을 새 파일로 교체합니다.
         이름은 반드시 index.html 이어야 합니다.
         탐색기에서 확장자가 숨겨져 있으면 "index" 로만 바꿔야
         실제 파일명이 index.html 이 됩니다.
         ("index.html" 로 바꾸면 진짜 이름은 index.html.html 이 됩니다)

     (2) 1_서버켜기.bat 을 다시 우클릭 -> "관리자 권한으로 실행"

         ★ 이 단계를 빼면 화면은 바뀌지 않습니다.
           서버가 읽는 파일은  C:\\inetpub\\wwwroot\\index.html  이라는
           "복사본" 이기 때문입니다. 폴더의 파일을 바꿔도 복사를 다시
           해 주기 전까지는 예전 화면이 그대로 나갑니다.

     (3) 브라우저에서 Ctrl+F5 로 새로고침합니다.
         그냥 새로고침하면 브라우저에 저장된 예전 화면이 다시 뜹니다.

  1_서버켜기.bat 은 마지막에
      "서버가 지금 내보내는 화면 : V4-1 ..." 또는 "... V4-2 ..."
  를 찍어 줍니다. 이 줄이 실제 정답입니다. 이 줄이 원하는 버전이 아니면
  위 (1) 이나 (2) 에서 무언가 어긋난 것입니다.


■ AI Agent 한 건 연결해 보기  ★ 다음 확인 항목

  동료가 만든 HTML 을 이 서버에 올려서 카드로 여는 절차입니다.
  백엔드가 없어도 됩니다. 카드는 주소가 채워지면 켜지도록 되어 있습니다.

  (1) 4_에이전트연결.bat 을 우클릭 -> "관리자 권한으로 실행"
  (2) 폴더 이름을 영문/숫자로 입력 (예: yield-check)
      한글 폴더는 주소가 깨질 수 있어 영문을 권합니다.
  (3) HTML 파일을 검은 창에 끌어다 놓고 Enter
  (4) 화면에 나온
          "addr":"http://10.x.x.x/agents/yield-check/"
      한 줄을 마우스로 드래그해서 복사 (선택 후 Enter 를 누르면 복사됩니다)
  (5) 아무 키나 누르면 메모장이 열립니다.
      연결할 Agent 를 찾아  "addr": ""  부분을 위 줄로 바꾸고
      저장한 다음 메모장을 닫으세요.
  (6) 메모장을 닫으면 배치가 알아서 서버에 반영하고 브라우저를 엽니다.

  카드가 "준비중" 에서 "● 사용 가능" 으로 바뀌고 누르면 그 페이지가 열립니다.

  미리 넣어 둔 예시가 하나 있습니다.
  서버를 켜면 "공정 조건 최적화 Agent" 가 이미 켜져 있습니다.
  눌러 보면 확인용 페이지가 열립니다. 연결 경로가 살아 있다는 뜻입니다.

  ※ 주의 : 예시 주소는 http://localhost/... 로 넣어 두었습니다.
     내 PC 에서는 열리지만 동료 PC 에서는 열리지 않습니다.
     동료에게 보여주려면 4_에이전트연결.bat 이 찍어 주는 실제 IP 주소로
     바꿔 주세요.


■ 카드를 누르면 팝업으로 열립니다

  올린 HTML 은 새 탭이 아니라 MAPS 화면 안의 큰 팝업으로 열립니다.
  닫으면 보던 목록·검색어·스크롤 위치가 그대로 남습니다.

  - 닫기 : 오른쪽 위 X, 배경 클릭, ESC, 또는 브라우저 뒤로가기
  - 주소 : 팝업 아래쪽에 실제 주소가 보이고 [주소 복사] 로 복사됩니다
  - 팝업 상태의 주소(.../#agent=폴더이름)를 그대로 동료에게 보내면
    상대방 화면에서도 그 팝업이 열린 채로 뜹니다
  - [새 창] 을 누르면 별도 창으로, 8초가 지나도 안 뜨면 [새 탭에서 열기] 가
    나타납니다

  ※ 다른 서버의 대시보드 주소(예: http://10.31.24.11:8080/...)는 팝업이 아니라
     지금처럼 새 탭으로 열립니다. 남의 서버는 대개 다른 사이트 안에 표시되는
     것을 거부하도록 설정되어 있어, 팝업으로 열면 빈 화면이 되기 때문입니다.


■ 자료를 만들어 올리는 분께 (여러 명이 올릴 때 규칙)

  팝업 안의 페이지는 MAPS 본체와 분리된 상태로 실행됩니다.
  남이 만든 페이지가 MAPS 의 로그인 정보나 데이터에 손대지 못하게 하는
  안전장치인데, 그 대신 아래 제약이 생깁니다.

  (1) 되도록 HTML 파일 "한 개" 로 만들어 주세요.
      CSS·JS·데이터를 파일 안에 함께 넣으면 됩니다.
      옆에 둔 별도 파일을 코드로 불러오는 방식(fetch)은 막혀 있습니다.

  (2) 인터넷 주소의 라이브러리를 쓰지 마세요.
      사내망에서는 연결되지 않아 화면이 깨집니다. 파일 안에 넣어 주세요.

  (3) localStorage 는 쓸 수 없습니다. 값이 저장되지 않습니다.

  (4) 파일 이름은 index.html, 폴더 이름은 영문/숫자로.

  위 제약이 걸리는 자료라면 알려 주세요. 업로드 영역을 별도 주소로 분리하면
  제약 없이 쓸 수 있습니다(새 PC 구성 때 반영 예정).


■ 두 버전의 차이

  index-V4-1.html   별자리 히어로.  외부 통신 0건.
  index-V4-2.html   영상 히어로.    첫 화면은 영상만, 대시보드는 아래 화면으로 분리.
                    영상은 사내 홈페이지에서 받아오므로 외부 통신이 있습니다.


■ 확인할 것은 딱 하나입니다

  "동료 자리에서 그 주소로 MAPS 화면이 뜨는가"

  뜨면 -> 새 PC 를 들여서 똑같이 하면 됩니다. 방식이 검증된 것입니다.
  안 뜨면 -> 사내 네트워크가 PC 간 통신을 막고 있는 것입니다.
             이것도 중요한 결과입니다. 새 PC 신청서에 "서버망 배치 필요" 로
             적을 근거가 됩니다.


■ 자동이 안 될 때 (직접 클릭으로 하는 방법)

  1_서버켜기.bat 이 중간에 멈추면 아래를 순서대로 하면 같은 결과가 됩니다.

  (1) 제어판 -> 프로그램 -> "Windows 기능 켜기/끄기"
      -> "인터넷 정보 서비스" 체크 -> 확인 -> 설치 대기

  (2) 이 폴더의 index.html 을  C:\\inetpub\\wwwroot\\  안으로 복사
      (이름은 반드시 index.html 그대로)

  (3) Windows Defender 방화벽 -> 고급 설정 -> 인바운드 규칙 -> 새 규칙
      -> 포트 -> TCP -> 특정 로컬 포트 80 -> 연결 허용 -> 이름 아무거나

  (4) 명령 프롬프트에서  ipconfig  실행 -> "IPv4 주소" 를 확인
      -> http://그주소/  를 동료에게 전달


■ 미리 알아 둘 것

  - 이 배치 파일들은 Windows 표준 명령(dism, copy, netsh, net)만 씁니다.
    새로 설치하는 프로그램은 없습니다.

  - 이 PC 는 어디까지나 "실험용" 입니다. 개인 업무 PC 는 절전/재부팅으로
    수시로 끊기고, IP 도 바뀌면 공유한 주소가 전부 죽습니다.
    그래서 실제 운영은 새 PC 로 해야 합니다.

  - 개인 PC 포트를 여는 것이 사내 보안 정책에 걸릴 수 있습니다.
    우선 옆자리 1~2명에게만 보여주고, 부서 전체 공지는 IT 승인 후에 하세요.
"""

(OUT / "1_서버켜기.bat").write_bytes(START.replace("\n", "\r\n").encode("cp949"))
(OUT / "2_서버끄기.bat").write_bytes(STOP.replace("\n", "\r\n").encode("cp949"))
(OUT / "3_화면바꾸기.bat").write_bytes(SWAP.replace("\n", "\r\n").encode("cp949"))
(OUT / "4_에이전트연결.bat").write_bytes(CONNECT.replace("\n", "\r\n").encode("cp949"))
(OUT / "읽어보세요.txt").write_bytes(
    b"\xef\xbb\xbf" + README_TXT.replace("\n", "\r\n").encode("utf-8")
)
print("wrote", *(p.name for p in sorted(OUT.iterdir())))
