#!/usr/bin/env python3
"""산출물에 **빌드 스탬프**를 박는다. 두 빌더(`build_v4.py` · `build_standalone.py`)가 공유한다.

## 왜 있는가

"고쳤는데 화면은 그대로" 가 세 번 반복됐다. 원인은 매번 달랐다 —
(1) IIS 가 복사본을 서빙하고 있었고, (2) 브라우저 캐시였고, (3) 새 꾸러미를 안 풀었다.
증상이 하나라 매번 추측으로 좁혀야 했다.

스탬프가 있으면 추측이 필요 없다. **화면·서버 응답·꾸러미 파일이 같은 값을 말하는지**
비교하면 원인이 두 갈래로 갈린다.

    화면 파일 빌드 != 서버 응답 빌드   ->  배포(복사)가 안 된 것
    두 값이 같은데 화면이 옛날         ->  브라우저 캐시

## 값의 성질

시각이 아니라 **내용 해시**다. 같은 입력을 두 번 빌드하면 값도 같다.
그래서 "빌드를 다시 돌렸는지" 가 아니라 "내용이 달라졌는지" 를 가리킨다 — 이쪽이 알고 싶은 것이다.

해시는 스탬프를 **제거한 상태**의 본문으로 계산한다. 그러지 않으면 스탬프가 스탬프를
바꾸는 순환이 된다. 이미 스탬프가 박힌 파일에 다시 적용해도 값이 안정적인 이유다.
"""

import hashlib
import re

# `<head>` 삽입 자리. 원본에 정확히 한 번 있어야 한다.
VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'

# 끝의 주석은 배치가 이 줄만 골라내기 위한 표시다. `maps-build` 라는 낱말만으로는
# 스탬프를 읽는 자바스크립트 한 줄까지 함께 잡혀 findstr 이 마지막 줄을 집는다.
STAMP_TAIL = "<!--maps-build-stamp-->"
META_RE = re.compile(r'\n<meta name="maps-build" content="[0-9a-f]{8}"><!--maps-build-stamp-->')
# 푸터는 스탬프가 있든 없든 둘 다 잡아 하나로 되돌린다.
FOOTER_RE = re.compile(
    r'<span>생산기술혁신센터 AI 플랫폼 (v[\d.]+)(?: · build [0-9a-f]{8})? · 사내 전용</span>'
)


def strip(html: str) -> str:
    """스탬프를 걷어낸 '알맹이'. 해시 계산과 재적용의 기준이다."""
    html = META_RE.sub("", html)
    return FOOTER_RE.sub(r"<span>생산기술혁신센터 AI 플랫폼 \1 · 사내 전용</span>", html)


def compute(html: str) -> str:
    return hashlib.sha256(strip(html).encode("utf-8")).hexdigest()[:8]


def apply(html: str) -> tuple[str, str]:
    """스탬프를 박은 본문과 그 값을 돌려준다. 앵커가 없으면 조용히 넘어가지 않고 중단한다."""
    base = strip(html)
    build = hashlib.sha256(base.encode("utf-8")).hexdigest()[:8]

    n = base.count(VIEWPORT)
    if n != 1:
        raise SystemExit(f"[중단] 빌드 스탬프: viewport 메타를 {n}번 찾았습니다(1이어야 함).")
    base = base.replace(
        VIEWPORT, VIEWPORT + f'\n<meta name="maps-build" content="{build}">{STAMP_TAIL}', 1
    )

    n = len(FOOTER_RE.findall(base))
    if n != 1:
        raise SystemExit(f"[중단] 빌드 스탬프: 푸터 문구를 {n}번 찾았습니다(1이어야 함).")
    base = FOOTER_RE.sub(
        r"<span>생산기술혁신센터 AI 플랫폼 \1 · build " + build + r" · 사내 전용</span>", base
    )
    return base, build


def read(html: str) -> str:
    """이미 박혀 있는 스탬프를 읽는다. 없으면 빈 문자열."""
    m = re.search(r'<meta name="maps-build" content="([0-9a-f]{8})">', html)
    return m.group(1) if m else ""
