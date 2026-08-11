@echo off
setlocal enabledelayedexpansion
title MAPS - 올라온 등록요청 확인

set "WWW=%SystemDrive%\inetpub\wwwroot"
set "JSON=%~dp0data\dashboards.json"

echo.
echo ==============================================================
echo    올라온 등록요청 확인
echo ==============================================================
echo.

net session >nul 2>&1
if errorlevel 1 goto NOADMIN

if not exist "%WWW%\requests" goto NONE

set "MYIP="
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=*" %%B in ("%%A") do if not defined MYIP set "MYIP=%%B"
)
if not defined MYIP set "MYIP=localhost"

set /a N=0
for %%F in ("%WWW%\requests\*.txt") do (
    set /a N+=1
    echo --------------------------------------------------------------
    echo   [!N!]  폴더 이름 : %%~nF
    type "%%F"
    if exist "%WWW%\agents\%%~nF\index.html" (
        echo   미리 보기   : http://%MYIP%/agents/%%~nF/
        echo.
        echo   dashboards.json 에 붙여 넣을 줄:
        echo       "addr":"http://%MYIP%/agents/%%~nF/"
    ) else (
        echo   첨부 파일이 없는 요청입니다 ^(메타만 접수^)
    )
    echo.
)
if %N%==0 goto NONE

echo --------------------------------------------------------------
echo   위에서 공개할 것을 골라, 그 줄을 dashboards.json 의 해당 Agent
echo   "addr": "" 자리에 붙여 넣고 저장한 뒤 메모장을 닫으세요.
echo.
echo   ※ 붙여 넣기 전까지는 아무에게도 보이지 않습니다.
echo      올라와 있다고 공개된 것이 아닙니다.
echo.
pause

start /wait notepad "%JSON%"

set /a M=0
for %%F in ("%~dp0index-*.html") do (
    set "FN=%%~nF"
    set "VER=!FN:index-=!"
    if exist "%WWW%\!VER!" (
        if not exist "%WWW%\!VER!\data" mkdir "%WWW%\!VER!\data" >nul 2>&1
        copy /y "%JSON%" "%WWW%\!VER!\data\dashboards.json" >nul
        set /a M+=1
    )
)
echo.
echo   화면 !M!개에 반영했습니다. 브라우저에서 Ctrl+F5 로 새로고침하세요.
start "" "http://localhost/?v=%RANDOM%"
goto END

:NONE
echo   아직 올라온 등록요청이 없습니다.
echo.
echo   구성원이 화면에서 [＋ AI Agent 등록] 으로 HTML 을 올리면
echo   여기에 나타납니다.
echo.
echo   ※ 업로드가 안 되고 "요청서 내려받기" 만 뜬다면 ASP.NET 이 꺼져 있는 것입니다.
echo      1_서버켜기.bat 을 관리자 권한으로 다시 실행해 보세요.
goto END

:NOADMIN
echo   [중단] 관리자 권한이 없습니다.
echo   이 파일을 마우스 우클릭 하고 "관리자 권한으로 실행" 을 눌러 주세요.

:END
echo.
pause
