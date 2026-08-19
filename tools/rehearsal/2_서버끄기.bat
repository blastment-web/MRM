@echo off
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
if exist "%WWW%\hero.mp4"     del /f /q "%WWW%\hero.mp4"     >nul 2>&1
if exist "%WWW%\hero.webm"    del /f /q "%WWW%\hero.webm"    >nul 2>&1
rem 예전 판이 남긴 선택 화면 목록. 지금은 만들지 않지만 있으면 지운다.
if exist "%WWW%\versions.js"  del /f /q "%WWW%\versions.js"  >nul 2>&1
for %%F in ("%~dp0index-*.html") do (
    set "FN=%%~nF"
    set "SLUG=!FN:index-=!"
    if exist "%WWW%\!SLUG!" rd /s /q "%WWW%\!SLUG!" >nul 2>&1
)
if exist "%WWW%\agents" rd /s /q "%WWW%\agents" >nul 2>&1
if exist "%WWW%\data"   rd /s /q "%WWW%\data"   >nul 2>&1
if exist "%WWW%\api"    rd /s /q "%WWW%\api"    >nul 2>&1
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
