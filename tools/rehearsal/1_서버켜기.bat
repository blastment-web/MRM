@echo off
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

rem 주소창에 IP 만 치면 바로 이 화면이 뜬다. 고르는 화면은 두지 않는다.
rem 다른 것을 기본으로 하고 싶으면 아래 한 줄의 이름만 바꾸면 된다
rem (index-v4-1.html 이면 v4-1). 그 이름의 화면이 없으면 첫 번째 화면을 쓴다.
set "MAIN=v4-2"

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
    set "SLUGS=!SLUGS! !SLUG!"
    if not defined FIRST set "FIRST=!SLUG!"
    echo         /!SLUG!/
)

rem 지정한 기본 화면이 없으면 첫 번째 것으로 대신한다.
if not exist "%WWW%\%MAIN%\index.html" set "MAIN=%FIRST%"
rem 루트에도 한 벌 놓는다. 앱이 data/ 와 api/ 를 상대 경로로 읽으므로 같이 옮긴다.
if not exist "%WWW%\data" mkdir "%WWW%\data" >nul 2>&1
copy /y "%WWW%\%MAIN%\index.html" "%WWW%\index.html" >nul
if errorlevel 1 goto NOCOPY
copy /y "%~dp0data\dashboards.json" "%WWW%\data\dashboards.json" >nul
if exist "%~dp0hero.mp4" copy /y "%~dp0hero.mp4" "%WWW%\hero.mp4" >nul
if exist "%~dp0api" xcopy "%~dp0api" "%WWW%\api" /e /i /y >nul 2>&1
echo         /            ^(%MAIN%^)

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
    echo   자체 확인 : 첫 화면 !C0!    ^(200 이면 정상^)
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
echo        index-이름.html  ^(하나 이상^)
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
