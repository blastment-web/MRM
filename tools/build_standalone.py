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

  P2  감속모션에서 스크롤 리빌이 통째로 사라진다
      `.reveal{opacity:1;transform:none;transition:none}` 이라 등장 자체가 없다.
      Windows "애니메이션 효과 표시" 끄기는 회사 PC 기본값이라 여기 걸리는
      환경이 많다. 멀미의 원인인 이동(translate)은 계속 막고, 페이드만 되살린다.

  P3  백엔드 없는 곳에서 화면이 비어 있다
      api/* · data/dashboards.json 요청이 프록시·캡티브포털을 만나면 즉시
      실패하지 않고 수십 초를 매달린다. 그 사이 STATE 가 비어 있어 TOP5 ·
      막대차트 · STATS 카운트업이 안 그려지고, boot() 는 12초 만에 포기한다.
      GET 요청에만 2.5초 타임아웃을 걸어 폴백 데이터로 즉시 넘어가게 한다.
      (POST 는 업로드가 있어 건드리지 않는다.)

  P4  구형 Safari 에서 부드러운 스크롤이 없다
      scroll-behavior 는 Safari 15.4 부터다. 미지원이면 rAF 로 대신 굴린다.

  P6  저사양 판정이 내려지면 배경 별자리가 사라진다
      applyTier() 가 점 개수(CAP·밀도)와 연결 거리(LINK)를 동시에 깎는다.
      연결선 수는 점²×거리² 에 비례하므로 두 축을 같이 줄이면 곱으로 무너진다.
      실측(1440x915): TIER0 캔버스의 1.634% → TIER1 0.111% = 15배 감소.
      TIER2 는 LINK=0 이라 연결선이 아예 0개고 점 22개만 남는다.
      감속모션(Windows "애니메이션 효과 표시" 끄기 = 회사 PC 기본값)이면 무조건
      TIER1 이라, 그런 PC 에서는 "뒤에 별자리가 안 나오는" 상태로 보인다.

      부하를 줄이는 실제 지렛대는 프레임 간격(FRAME_MS)과 dpr=1 이지 기하 밀도가
      아니다. 프레임 스로틀은 그대로 두고 밀도·연결거리만 되살린다.
      TIER0 은 한 값도 건드리지 않는다 — 일반 PC 의 모양은 지금 그대로다.

  P5  리빌 안전망 · 높이 재측정
      옵저버가 어떤 이유로든 놓친 .reveal 은 보이는 순간 강제로 켠다.
      내용이 다 들어온 뒤 resize 이벤트를 한 번 쏴 fitScreens 를 다시 재게 한다.

사용법:
    python3 tools/build_standalone.py                       # V3 → releases/MAPS-V3/index.standalone.html
    python3 tools/build_standalone.py <입력> <출력>
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = ROOT / "releases" / "MAPS-V3" / "index.html"
DEFAULT_OUT = ROOT / "releases" / "MAPS-V3" / "index.standalone.html"


# ---------------------------------------------------------------- P1
P1_FROM = "          if(!REDUCED) start();"
P1_TO = (
    "          start();   /* standalone: 감속모션이어도 재시작한다 — 부하는 LITE/TIER 가 낮춘다 */"
)

# ---------------------------------------------------------------- P2
P2_FROM = """  @media (prefers-reduced-motion:reduce){
    .reveal{opacity:1;transform:none;transition:none}
  }"""
P2_TO = """  @media (prefers-reduced-motion:reduce){
    /* standalone: 멀미의 원인은 이동이지 등장이 아니다 — translate 만 막고 페이드는 남긴다.
       (원본은 transition 까지 꺼서 감속모션 PC 에서 리빌이 통째로 사라졌다) */
    .reveal{opacity:0;transform:none;transition:opacity .5s ease}
    .reveal.in{opacity:1}
  }"""

# ---------------------------------------------------------------- P6
# 저부하 등급에서도 별자리가 읽히도록 밀도·연결거리를 되살린다.
# 비용은 프레임 스로틀(FRAME_MS)과 dpr=1 로 계속 억제한다.
#
#   1440x915(=1,317,600px) 기준 점 개수 · 상대 연결선량 · 상대 CPU
#     TIER0  78점 LINK150 60fps  → 선 1.00 · 부하 1.00   (변경 없음)
#     TIER1  60점 LINK150 24fps  → 선 0.59 · 부하 0.24   (기존 29점 LINK104 = 선 0.07)
#     TIER2  44점 LINK132 18fps  → 선 0.25 · 부하 0.10   (기존 22점 LINK0   = 선 0)
P6A_FROM = """    function applyTier(){
      if(TIER >= 2){      LINK = 0;   SPEED = 0.10; CAP = 22; FRAME_MS = 50; }
      else if(TIER >= 1){ LINK = 104; SPEED = 0.12; CAP = 34; FRAME_MS = 42; }
      else {              LINK = 150; SPEED = 0.30; CAP = 120; FRAME_MS = 0;  }
    }"""
P6A_TO = """    /* standalone: DENS(1점당 면적) · LALPHA(연결선 불투명도) 를 등급별로 함께 잡는다.
       저부하 등급에서 별자리가 사라지던 원인이 밀도와 연결거리의 동시 감축이었다. */
    var DENS = 17000, LALPHA = 0.42;
    function applyTier(){
      if(TIER >= 2){      LINK = 132; SPEED = 0.09; CAP = 44;  FRAME_MS = 55; DENS = 30000; LALPHA = 0.54; }
      else if(TIER >= 1){ LINK = 150; SPEED = 0.12; CAP = 64;  FRAME_MS = 42; DENS = 22000; LALPHA = 0.50; }
      else {              LINK = 150; SPEED = 0.30; CAP = 120; FRAME_MS = 0;  DENS = 17000; LALPHA = 0.42; }
    }"""

P6B_FROM = "      var target = Math.round(Math.min(CAP, Math.max(16, (w * h) / ((TIER >= 1) ? 38000 : 17000))));"
P6B_TO = "      var target = Math.round(Math.min(CAP, Math.max(16, (w * h) / DENS)));   /* standalone: 등급별 DENS */"

P6C_FROM = """          if(d2 < LINK*LINK){
            al = (1 - Math.sqrt(d2)/LINK) * 0.42;"""
P6C_TO = """          if(d2 < LINK*LINK){
            al = (1 - Math.sqrt(d2)/LINK) * LALPHA;   /* standalone: 선이 적은 등급일수록 진하게 */"""

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

  /* -------- P5) 리빌 안전망 — 옵저버가 놓친 요소를 보이는 순간 켠다 -------- */
  (function revealNet(){
    function sweep(){
      var els = document.querySelectorAll(".reveal:not(.in)");
      if(!els.length) return true;
      var vh = window.innerHeight || 0;
      for(var i=0;i<els.length;i++){
        var r = els[i].getBoundingClientRect();
        if(r.top < vh * 0.94 && r.bottom > 0) els[i].classList.add("in");
      }
      return false;
    }
    var ticking = false;
    function onScroll(){
      if(ticking) return;
      ticking = true;
      requestAnimationFrame(function(){ ticking = false; sweep(); });
    }
    window.addEventListener("scroll", onScroll, { passive:true });
    window.addEventListener("resize", onScroll, { passive:true });
    setTimeout(sweep, 600);
    setTimeout(sweep, 1600);
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


def patch(src_text: str) -> str:
    """치환을 하나라도 놓치면 조용히 넘어가지 않고 실패시킨다."""
    steps = [
        ("P1 파티클 재시작", P1_FROM, P1_TO),
        ("P2 감속모션 리빌 페이드", P2_FROM, P2_TO),
        ("P6a 등급별 밀도·연결거리 재조정", P6A_FROM, P6A_TO),
        ("P6b 점 개수 산식", P6B_FROM, P6B_TO),
        ("P6c 연결선 불투명도", P6C_FROM, P6C_TO),
        ("P3 오프라인 가드 주입", "<body>", GUARD),
        ("P4·P5 복원 레이어 주입", "</body>", RESILIENCE),
    ]
    out = src_text
    for label, needle, repl in steps:
        n = out.count(needle)
        if n != 1:
            raise SystemExit(f"[중단] {label}: 앵커를 {n}번 찾았습니다(1이어야 함) — 원본 구조가 바뀌었습니다.\n  앵커: {needle[:70]!r}")
        out = out.replace(needle, repl, 1)
        print(f"  ✓ {label}")
    return out


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    if not src.is_file():
        raise SystemExit(f"[중단] 입력 파일이 없습니다: {src}")

    text = src.read_text(encoding="utf-8")
    print(f"입력: {src.relative_to(ROOT)}  ({len(text):,} bytes)")
    result = patch(text)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result, encoding="utf-8")
    print(f"출력: {out.relative_to(ROOT)}  ({len(result):,} bytes)")


if __name__ == "__main__":
    main()
