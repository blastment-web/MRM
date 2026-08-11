@echo off
setlocal enabledelayedexpansion
title MAPS 실험 서버 켜기

set "WWW=%SystemDrive%\inetpub\wwwroot"
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
set "MISS="
for %%F in ("index-V4-1.html" "index-V4-2.html" "index-선택화면.html" "data\dashboards.json") do (
    if not exist "%~dp0%%~F" set "MISS=!MISS! %%~F"
)
if defined MISS goto NOFILE
echo   [2/6] 꾸러미 파일 확인 ....... OK

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

rem ---------------- 4. 배포 ----------------
rem 버전마다 폴더를 따로 둔다. 갈아 끼우지 않으므로 "바꿨는데 그대로" 가 생기지 않는다.
if exist "%WWW%\index.html" if not exist "%WWW%\index.html.maps-backup" copy /y "%WWW%\index.html" "%WWW%\index.html.maps-backup" >nul
if not exist "%WWW%\v4-1\data" mkdir "%WWW%\v4-1\data" >nul 2>&1
if not exist "%WWW%\v4-2\data" mkdir "%WWW%\v4-2\data" >nul 2>&1
copy /y "%~dp0index-선택화면.html" "%WWW%\index.html" >nul
copy /y "%~dp0index-V4-1.html"     "%WWW%\v4-1\index.html" >nul
copy /y "%~dp0index-V4-2.html"     "%WWW%\v4-2\index.html" >nul
rem 상대 경로로 읽히는 유일한 파일이라 두 폴더 모두에 넣는다. 원본은 꾸러미 폴더 한 곳뿐이라 어긋날 수 없다.
copy /y "%~dp0data\dashboards.json" "%WWW%\v4-1\data\dashboards.json" >nul
copy /y "%~dp0data\dashboards.json" "%WWW%\v4-2\data\dashboards.json" >nul
if errorlevel 1 goto NOCOPY
rem 올린 자료는 버전과 무관하게 한 벌만 둔다 (addr 이 전체 URL 이라 어디서든 열린다)
if exist "%~dp0agents" xcopy "%~dp0agents" "%WWW%\agents" /e /i /y >nul 2>&1
echo   [4/6] 화면 두 벌 + 자료 배포 . OK

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

rem ---------------- 세 주소가 실제로 뜨는지 확인 ----------------
set "C0="
set "C1="
set "C2="
if exist "%SystemRoot%\System32\curl.exe" (
    for /f %%C in ('curl -s -o nul -m 10 -w "%%{http_code}" "http://localhost/?v=%RANDOM%" 2^>nul') do set "C0=%%C"
    for /f %%C in ('curl -s -o nul -m 10 -w "%%{http_code}" "http://localhost/v4-1/?v=%RANDOM%" 2^>nul') do set "C1=%%C"
    for /f %%C in ('curl -s -o nul -m 10 -w "%%{http_code}" "http://localhost/v4-2/?v=%RANDOM%" 2^>nul') do set "C2=%%C"
)

echo --------------------------------------------------------------
if defined C0 echo   자체 확인 :  선택화면 !C0!    V4-1 !C1!    V4-2 !C2!    ^(200 이면 정상^)
if not defined C0 echo   자체 확인 : 건너뜀 - 브라우저에서 직접 확인하세요.
echo.
echo   내 PC 에서
echo        선택 화면    http://localhost/
echo        V4-1 별자리  http://localhost/v4-1/
echo        V4-2 영상    http://localhost/v4-2/
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
echo   버전을 바로 열려면 뒤에 v4-1/ 또는 v4-2/ 를 붙이세요.
echo        http://!MYIP!/v4-1/
echo        http://!MYIP!/v4-2/
goto SHOWEND
:NOIP
echo        사내 IP 를 찾지 못했습니다 - 네트워크 연결을 확인하세요
:SHOWEND
echo --------------------------------------------------------------

rem 주소 뒤의 ?v= 는 브라우저 캐시를 피하려는 것이다. 서버는 이 값을 무시한다.
start "" "http://localhost/?v=%RANDOM%"
goto END

:NOADMIN
echo   [중단] 관리자 권한이 없습니다.
echo.
echo   이 파일을 마우스 우클릭 하고 "관리자 권한으로 실행" 을 눌러 주세요.
echo   그냥 더블클릭하면 아무것도 되지 않습니다.
goto END

:NOFILE
echo   [중단] 꾸러미에서 빠진 파일이 있습니다 :!MISS!
echo.
echo   압축을 통째로 풀었는지 확인하세요. 폴더 안에 아래가 모두 있어야 합니다.
echo        index-V4-1.html  index-V4-2.html  index-선택화면.html
echo        data\dashboards.json
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
