#!/usr/bin/env python3
"""MAPS 배포본 → 단독 실행용(standalone) HTML 빌더.

`index.html` 을 다른 PC · 다른 네트워크 · 사내 VDI 에서 그대로 열었을 때
히어로 파티클 · 스크롤 리빌 · 부드러운 스크롤 · STATS 카운트업이 죽는 문제를
고친 사본을 만든다. **원본은 수정하지 않는다** — 읽어서 치환한 결과를 따로 쓴다.

고치는 것 (전부 코드에서 원인이 확인된 것만):

  P1  히어로 파티클이 한 번 스크롤하면 영영 안 돌아온다
      IntersectionObserver 콜백이 `if(!REDUCED) start()` 로 묶여 있다.
      화면 밖 → stop() 은 무조건 걸리는데 재시작만 REDUCED 에서 막히니,
      감속모션 PC 에서는 히어로를 지나쳤다 돌아오면 배경이 정지한 채로 남는다.
      원본 주석("정지가 아니라 가볍게")대로 재시작은 항상 하고, 부하는
      이미 계산돼 있는 LITE/TIER 프로파일이 알아서 낮춘다.

  P7  감속모션 설정 하나에 효과 절반이 꺼진다
      원본은 OS 의 `prefers-reduced-motion` 을 CSS 4곳 · JS 2곳에서 읽어
      리빌 · 로고 펄스 · 스크롤 힌트 · 타일 트랜지션을 끄고, 파티클을 LITE 등급으로
      내린다. Windows "애니메이션 효과 표시" 끄기는 회사 PC 기본값이라, 로컬에서
      보던 화면과 딴판이 된다. standalone 은 **로컬과 동일한 화면**이 목적이므로
      이 게이트를 전부 무력화한다.
      (원본 index.html 은 접근성 설정을 그대로 존중한다. 이 무력화는 사본 전용이다.)

  P8  백엔드가 없어 공지 · 게시판 · Q&A · 자료공유가 텅 빈다
      로컬 미리보기(tools/build_preview.py)가 넣어 주던 샘플을 그대로 주입해
      목록 · 상세 · 댓글 · 좋아요 · 정렬 · 검색까지 실제로 눌러 볼 수 있게 한다.
      데이터는 tools/demo_data.py 하나를 두 빌더가 공유한다.

  P3  백엔드 없는 곳에서 화면이 비어 있다
      api/* · data/dashboards.json 요청이 프록시·캡티브포털을 만나면 즉시
      실패하지 않고 수십 초를 매달린다. 그 사이 STATE 가 비어 있어 TOP5 ·
      막대차트 · STATS 카운트업이 안 그려지고, boot() 는 12초 만에 포기한다.
      GET 요청에만 2.5초 타임아웃을 걸어 폴백 데이터로 즉시 넘어가게 한다.
      (POST 는 업로드가 있어 건드리지 않는다.)

  P4  구형 Safari 에서 부드러운 스크롤이 없다
      scroll-behavior 는 Safari 15.4 부터다. 미지원이면 rAF 로 대신 굴린다.

  P6  저부하 등급으로 떨어지면 배경 별자리가 사라진다 → 등급을 TIER 0 으로 고정
      applyTier() 가 점 개수(CAP·밀도)와 연결 거리(LINK)를 동시에 깎는다.
      연결선 수는 점²×거리² 에 비례하므로 두 축을 같이 줄이면 곱으로 무너진다.
      실측(1440x915): TIER0 캔버스의 1.634% → TIER1 0.111% = 15배 감소.
      TIER2 는 LINK=0 이라 연결선이 아예 0개고 점 22개만 남는다.
      standalone 은 로컬과 같은 화면이 목적이므로 등급을 TIER 0(60fps · 풀 밀도)
      으로 고정한다. 늘어나는 그리기 비용은 P9 드로우 콜 일괄화가 상쇄한다.

  P9  별자리가 깜빡이며 자리를 옮기고, 배경이 뚝뚝 끊긴다
      두 증상 모두 적응형 강등이 원인이다. 진입 직후에는 데이터 로드 · 리빌 ·
      카운트업이 겹쳐 어느 PC 든 프레임이 늦는 순간이 있는데, degrade() 가 그
      일시 부하를 영구 강등으로 오판한다(등급은 다시 오르지 않는다). 강등마다
      resize()→seed() 가 점 전체를 새 난수 위치에 다시 뿌려 "자리 바뀌고 또
      바뀌고", 강등이 끝나면 18~24fps 스로틀에 갇혀 "버벅"인다.

      a·b) 드로우 콜 일괄화 — 원본은 연결선 하나마다 상태 변경 + stroke 를
           반복한다(프레임당 수백 콜). 투명도를 8단계로 양자화해 단계마다 한
           번씩만 stroke 하면 8콜로 준다. 좌표·색·굵기는 그대로다.
           점도 색이 전부 같으므로 한 경로에 모아 한 번만 fill 한다.
      c)   강등 중지 — 판정 코드는 남기고 등급 변경만 하지 않는다.
      d)   크기가 실제로 바뀌지 않은 resize() 는 재배치하지 않는다 — P5 의
           fitScreens 용 resize 이벤트나 스크롤바 등장에도 seed() 가 돌아
           별자리가 통째로 자리를 바꿨다.

      결과(Chromium · CPU 10배 감속 스크롤): 재배치 점프 원본 1회 → 0회,
      평균 프레임 47.5ms ≈ 로컬 조건 원본 48.3ms. 로컬과 동등하다.

  P5  리빌 안전망 · 높이 재측정
      옵저버가 어떤 이유로든 놓친 .reveal 은 보이는 순간 강제로 켠다.
      내용이 다 들어온 뒤 resize 이벤트를 한 번 쏴 fitScreens 를 다시 재게 한다.

사용법:
    python3 tools/build_standalone.py                       # V3 → releases/MAPS-V3/index.standalone.html
    python3 tools/build_standalone.py <입력> <출력>
"""

import json
import sys
from pathlib import Path

from demo_data import BOARD, LOUNGE, SHARE

ROOT = Path(__file__).resolve().parent.parent


def latest_release() -> Path:
    """releases/MAPS-V<n>/ 중 번호가 가장 큰 것. 버전이 늘어도 손댈 필요가 없게."""
    dirs = []
    for d in (ROOT / "releases").glob("MAPS-V*"):
        if d.is_dir() and (d / "index.html").is_file():
            # "MAPS-V4-1" 처럼 마이너가 붙는 이름도 정렬되도록 튜플로 만든다
            parts = d.name[len("MAPS-V"):].split("-")
            if all(x.isdigit() for x in parts) and parts:
                dirs.append((tuple(int(x) for x in parts), d))
    if not dirs:
        raise SystemExit("[중단] releases/MAPS-V<n>/index.html 을 찾지 못했습니다.")
    return max(dirs)[1]


DEFAULT_DIR = latest_release()
DEFAULT_SRC = DEFAULT_DIR / "index.html"
DEFAULT_OUT = DEFAULT_DIR / "index.standalone.html"


# ---------------------------------------------------------------- P1
P1_FROM = "          if(!REDUCED) start();"
P1_TO = (
    "          start();   /* standalone: 감속모션이어도 재시작한다 — 배경이 정지한 채 남지 않게 */"
)

# ---------------------------------------------------------------- P7
# CSS 4곳: 조건을 절대 참이 되지 않게 바꿔 블록 전체를 죽인다.
# `not all` 은 어떤 매체에도 매치되지 않는 표준 표현이라, 블록을 지우지 않고도
# 원문이 무엇이었는지 그대로 남길 수 있다.
P7_CSS = [
    (
        "P7a 로고 펄스",
        "  @media (prefers-reduced-motion:reduce){#introStage .pls{display:none}}",
        "  @media not all{ /* standalone: 감속모션 게이트 해제 (원본: prefers-reduced-motion:reduce) */\n"
        "    #introStage .pls{display:none}}",
    ),
    (
        "P7b 타일·톱니 트랜지션",
        "  @media (prefers-reduced-motion:reduce){.cell,.gear{transition:none}}",
        "  @media not all{ /* standalone: 감속모션 게이트 해제 */\n"
        "    .cell,.gear{transition:none}}",
    ),
    (
        "P7c 스크롤 리빌",
        "  @media (prefers-reduced-motion:reduce){\n    .reveal{opacity:1;transform:none;transition:none}\n  }",
        "  @media not all{ /* standalone: 감속모션 게이트 해제 — 리빌을 로컬과 똑같이 살린다 */\n"
        "    .reveal{opacity:1;transform:none;transition:none}\n  }",
    ),
    (
        "P7d 스크롤 힌트",
        "  @media (prefers-reduced-motion:reduce){.scroll-hint::after{animation:none;opacity:.6}}",
        "  @media not all{ /* standalone: 감속모션 게이트 해제 */\n"
        "    .scroll-hint::after{animation:none;opacity:.6}}",
    ),
]

# JS 2곳: 판정 결과만 false 로 고정한다. matchMedia 호출 자체는 남겨 두어
# 원본이 무엇을 보고 있었는지 읽는 사람이 알 수 있게 한다.
P7_JS = [
    (
        "P7e 로고 애니메이션 판정",
        '  try{reduce=window.matchMedia("(prefers-reduced-motion:reduce)").matches;}catch(e){}',
        '  try{reduce=window.matchMedia("(prefers-reduced-motion:reduce)").matches;}catch(e){}\n'
        "  reduce=false;   /* standalone: 로컬과 동일한 화면이 목적이라 OS 설정을 따르지 않는다 */",
    ),
    (
        "P7f 파티클 등급 판정",
        '  try{ REDUCED = window.matchMedia("(prefers-reduced-motion:reduce)").matches; }catch(e){}',
        '  try{ REDUCED = window.matchMedia("(prefers-reduced-motion:reduce)").matches; }catch(e){}\n'
        "  REDUCED = false;   /* standalone: 로컬과 동일한 화면이 목적이라 OS 설정을 따르지 않는다 */",
    ),
]

# ---------------------------------------------------------------- P6
# 등급을 TIER 0 으로 고정한다 — 어떤 경로로든 저부하 등급에 들어가면 별자리가
# 사라지거나(LINK 축소) 재배치되므로(seed), 로컬과 같은 값 하나만 쓴다.
P6A_FROM = """    function applyTier(){
      if(TIER >= 2){      LINK = 0;   SPEED = 0.10; CAP = 22; FRAME_MS = 50; }
      else if(TIER >= 1){ LINK = 104; SPEED = 0.12; CAP = 34; FRAME_MS = 42; }
      else {              LINK = 150; SPEED = 0.30; CAP = 120; FRAME_MS = 0;  }
    }"""
P6A_TO = """    /* standalone: 등급을 항상 TIER 0(로컬 기본)으로 고정한다. 어느 등급이든
       원본은 강등 시 seed() 로 점을 새 난수 위치에 다시 뿌려 별자리가 깜빡이며
       자리를 옮겼고, 강등 후에는 18~24fps 스로틀에 갇혀 배경이 뚝뚝 끊겼다.
       그리기 비용은 아래 P9 일괄화가 줄이므로 60fps · 풀 밀도를 유지한다. */
    var DENS = 17000, LALPHA = 0.42;
    /* 연결선을 투명도 단계별로 모아 두는 버퍼. 매 프레임 length=0 으로 비우고
       재사용한다 — 프레임마다 배열을 새로 만들면 GC 가 스크롤 중에 튄다. */
    var BK = 8, LBUF = [[],[],[],[],[],[],[],[]];
    function applyTier(){
      LINK = 150; SPEED = 0.30; CAP = 120; FRAME_MS = 0;
    }"""

P6B_FROM = "      var target = Math.round(Math.min(CAP, Math.max(16, (w * h) / ((TIER >= 1) ? 38000 : 17000))));"
P6B_TO = "      var target = Math.round(Math.min(CAP, Math.max(16, (w * h) / DENS)));   /* standalone: TIER0 고정 밀도 */"

# ---------------------------------------------------------------- P9
# 그리기 비용 절감. 좌표·색·굵기는 그대로 두고 드로우 콜 수만 줄인다.
#
# 원본은 연결선 하나마다 strokeStyle 대입 + beginPath + stroke 를 반복한다.
# 78점이면 최대 3,003쌍이라 프레임당 수백~수천 번의 드로우 콜이 나간다.
# 캔버스는 상태 변경과 stroke 호출이 비싸므로, 투명도를 8단계로 양자화해
# 같은 단계끼리 한 경로에 모으면 드로우 콜이 8번으로 떨어진다.
# 양자화 폭은 0.42/8 ≈ 0.05 — 어두운 배경의 1px 선에서는 눈에 띄지 않는다.
P9A_FROM = """      /* 연결선 */
      for(i=0;i<pts.length;i++){
        a = pts[i];
        for(j=i+1;j<pts.length;j++){
          b = pts[j];
          dx = a.x-b.x; dy = a.y-b.y; d2 = dx*dx + dy*dy;
          if(d2 < LINK*LINK){
            al = (1 - Math.sqrt(d2)/LINK) * 0.42;
            ctx.strokeStyle = "rgba(120,190,255," + al.toFixed(3) + ")";
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
          }
        }
        /* 마우스 근처 강조 */
        dx = a.x-mouse.x; dy = a.y-mouse.y; d2 = dx*dx + dy*dy;
        if(d2 < 170*170){
          al = (1 - Math.sqrt(d2)/170) * 0.42;
          ctx.strokeStyle = "rgba(77,216,232," + al.toFixed(3) + ")";
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(mouse.x,mouse.y); ctx.stroke();
        }
      }"""
P9A_TO = """      /* 연결선 — standalone: 투명도를 BK 단계로 양자화해 단계마다 한 번씩만 stroke 한다.
         원본은 선 하나마다 상태 변경 + stroke 를 반복해 프레임당 드로우 콜이
         선 개수만큼 나갔다. 좌표·색·굵기는 그대로다. */
      var bi, bx, seg;
      for(bi=0;bi<BK;bi++) LBUF[bi].length = 0;
      for(i=0;i<pts.length;i++){
        a = pts[i];
        for(j=i+1;j<pts.length;j++){
          b = pts[j];
          dx = a.x-b.x; dy = a.y-b.y; d2 = dx*dx + dy*dy;
          if(d2 < LINK*LINK){
            al = 1 - Math.sqrt(d2)/LINK;
            bx = (al * BK) | 0; if(bx >= BK) bx = BK - 1; else if(bx < 0) bx = 0;
            LBUF[bx].push(a.x,a.y,b.x,b.y);
          }
        }
      }
      ctx.lineWidth = 1;
      for(bi=0;bi<BK;bi++){
        seg = LBUF[bi];
        if(!seg.length) continue;
        ctx.strokeStyle = "rgba(120,190,255," + (((bi + 0.5) / BK) * LALPHA).toFixed(3) + ")";
        ctx.beginPath();
        for(j=0;j<seg.length;j+=4){ ctx.moveTo(seg[j],seg[j+1]); ctx.lineTo(seg[j+2],seg[j+3]); }
        ctx.stroke();
      }
      /* 마우스 근처 강조 — 커서가 히어로 밖이면(-9999) 계산 자체를 건너뛴다 */
      if(mouse.x > -9000){
        for(bi=0;bi<BK;bi++) LBUF[bi].length = 0;
        for(i=0;i<pts.length;i++){
          a = pts[i];
          dx = a.x-mouse.x; dy = a.y-mouse.y; d2 = dx*dx + dy*dy;
          if(d2 < 28900){
            al = 1 - Math.sqrt(d2)/170;
            bx = (al * BK) | 0; if(bx >= BK) bx = BK - 1; else if(bx < 0) bx = 0;
            LBUF[bx].push(a.x,a.y);
          }
        }
        for(bi=0;bi<BK;bi++){
          seg = LBUF[bi];
          if(!seg.length) continue;
          ctx.strokeStyle = "rgba(77,216,232," + (((bi + 0.5) / BK) * 0.42).toFixed(3) + ")";
          ctx.beginPath();
          for(j=0;j<seg.length;j+=2){ ctx.moveTo(seg[j],seg[j+1]); ctx.lineTo(mouse.x,mouse.y); }
          ctx.stroke();
        }
      }"""

# 점도 같은 이유로 한 경로에 모은다. fillStyle 은 매 점마다 같은 값을 다시 넣고 있었다.
P9B_FROM = """      /* 점 */
      for(i=0;i<pts.length;i++){
        a = pts[i];
        ctx.fillStyle = "rgba(190,225,255,.78)";
        ctx.beginPath(); ctx.arc(a.x,a.y,a.r,0,Math.PI*2); ctx.fill();
      }"""
P9B_TO = """      /* 점 — standalone: 색이 전부 같으므로 한 경로에 모아 한 번만 fill 한다 */
      ctx.fillStyle = "rgba(190,225,255,.78)";
      ctx.beginPath();
      for(i=0;i<pts.length;i++){
        a = pts[i];
        ctx.moveTo(a.x + a.r, a.y);
        ctx.arc(a.x,a.y,a.r,0,Math.PI*2);
      }
      ctx.fill();"""

# 강등에서 "점을 다시 뿌리는" 축만 영구히 버리고, "프레임 수를 낮추는" 축은 되살린다.
#
# 원본 강등은 등급을 내릴 때마다 applyTier()+resize() 로 점 전체를 새 난수 위치에
# 다시 뿌려 "별자리가 깜빡이며 자리를 옮기는" 현상의 원인이 됐다. 그래서 한때 강등을
# 통째로 비워 뒀는데, 그러면 원격 데스크톱(사내 클라우드)에서 쓸 수단이 없어진다.
# 화면 전체를 60fps 로 다시 칠하면 화면 전송 인코더가 그 영역에 대역을 다 쓰고
# 주변 글자가 손실 압축으로 뭉개진다. 2560x1080 은 1920x1080 보다 픽셀이 33% 많아
# 같은 코드가 넓은 화면에서만 무너진다.
#
# 그래서 FRAME_MS 만 건드린다. 점 좌표·개수·연결거리는 그대로라 재배치가 원천적으로 없다.
#   - body.lite (설정의 "원격 화면 최적화" 또는 자동 감지) 면 곧바로 20fps
#   - 프레임 시간 실측이 나쁘면 30fps -> 20fps 로 한 단계씩만 (되돌리지 않는다)
# body.lite 를 끄면 60fps 로 복귀한다 — 사용자가 명시적으로 끈 것이므로 존중한다.
#
# 점 개수는 손대지 않는다. CAP=120 이 1920 에서도 2560 에서도 이미 걸려 있어
# (raw 122 / 163 -> 둘 다 120) 밀도 상한을 넣어도 실제로 바뀌는 값이 없다.
P9C_FROM = """        if(avg > 45 && TIER < 2){ TIER = 2; applyTier(); resize(); document.body.classList.add("lite"); }
        else if(avg > 28 && TIER < 1){ TIER = 1; applyTier(); resize(); document.body.classList.add("lite"); }"""
P9C_TO = """        /* standalone: 등급(점 밀도)은 절대 내리지 않는다 — applyTier()+resize() 가
           점을 다시 뿌려 깜빡임을 만든다. 프레임 수만 낮춘다. */
        if(avg > 45)      FRAME_MS = Math.max(FRAME_MS, 50);   /* 20fps */
        else if(avg > 28) FRAME_MS = Math.max(FRAME_MS, 33);   /* 30fps */"""

# body.lite 를 매 프레임 확인해 즉시 반영한다. classList 조회 한 번은 무시할 수 있는 비용이고,
# 설정 스위치를 켠 순간 바로 조용해지는 것이 사용자에게 훨씬 분명하다.
P9E_FROM = """    var acc = 0, cnt = 0, last = 0, nextAt = 0;
    function degrade(now){
      if(last){ acc += (now - last); cnt++; }"""
P9E_TO = """    var acc = 0, cnt = 0, last = 0, nextAt = 0, liteWas = null;
    function degrade(now){
      /* 원격 화면 최적화 스위치를 켜면 곧바로 20fps 로 내려간다. 점은 그대로다. */
      var lite = document.body.classList.contains("lite");
      if(lite !== liteWas){
        liteWas = lite;
        FRAME_MS = lite ? 50 : 0;
      }
      if(last){ acc += (now - last); cnt++; }"""

# 크기가 실제로 바뀌지 않았으면 재배치하지 않는다. 원본 resize() 는 호출될 때마다
# 무조건 seed() 로 점을 새 난수 위치에 뿌린다. fitScreens 를 깨우려고 쏘는 resize
# 이벤트(P5)나 스크롤바 등장 같은 1~2px 흔들림에도 별자리가 통째로 자리를 바꿨다.
P9D_FROM = """    function resize(){
      var r = hero.getBoundingClientRect();
      w = Math.max(1, Math.round(r.width));
      h = Math.max(1, Math.round(r.height));"""
P9D_TO = """    var pw = -1, ph = -1;   /* standalone: 마지막으로 seed 한 크기 */
    function resize(){
      var r = hero.getBoundingClientRect();
      w = Math.max(1, Math.round(r.width));
      h = Math.max(1, Math.round(r.height));
      /* standalone: 크기가 그대로면 재배치하지 않는다 — 별자리 자리 이동 방지 */
      if(cv.width > 0 && Math.abs(w - pw) < 3 && Math.abs(h - ph) < 3) return;
      pw = w; ph = h;"""

# ---------------------------------------------------------------- P3
GUARD = """<body>
<script>
/* ============================================================================
   MAPS standalone — 오프라인 가드 (script #1 보다 먼저 실행되어야 한다)
   백엔드가 없는 곳에서 GET 요청이 매달려 화면이 비는 것을 막는다.
   ============================================================================ */
(function(){
  "use strict";
  var F = window.fetch;
  if(typeof F !== "function" || typeof AbortController !== "function") return;
  var TIMEOUT = 2500;
  window.fetch = function(input, init){
    var url = (typeof input === "string") ? input : ((input && input.url) || "");
    var method = ((init && init.method) || (input && input.method) || "GET").toUpperCase();
    /* 외부 절대주소 · POST(업로드) · 이미 signal 을 쓰는 호출은 그대로 통과시킨다 */
    if(method !== "GET" || /^[a-z]+:\\/\\//i.test(url) || (init && init.signal)){
      return F.apply(window, arguments);
    }
    var ac = new AbortController();
    var opt = {};
    if(init) for(var k in init){ if(Object.prototype.hasOwnProperty.call(init, k)) opt[k] = init[k]; }
    opt.signal = ac.signal;
    var timer = setTimeout(function(){ try{ ac.abort(); }catch(e){} }, TIMEOUT);
    return F.call(window, input, opt).then(
      function(r){ clearTimeout(timer); return r; },
      function(e){ clearTimeout(timer); throw e; }
    );
  };
})();
</script>"""

# ---------------------------------------------------------------- P8
# 원본 로직은 건드리지 않는다. 전역 로더 함수만 데모 주입 버전으로 교체한다.
# SHARE_ITEMS / LG_POSTS / BOARD_POSTS / NOTICELIST 는 let 전역이라 별도
# classic script 에서도 같은 렉시컬 바인딩에 대입할 수 있다.
DEMO = """<script>
/* ============================================================================
   MAPS standalone — 데모 데이터 주입
   백엔드가 없어도 공지 · 자료공유 · Q&A · 게시판이 채워지도록 로더만 교체한다.
   내용은 tools/demo_data.py 에 있고 미리보기 빌드와 같은 것을 쓴다.
   ============================================================================ */
(function demoData(){
  "use strict";
  var DEMO_SHARE  = __SHARE__;
  var DEMO_LOUNGE = __LOUNGE__;
  var DEMO_BOARD  = __BOARD__;

  /* 공지는 건드리지 않는다 — script #3 의 NOTICE_SAMPLE 이 이미 8건을 갖고 있고
     `더보기 +` 토글까지 그 총계를 기준으로 돈다. 여기서 덮으면 오히려 줄어든다. */
  window.loadShare       = async function(){ SHARE_ITEMS = DEMO_SHARE;  renderShare(); };
  window.loadLounge      = async function(){ LG_POSTS    = DEMO_LOUNGE; lgRenderFeed(); };
  window.loadPosts       = async function(){ BOARD_POSTS = DEMO_BOARD;  PAGE_SHOWN = PAGE_SIZE; renderBoardRows(); };
  window.refreshBoardDot = async function(){};

  try{ loadShare(); }catch(e){}
  try{ lgRenderComposer(); loadLounge(); }catch(e){}
  try{ loadPosts(); }catch(e){}
})();
</script>
"""

# ---------------------------------------------------------------- P4 · P5
RESILIENCE = """<script>
/* ============================================================================
   MAPS standalone — 복원 레이어
   script #1·#2·#3 은 건드리지 않는다. 밖에서 보강만 한다.
   ============================================================================ */
(function(){
  "use strict";

  /* -------- P4) 부드러운 스크롤 — scroll-behavior 미지원 브라우저 대체 -------- */
  var NATIVE = false;
  try{ NATIVE = "scrollBehavior" in document.documentElement.style; }catch(e){}

  function navH(){
    try{
      var v = getComputedStyle(document.documentElement).getPropertyValue("--nav-h");
      return parseFloat(v) || 68;
    }catch(e){ return 68; }
  }
  function glide(to){
    var from = window.pageYOffset || document.documentElement.scrollTop || 0;
    var dist = to - from;
    if(Math.abs(dist) < 2){ window.scrollTo(0, to); return; }
    var dur = Math.min(900, Math.max(320, Math.abs(dist) * 0.55)), t0 = null;
    function frame(ts){
      if(t0 === null) t0 = ts;
      var p = Math.min(1, (ts - t0) / dur);
      var e = p < 0.5 ? 4*p*p*p : 1 - Math.pow(-2*p + 2, 3) / 2;   /* easeInOutCubic */
      window.scrollTo(0, Math.round(from + dist * e));
      if(p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  if(!NATIVE){
    /* 앵커 이동 — 원본 위임 핸들러(홈이 아닐 때만 가로챈다)와 겹치지 않게 마지막에 붙는다 */
    document.addEventListener("click", function(e){
      var a = (e.target && e.target.closest) ? e.target.closest('a[href^="#"]') : null;
      if(!a) return;
      var href = a.getAttribute("href");
      if(!href || href === "#") return;
      var t = null;
      try{ t = document.querySelector(href); }catch(err){ return; }
      if(!t) return;
      e.preventDefault();
      var top = t.getBoundingClientRect().top + (window.pageYOffset || 0) - navH();
      glide(Math.max(0, top));
    });
    /* 맨 위로 버튼 — 원본은 scrollTo({behavior:"smooth"}) 를 쓴다 */
    var top = document.getElementById("toTopBtn");
    if(top) top.addEventListener("click", function(e){ e.preventDefault(); glide(0); }, true);
  }

  /* -------- P5) 리빌 안전망 — 옵저버가 놓친 요소를 보이는 순간 켠다 --------
     스크롤마다 getBoundingClientRect 를 돌리면 매 프레임 레이아웃이 강제돼
     정작 스크롤이 버벅인다. 원본 옵저버가 이미 대부분을 처리하므로 여기서는
     남은 것만 저빈도 타이머로 훑고, 다 켜지면 스스로 멈춘다. */
  (function revealNet(){
    var left = document.querySelectorAll(".reveal").length;
    if(!left) return;
    var iv = setInterval(function(){
      var els = document.querySelectorAll(".reveal:not(.in)");
      if(!els.length){ clearInterval(iv); return; }      /* 할 일이 없으면 타이머를 끈다 */
      var vh = window.innerHeight || 0;
      for(var i=0;i<els.length;i++){
        var r = els[i].getBoundingClientRect();
        if(r.top < vh * 0.94 && r.bottom > 0) els[i].classList.add("in");
      }
    }, 500);
    setTimeout(function(){ clearInterval(iv); }, 60000);  /* 최후 보루 — 무한히 돌지 않는다 */
  })();

  /* -------- P5) 높이 재측정 — fitScreens 는 script #3 안의 지역 함수라
     직접 못 부른다. 원본이 걸어 둔 resize 리스너를 대신 깨운다. -------- */
  function nudge(){
    try{ window.dispatchEvent(new Event("resize")); }
    catch(e){
      try{ var ev = document.createEvent("Event"); ev.initEvent("resize", true, true); window.dispatchEvent(ev); }catch(e2){}
    }
  }
  if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", function(){ setTimeout(nudge, 0); });
  }else{
    setTimeout(nudge, 0);
  }
  setTimeout(nudge, 900);
  setTimeout(nudge, 2600);   /* 폴백 데이터까지 다 그려진 뒤 한 번 더 */
})();
</script>
</body>"""


def demo_block() -> str:
    """데모 데이터를 JSON 으로 박아 넣는다. `</script>` 가 문자열 안에 생기면
    브라우저가 스크립트를 거기서 끊으므로 이스케이프한다."""
    out = DEMO
    for token, data in (("__SHARE__", SHARE), ("__LOUNGE__", LOUNGE), ("__BOARD__", BOARD)):
        out = out.replace(token, json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    return out


# 별자리 파티클을 손보는 패치들. V4 부터 히어로가 배경 영상으로 바뀌어 이 코드가
# 아예 없으므로, 앵커가 0개면 "해당 없음"으로 건너뛴다. 다만 2개 이상이면 여전히
# 중단한다 — 그건 구조가 예상과 다르다는 뜻이지 부재가 아니다.
PARTICLE_STEPS = [
    ("P1 파티클 재시작", lambda: (P1_FROM, P1_TO)),
    ("P6a 등급 고정", lambda: (P6A_FROM, P6A_TO)),
    ("P6b 점 개수 산식", lambda: (P6B_FROM, P6B_TO)),
    ("P9a 연결선 드로우 콜 일괄화", lambda: (P9A_FROM, P9A_TO)),
    ("P9b 점 드로우 콜 일괄화", lambda: (P9B_FROM, P9B_TO)),
    ("P9e 원격 화면 스위치를 프레임 수에 반영", lambda: (P9E_FROM, P9E_TO)),
    ("P9c 강등을 프레임 수만 낮추도록 교체", lambda: (P9C_FROM, P9C_TO)),
    ("P9d 동일 크기 resize 의 재배치 차단", lambda: (P9D_FROM, P9D_TO)),
]


def patch(src_text: str) -> str:
    """치환을 하나라도 놓치면 조용히 넘어가지 않고 실패시킨다.
    단, 파티클 관련 패치는 대상 코드가 없는 버전(V4~)에서 건너뛴다."""
    optional = {label for label, _ in PARTICLE_STEPS}
    steps = [
        *[(label, *mk()) for label, mk in PARTICLE_STEPS],
        *P7_CSS,
        *P7_JS,
        ("P3 오프라인 가드 주입", "<body>", GUARD),
        ("P8·P4·P5 데모 데이터 + 복원 레이어 주입", "</body>", demo_block() + RESILIENCE),
    ]
    out = src_text
    for label, needle, repl in steps:
        n = out.count(needle)
        if n == 0 and label in optional:
            print(f"  – {label}: 해당 코드 없음 — 건너뜀")
            continue
        if n != 1:
            raise SystemExit(f"[중단] {label}: 앵커를 {n}번 찾았습니다(1이어야 함) — 원본 구조가 바뀌었습니다.\n  앵커: {needle[:70]!r}")
        out = out.replace(needle, repl, 1)
        print(f"  ✓ {label}")
    return out


def main() -> None:
    src = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SRC
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else DEFAULT_OUT
    if not src.is_file():
        raise SystemExit(f"[중단] 입력 파일이 없습니다: {src}")

    def show(p: Path) -> str:
        """저장소 안이면 짧게, 밖이면 절대경로 그대로."""
        try:
            return str(p.relative_to(ROOT))
        except ValueError:
            return str(p)

    text = src.read_text(encoding="utf-8")
    print(f"입력: {show(src)}  ({len(text):,} bytes)")
    result = patch(text)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result, encoding="utf-8")
    print(f"출력: {show(out)}  ({len(result):,} bytes)")


if __name__ == "__main__":
    main()
