@echo off
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
