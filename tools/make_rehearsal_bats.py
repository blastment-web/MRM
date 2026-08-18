# -*- coding: utf-8 -*-
"""리허설용 배치 파일 생성.

배치 파일은 반드시 CP949(한국어 Windows ANSI 코드페이지)로 저장한다.
UTF-8 로 저장하면 cmd 창에서 한글이 전부 깨져 안내문 자체가 쓸모없어진다.

## 배포 규칙 — 파일 이름이 곧 주소다

꾸러미 폴더의 `index-<이름>.html` 하나가 주소 하나가 된다.

    index-v4-1.html  ->  http://IP/v4-1/
    index-v5.html    ->  http://IP/v5/

배치를 고치지 않고 파일만 넣으면 버전이 늘어난다. 선택 화면도 배치가 함께
써 주는 `versions.js` 를 읽어 자동으로 카드를 늘린다 — 새 버전을 넣었는데
선택 화면에 안 보이면 "올렸는데 안 뜬다" 로 시간을 버리기 때문이다.

선택 화면 파일 이름이 `선택화면.html` 인 이유도 이 규칙 때문이다.
`index-` 로 시작하면 위 글롭에 걸려 엉뚱한 주소가 생긴다.

`agents\\` 는 버전 폴더 안에 넣지 않고 루트에 한 벌만 둔다. dashboards.json 의
addr 이 전체 URL 이라 버전과 무관하게 열리기 때문이다. 상대 경로로 읽히는
`data/dashboards.json` 만 버전 폴더마다 복사한다.
"""
from pathlib import Path

OUT = Path("/home/user/MRM/tools/rehearsal")
OUT.mkdir(parents=True, exist_ok=True)

START = r"""@echo off
setlocal enabledelayedexpansion
title MAPS 실험 서버 켜기

set "WWW=%SystemDrive%\inetpub\wwwroot"
set "MDATA=%SystemDrive%\inetpub\maps-data"
set "LOG=%TEMP%\maps-iis-setup.log"
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

rem ---------------- 2. 꾸러미 파일 확인 ----------------
rem index-<이름>.html 하나가 주소 하나가 된다. 몇 개든 상관없다.
if not exist "%~dp0선택화면.html" goto NOFILE
if not exist "%~dp0data\dashboards.json" goto NOFILE
set /a NV=0
for %%F in ("%~dp0index-*.html") do set /a NV+=1
if %NV%==0 goto NOVER
echo   [2/6] 꾸러미 파일 확인 ....... OK  -  화면 %NV%개

rem ---------------- 3. IIS 켜기 ----------------
rem IIS 가 켜져 있어도 ASP.NET 은 빠져 있을 수 있으므로 둘 다 확인한다.
set "ASPOK="
if exist "%windir%\Microsoft.NET\Framework64\v4.0.30319\aspnet_isapi.dll" set "ASPOK=1"
sc query w3svc >nul 2>&1
if not errorlevel 1 if defined ASPOK goto IISOK
echo   [3/6] IIS 켜는 중 ............ 처음이면 1~3분 걸립니다. 그대로 기다려 주세요.
echo MAPS IIS setup > "%LOG%"
rem ASP.NET 넷은 등록요청 업로드(api\dash-request.ashx)를 받기 위한 것이다.
rem .NET Framework 는 Windows 에 이미 들어 있어 새로 내려받을 것이 없다.
for %%F in (IIS-WebServerRole IIS-WebServer IIS-CommonHttpFeatures IIS-StaticContent IIS-DefaultDocument IIS-HttpErrors IIS-RequestFiltering IIS-WebServerManagementTools IIS-ManagementConsole NetFx4Extended-ASPNET45 IIS-NetFxExtensibility45 IIS-ISAPIExtensions IIS-ISAPIFilter IIS-ASPNET45) do (
    echo ---- %%F >> "%LOG%"
    dism /online /enable-feature /featurename:%%F /all /norestart >> "%LOG%" 2>&1
)
sc query w3svc >nul 2>&1
if errorlevel 1 goto NOIIS
set "ASPOK="
if exist "%windir%\Microsoft.NET\Framework64\v4.0.30319\aspnet_isapi.dll" set "ASPOK=1"
echo         IIS ................... 설치 완료
goto IISDONE
:IISOK
echo   [3/6] IIS .................... 이미 켜져 있음
:IISDONE

rem ---------------- 4. 배포 ----------------
if exist "%WWW%\index.html" if not exist "%WWW%\index.html.maps-backup" copy /y "%WWW%\index.html" "%WWW%\index.html.maps-backup" >nul
copy /y "%~dp0선택화면.html" "%WWW%\index.html" >nul
if errorlevel 1 goto NOCOPY

rem 선택 화면이 읽을 목록. 배열 끝의 쉼표는 자바스크립트에서 허용된다.
> "%WWW%\versions.js" echo window.MAPS_VERSIONS = [

set "SLUGS="
set "FIRST="
for %%F in ("%~dp0index-*.html") do (
    set "FN=%%~nF"
    set "SLUG=!FN:index-=!"
    if not exist "%WWW%\!SLUG!\data" mkdir "%WWW%\!SLUG!\data" >nul 2>&1
    copy /y "%%F" "%WWW%\!SLUG!\index.html" >nul
    rem 상대 경로로 읽히는 유일한 파일이라 버전 폴더마다 넣는다.
    copy /y "%~dp0data\dashboards.json" "%WWW%\!SLUG!\data\dashboards.json" >nul
    rem hero.mp4 를 넣어 두면 영상을 사내 홈페이지 대신 이 서버에서 받는다 (없으면 건너뛴다)
    if exist "%~dp0hero.mp4" copy /y "%~dp0hero.mp4" "%WWW%\!SLUG!\hero.mp4" >nul
    rem 앱이 api/* 를 상대 경로로 부르므로 화면 폴더마다 둔다 (data 와 같은 이유)
    if exist "%~dp0api" xcopy "%~dp0api" "%WWW%\!SLUG!\api" /e /i /y >nul 2>&1
    >> "%WWW%\versions.js" echo   {"slug":"!SLUG!"},
    set "SLUGS=!SLUGS! !SLUG!"
    if not defined FIRST set "FIRST=!SLUG!"
    echo         /!SLUG!/
)
>> "%WWW%\versions.js" echo ];

rem 올린 자료는 버전과 무관하게 한 벌만 둔다 (addr 이 전체 URL 이라 어디서든 열린다)
if exist "%~dp0agents" xcopy "%~dp0agents" "%WWW%\agents" /e /i /y >nul 2>&1
rem 업로드가 파일을 쓰는 곳은 이 두 폴더뿐이다. 나머지는 읽기 전용으로 남겨 둔다.
rem S-1-5-32-568 = IIS_IUSRS (언어팩과 무관하게 같은 SID 라 한글 Windows 에서도 통한다)
if not exist "%WWW%\agents"   mkdir "%WWW%\agents"   >nul 2>&1
icacls "%WWW%\agents"   /grant "*S-1-5-32-568:(OI)(CI)M" >nul 2>&1
rem 계정·세션·요청·승인 전 업로드 파일은 웹 루트 **밖**에 둔다.
rem wwwroot 안에 두면 http://IP/data/accounts.json 로 계정이 그대로 읽히고,
rem 승인 전 업로드 파일도 주소만 알면 열린다.
if not exist "%MDATA%\pending" mkdir "%MDATA%\pending" >nul 2>&1
icacls "%MDATA%" /grant "*S-1-5-32-568:(OI)(CI)M" >nul 2>&1
echo   [4/6] 화면 %NV%개 + 자료 배포 ... OK

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

rem ---------------- 실제로 뜨는지 확인 ----------------
set "C0="
if exist "%SystemRoot%\System32\curl.exe" (
    for /f %%C in ('curl -s -o nul -m 10 -w "%%{http_code}" "http://localhost/?v=%RANDOM%" 2^>nul') do set "C0=%%C"
)
echo --------------------------------------------------------------
if defined C0 (
    echo   자체 확인 : 선택 화면 !C0!    ^(200 이면 정상^)
    echo.
    echo   화면별 상태와 빌드 대조
    echo   ^(꾸러미와 서버의 빌드가 다르면 이 배치가 복사를 못 한 것입니다^)
    for %%S in (!SLUGS!) do (
        set "CODE=---"
        for /f %%C in ('curl -s -o nul -m 10 -w "%%{http_code}" "http://localhost/%%S/?v=%RANDOM%" 2^>nul') do set "CODE=%%C"
        call :BUILDOF "%~dp0index-%%S.html" BPKG
        curl -s -m 20 "http://localhost/%%S/?v=%RANDOM%" > "%TEMP%\maps-build-check.html" 2>nul
        call :BUILDOF "%TEMP%\maps-build-check.html" BSRV
        set "SAME=다름 - 배포 실패"
        if "!BPKG!"=="!BSRV!" set "SAME=같음"
        echo        /%%S/  !CODE!   꾸러미 !BPKG!   서버 !BSRV!   !SAME!
    )
    del /q "%TEMP%\maps-build-check.html" >nul 2>&1
    echo.
    echo   빌드가 "같음" 인데도 화면이 예전 그대로면 브라우저 캐시입니다.
    echo   그 화면에서 Ctrl+F5 를 누르세요. 화면 맨 아래에도 같은 값이 찍혀 있습니다.
) else (
    echo   자체 확인 : 건너뜀 - 브라우저에서 직접 확인하세요.
)
echo.
echo   내 PC 에서   http://localhost/
echo.
echo   동료에게 줄 주소
set "MYIP="
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=*" %%B in ("%%A") do (
        echo        http://%%B/
        if not defined MYIP set "MYIP=%%B"
    )
)
if not defined MYIP goto NOIP
echo.
echo   여러 줄이면 보통 10. 으로 시작하는 것이 사내 주소입니다.
echo   화면을 바로 열려면 뒤에 이름을 붙이세요.
for %%S in (!SLUGS!) do echo        http://!MYIP!/%%S/
goto SHOWEND
:NOIP
echo        사내 IP 를 찾지 못했습니다 - 네트워크 연결을 확인하세요
:SHOWEND
echo.
if defined ASPOK (
    echo   등록요청 받기 : 준비됨
    echo      관리자 1차 : admin   / maps2026!
    echo      관리자 2차 : manager / maps2026!
    echo      ^(오른쪽 위 "관리자 로그인" -^> 승인 관리 탭에서 1차·2차 승인^)
    echo      비밀번호를 바꾸려면 %MDATA%\accounts.json 을 지우고 이 배치를 다시 실행하세요.
) else (
    echo   등록요청 받기 : 안 됨 - ASP.NET 이 켜지지 않았습니다.
    echo                   화면에서는 "요청서 내려받기" 로 대신할 수 있습니다.
)
echo --------------------------------------------------------------

rem 주소 뒤의 ?v= 는 브라우저 캐시를 피하려는 것이다. 서버는 이 값을 무시한다.
start "" "http://localhost/?v=%RANDOM%"
goto END

rem ---------------- 빌드 스탬프 읽기 ----------------
rem %1 = HTML 파일, %2 = 결과를 담을 변수 이름.
rem 파일 안의  <meta name="maps-build" content="xxxxxxxx"><!--maps-build-stamp-->
rem 한 줄에서 8자리를 뽑는다. 꼬리 주석으로 그 한 줄만 걸리게 해 두었다
rem (maps-build 라는 낱말만 찾으면 이 값을 읽는 자바스크립트 줄까지 걸린다).
:BUILDOF
set "%~2=--------"
if not exist "%~1" goto :eof
set "BL="
for /f "delims=" %%L in ('findstr /c:"maps-build-stamp" "%~1" 2^>nul') do set "BL=%%L"
if not defined BL goto :eof
set "BL=!BL:*content=!"
set "%~2=!BL:~2,8!"
goto :eof

:NOADMIN
echo   [중단] 관리자 권한이 없습니다.
echo.
echo   이 파일을 마우스 우클릭 하고 "관리자 권한으로 실행" 을 눌러 주세요.
echo   그냥 더블클릭하면 아무것도 되지 않습니다.
goto END

:NOFILE
echo   [중단] 꾸러미에서 빠진 파일이 있습니다.
echo.
echo   이 폴더에 아래가 있어야 합니다.
echo        선택화면.html
echo        data\dashboards.json
echo   지금 폴더 : %~dp0
goto END

:NOVER
echo   [중단] 보여줄 화면 파일이 없습니다.
echo.
echo   이 폴더에 index-이름.html 형태의 파일이 최소 하나 있어야 합니다.
echo   예)  index-v4-1.html  ->  http://내IP/v4-1/
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
echo   [중단] 파일을 복사하지 못했습니다.
echo   대상 폴더 : %WWW%
goto END

:END
echo.
pause
"""

STOP = r"""@echo off
setlocal enabledelayedexpansion
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

rem 켤 때와 같은 목록을 훑어 자기가 만든 폴더만 지운다.
if exist "%WWW%\index.html"   del /f /q "%WWW%\index.html"   >nul 2>&1
if exist "%WWW%\versions.js"  del /f /q "%WWW%\versions.js"  >nul 2>&1
for %%F in ("%~dp0index-*.html") do (
    set "FN=%%~nF"
    set "SLUG=!FN:index-=!"
    if exist "%WWW%\!SLUG!" rd /s /q "%WWW%\!SLUG!" >nul 2>&1
)
if exist "%WWW%\agents" rd /s /q "%WWW%\agents" >nul 2>&1
if exist "%WWW%\data"   rd /s /q "%WWW%\data"   >nul 2>&1
echo   [3/4] 배치한 파일 삭제 ....... OK  (원본은 꾸러미 폴더에 그대로 있습니다)
rem %SystemDrive%\inetpub\maps-data 는 지우지 않는다 - 올라온 요청과 승인 이력이 들어 있다.
rem 완전히 지우려면 그 폴더를 직접 삭제하면 된다.

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
setlocal enabledelayedexpansion
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
echo   올린 자료는 모든 화면 버전에서 똑같이 열립니다.
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

rem 자료는 버전과 무관하게 한 벌만 둔다. addr 이 전체 URL 이라 어느 화면에서든 열린다.
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

rem 상대 경로로 읽히는 파일이라 화면 버전 폴더 모두에 반영해야 한다.
set "N=0"
for %%F in ("%~dp0index-*.html") do (
    set "FN=%%~nF"
    set "VER=!FN:index-=!"
    if exist "%WWW%\!VER!" (
        if not exist "%WWW%\!VER!\data" mkdir "%WWW%\!VER!\data" >nul 2>&1
        copy /y "%JSON%" "%WWW%\!VER!\data\dashboards.json" >nul
        set /a N+=1
    )
)
echo.
echo   화면 !N!개에 반영했습니다.
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

  관리자가 HTML 을 직접 연결할 때는 3_에이전트연결.bat 을 씁니다.
  구성원이 올린 요청은 화면의 관리자 콘솔에서 승인합니다 (아래 참고).


■ 화면을 하나 더 올리려면  ★ 파일 이름이 곧 주소입니다

  1. 올리고 싶은 HTML 파일의 이름을   index-이름.html   로 바꿉니다.
     이름은 영문/숫자/하이픈만 쓰세요.

         index-v5.html      ->   http://10.x.x.x/v5/
         index-test.html    ->   http://10.x.x.x/test/

  2. 그 파일을 이 폴더에 넣습니다.

  3. 1_서버켜기.bat 을 우클릭 -> "관리자 권한으로 실행" 을 다시 합니다.

  끝입니다. 새 주소가 생기고 선택 화면에도 카드가 자동으로 늘어납니다.
  검은 창 마지막에 지금 살아 있는 주소가 전부 찍힙니다.

  ※ 지우고 싶으면 그 index-이름.html 파일을 폴더에서 지우고
     2_서버끄기.bat -> 1_서버켜기.bat 순서로 다시 실행하세요.

  ※ 선택화면.html 은 이름에 index- 가 없습니다. 일부러 그렇게 두었습니다.
     그래야 선택 화면 자체가 주소로 만들어지지 않습니다.


■ 지금 들어 있는 화면

     index-v4-1.html    별자리 히어로.  외부 통신 0건.
     index-v4-2.html    영상 히어로.    첫 화면은 영상만, 대시보드는 아래 화면으로.
                        영상은 사내 홈페이지에서 받아오므로 외부 통신이 있습니다.

  두 주소는 동시에 살아 있습니다. 갈아 끼울 필요가 없습니다.
  화면 파일을 고쳐서 다시 올릴 때만 1_서버켜기.bat 을 한 번 더 실행하고,
  브라우저는 Ctrl+F5 로 새로고침하세요.


■ 원격 화면(사내 클라우드)에서 흐리거나 글자가 깨질 때  ★

  와이드 화면일수록 심합니다. 원인은 브라우저가 아니라 화면 전송입니다.
  원격 데스크톱은 화면을 영상처럼 압축해 보내는데, 배경이 계속 움직이면
  거기에 대역폭을 다 쓰고 주변 글자가 뭉개집니다.
  2560x1080 은 1920x1080 보다 픽셀이 33% 많아 넓은 화면에서만 티가 납니다.

  해결 : 화면 오른쪽 위 톱니바퀴 -> 설정 -> "원격 화면 최적화" 켜기

     배경 별자리를 초당 60번에서 20번 그리기로 낮추고, 흐림 효과와
     글자 등장 애니메이션을 끕니다. 전송량이 1/3 로 줄어 글자가 또렷해집니다.
     별자리 점의 위치와 개수는 그대로라 깜빡이거나 자리가 바뀌지 않습니다.

  대부분 자동으로 켜지지만, 자동 판단이 빗나갈 수 있습니다.
  흐리다고 느껴지면 설정에서 직접 켜 주세요. 한 번 고르면 기억합니다.

  ※ V4-2 영상이 처음에 느리다면, 영상을 사내 홈페이지에서 받아오기 때문입니다.
     hero.mp4 라는 이름의 영상 파일을 이 폴더에 넣고 1_서버켜기.bat 을 다시
     실행하면 이 서버에서 바로 받아 훨씬 빨라집니다. (파일이 없으면 지금처럼
     사내 홈페이지에서 받습니다 — 넣지 않아도 동작합니다)


■ AI Agent 한 건 연결해 보기

  동료가 만든 HTML 을 이 서버에 올려서 카드로 여는 절차입니다.
  백엔드가 없어도 됩니다. 카드는 주소가 채워지면 켜지도록 되어 있습니다.

  (1) 3_에이전트연결.bat 을 우클릭 -> "관리자 권한으로 실행"
  (2) 폴더 이름을 영문/숫자로 입력 (예: yield-check)
  (3) HTML 파일을 검은 창에 끌어다 놓고 Enter
  (4) 화면에 나온
          "addr":"http://10.x.x.x/agents/yield-check/"
      한 줄을 마우스로 드래그해서 복사 (선택 후 Enter 를 누르면 복사됩니다)
  (5) 아무 키나 누르면 메모장이 열립니다.
      연결할 Agent 를 찾아  "addr": ""  부분을 위 줄로 바꾸고
      저장한 다음 메모장을 닫으세요.
  (6) 메모장을 닫으면 배치가 모든 화면 버전에 반영하고 브라우저를 엽니다.

  카드가 "준비중" 에서 "● 사용 가능" 으로 바뀌고 누르면 그 페이지가 열립니다.
  올린 자료는 한 벌만 저장되며 어느 화면에서든 똑같이 열립니다.

  미리 넣어 둔 예시가 하나 있습니다.
  서버를 켜면 "공정 조건 최적화 Agent" 가 이미 켜져 있습니다.

  ※ 주의 : 예시 주소는 http://localhost/... 로 넣어 두었습니다.
     내 PC 에서는 열리지만 동료 PC 에서는 열리지 않습니다.
     동료에게 보여주려면 3_에이전트연결.bat 이 찍어 주는 실제 IP 주소로
     바꿔 주세요.


■ 구성원이 HTML 을 올리고, 관리자가 1차·2차 승인하면 카드가 생깁니다  ★

  전체 흐름
     구성원  화면의 [＋ AI Agent 등록] -> 항목 기입 + HTML 첨부 -> 요청 보내기
     관리자  1차 승인 (admin 계정)
     관리자  2차 승인 (manager 계정)   <- 여기서 카드가 생깁니다
     누구나  생긴 카드를 누르면 올린 HTML 이 팝업으로 열립니다

  ★ 올린다고 바로 공개되지 않습니다.
     2차 승인 전까지 그 파일은 웹에 아예 존재하지 않습니다. 주소를 알아도 못 엽니다.
     (C:\inetpub\maps-data 라는 웹 밖 폴더에 보관됩니다)

  관리자 계정 — 1_서버켜기.bat 이 처음 실행될 때 만들어집니다
     1차 : admin   / maps2026!
     2차 : manager / maps2026!

     같은 사람이 1차와 2차를 다 할 수 없습니다. admin 으로는 2차 버튼이 아예 안 보이고,
     manager 로는 1차 버튼이 안 보입니다. 서버에서도 같은 규칙을 막고 있습니다.

     비밀번호를 바꾸려면 C:\inetpub\maps-data\\accounts.json 을 지우고
     1_서버켜기.bat 을 다시 실행하세요. 새로 만들어집니다.

  승인하는 곳
     화면 오른쪽 위 [관리자 로그인] -> 관리자 콘솔이 열립니다
     -> "승인 관리" 탭 -> 올라온 요청 목록
     -> [1차 승인] / [1차 반려]  (admin 으로 로그인했을 때)
     -> [2차 승인] / [2차 반려]  (manager 로 로그인했을 때)
     반려하려면 사유를 적어야 하고, 1차·2차 처리 이력이 목록에 남습니다.
     ⬇ HTML 을 누르면 승인 전에도 첨부 파일을 받아 볼 수 있습니다.

  카드는 신청할 때 고른 카테고리에 생기고, 목록 맨 앞에 3일간 NEW 표시가 붙습니다.

  ※ 올릴 수 있는 것 : HTML 파일 1개, 3MB 까지.

  ※ 서버가 없어도 올라갑니다.
     ASP.NET 이 막혀 있거나 HTML 파일을 그냥 더블클릭해서 열었을 때도
     [요청 보내기] 를 누르면 카드가 바로 생기고, 카드를 누르면 올린 HTML 이 열립니다.
     다만 그때는 **올린 사람의 브라우저에만** 저장됩니다(동료에게는 안 보입니다).
     등록 창을 열면 지금이 어느 쪽인지 창 아래에 미리 알려 줍니다.

        서버 켜져 있음 : "서버에 올립니다 - 승인되면 모두에게 보입니다."
        서버 꺼져 있음 : "서버가 꺼져 있어 이 브라우저에 저장됩니다 ..."

     동료에게도 보이게 하려면 ASP.NET 이 켜진 상태에서 다시 올리면 됩니다.
     내 브라우저에만 있는 카드는 열어서 [삭제] 로 지웁니다.


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


■ 고쳤는데 화면이 예전 그대로일 때  ★

  화면마다 "빌드" 라는 8자리 표시가 붙어 있습니다. 같은 값이 세 군데 찍힙니다.

     (1) 이 폴더의 빌드.txt
     (2) 1_서버켜기.bat 을 실행하면 나오는 "화면별 상태와 빌드 대조" 줄
     (3) 화면 맨 아래 푸터의  build xxxxxxxx

  1_서버켜기.bat 이 이렇게 찍습니다.

     /v4-1/  200   꾸러미 645e2148   서버 645e2148   같음

  - "다름" 이면  -> 배치가 파일을 복사하지 못한 것입니다.
                   관리자 권한으로 1_서버켜기.bat 을 다시 실행하세요.
  - "같음" 인데 화면이 예전 그대로면  -> 브라우저가 옛 화면을 기억하고 있는 것입니다.
                   그 화면에서 Ctrl+F5 를 누르세요.
  - 푸터의 값이 빌드.txt 와 다르면  -> 새로 받은 꾸러미가 아니라 예전 폴더를 열고
                   있는 것입니다. 폴더 이름 뒤의 8자리와 zip 이름을 맞춰 보세요.

  ※ 이 값은 시각이 아니라 내용을 요약한 값입니다. 내용이 같으면 언제 만들어도
     같은 값이 나옵니다. 값이 달라졌다면 내용이 진짜로 달라진 것입니다.


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

  (2) C:\\inetpub\\wwwroot\\ 안에 아래처럼 넣습니다.
         index.html                 <- 선택화면.html 의 이름을 바꾼 것
         v4-1\\index.html            <- index-v4-1.html
         v4-1\\data\\dashboards.json
         v4-2\\index.html            <- index-v4-2.html
         v4-2\\data\\dashboards.json
         agents\\                    <- 이 폴더의 agents 폴더를 통째로
      (화면을 더 올렸다면 같은 방식으로 폴더를 하나 더 만들면 됩니다)

  (3) Windows Defender 방화벽 -> 고급 설정 -> 인바운드 규칙 -> 새 규칙
      -> 포트 -> TCP -> 특정 로컬 포트 80 -> 연결 허용 -> 이름 아무거나

  (4) 명령 프롬프트에서  ipconfig  실행 -> "IPv4 주소" 를 확인
      -> http://그주소/  를 동료에게 전달


■ 미리 알아 둘 것

  - 이 배치 파일들은 Windows 표준 명령(dism, copy, xcopy, netsh, net)만 씁니다.
    새로 설치하는 프로그램은 없습니다.

  - 이 PC 는 어디까지나 "실험용" 입니다. 개인 업무 PC 는 절전/재부팅으로
    수시로 끊기고, IP 도 바뀌면 공유한 주소가 전부 죽습니다.
    그래서 실제 운영은 새 PC 로 해야 합니다.

  - 개인 PC 포트를 여는 것이 사내 보안 정책에 걸릴 수 있습니다.
    우선 옆자리 1~2명에게만 보여주고, 부서 전체 공지는 IT 승인 후에 하세요.
"""

def write_bat(name: str, text: str) -> None:
    """CP949 로 못 쓰는 글자(— … 등)가 섞이면 어느 줄인지 알려 준다."""
    try:
        (OUT / name).write_bytes(text.replace("\n", "\r\n").encode("cp949"))
    except UnicodeEncodeError as e:
        ln = text[:e.start].count("\n") + 1
        raise SystemExit(f"[중단] {name} {ln}행: CP949 로 쓸 수 없는 글자 "
                         f"{text[e.start:e.end]!r} — 보통 - 이나 ... 로 바꾸면 된다.")


write_bat("1_서버켜기.bat", START)
write_bat("2_서버끄기.bat", STOP)
write_bat("3_에이전트연결.bat", CONNECT)
(OUT / "읽어보세요.txt").write_bytes(
    b"\xef\xbb\xbf" + README_TXT.replace("\n", "\r\n").encode("utf-8")
)

for stale in ("3_화면바꾸기.bat", "4_에이전트연결.bat", "4_요청확인.bat", "index-선택화면.html"):
    q = OUT / stale
    if q.exists():
        q.unlink()
        print("삭제:", stale)

print("생성:", *(p.name for p in sorted(OUT.iterdir())))
