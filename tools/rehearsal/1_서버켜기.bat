@echo off
setlocal enabledelayedexpansion
title MAPS 실험 서버 켜기

set "WWW=%SystemDrive%\inetpub\wwwroot"
set "LOG=%TEMP%\maps-iis-setup.log"
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
echo   [2/6] index.html 확인 ........ OK

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
echo   [4/6] 화면 파일 배치 ......... OK

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

rem ---------------- 스스로 확인 ----------------
set "CODE="
if exist "%SystemRoot%\System32\curl.exe" (
    for /f %%C in ('curl -s -o nul -m 5 -w "%%{http_code}" http://localhost/ 2^>nul') do set "CODE=%%C"
)

echo --------------------------------------------------------------
if "!CODE!"=="200" echo   자체 확인 : 화면이 정상적으로 응답합니다.
if defined CODE if not "!CODE!"=="200" echo   자체 확인 : 응답 코드 !CODE! - 아래 문제 해결을 보세요.
if not defined CODE echo   자체 확인 : 건너뜀 - 브라우저에서 직접 확인하세요.
echo.
echo   내 PC 에서  :  http://localhost/
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

start "" http://localhost/

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
