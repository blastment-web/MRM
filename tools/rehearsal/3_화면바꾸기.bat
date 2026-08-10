@echo off
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
