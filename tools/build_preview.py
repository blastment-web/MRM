#!/usr/bin/env python3
"""index.html -> 디자인 미리보기 파일 생성 (Artifact 배포용).

백엔드(api/*)가 없는 환경에서도 화면 전체를 확인할 수 있도록,
원본에서 래퍼 태그를 벗겨내고 샘플 데이터 주입 shim 을 덧붙인다.

    python3 tools/build_preview.py [출력경로]

기본 출력: preview/aims-preview.html

원칙: **원본 index.html 은 절대 수정하지 않는다.**
추출(extract) + shim append 만 수행하며, shim 은 원본 로직을 고치는 대신
전역 로더 함수만 교체해 데모 데이터를 넣는다.
"""
import io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "index.html")
OUT = (sys.argv[1] if len(sys.argv) > 1
       else os.environ.get("AIMS_PREVIEW_OUT")
       or os.path.join(ROOT, "preview", "aims-preview.html"))

src = io.open(SRC, encoding="utf-8").read()

# 1) <style> ... </body> 직전까지 잘라낸다 (doctype/html/head/body 래퍼 제거)
i_style = src.index("<style>")
i_bodyend = src.rindex("</body>")
i_bodyopen = src.index("<body>")

head_css = src[i_style:src.index("</style>") + len("</style>")]
body_inner = src[i_bodyopen + len("<body>"):i_bodyend]

title = re.search(r"<title>(.*?)</title>", src, re.S).group(1)

# 2) 데모 데이터 — tools/demo_data.py 공용 ------------------------------------
from demo_data import NOTICES, SHARE, LOUNGE, BOARD  # noqa: E402

# 3) shim 스크립트 -----------------------------------------------------------
# 원본 로직은 건드리지 않는다. 전역 함수(classic script 최상위 함수 선언 =
# globalThis 프로퍼티)만 교체하고, let 으로 선언된 전역 렉시컬 바인딩에 직접 대입한다.
shim = """
<style>
  /* 미리보기 전용 — 원본 파일에는 없는 스타일 */
  #pvBadge{position:fixed;left:16px;bottom:16px;z-index:55;display:flex;align-items:center;gap:9px;
    max-width:min(92vw,420px);padding:9px 14px;border-radius:999px;
    background:rgba(13,19,34,.92);border:1px solid var(--panel-line);
    backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
    box-shadow:0 8px 28px rgba(0,0,0,.45);
    font-size:12px;font-weight:600;color:var(--txt-dim);letter-spacing:-0.01em}
  #pvBadge .pv-dot{width:7px;height:7px;border-radius:50%;background:var(--accent);flex-shrink:0;
    box-shadow:0 0 0 3px rgba(77,216,232,.16)}
  #pvBadge b{color:var(--txt);font-weight:700}
  #pvBadge .pv-x{margin-left:2px;background:none;border:none;color:var(--txt-faint);
    cursor:pointer;font-size:15px;line-height:1;padding:2px 0 2px 4px}
  #pvBadge .pv-x:hover{color:var(--txt)}
  @media(max-width:560px){#pvBadge{left:10px;right:10px;bottom:84px;max-width:none;font-size:11px}}
  /* 디자인 조정 패널 — 미리보기 전용, index.html 에는 없다 */
  #pvTuneBtn{position:fixed;left:16px;bottom:62px;z-index:57;
    background:rgba(13,19,34,.94);border:1px solid var(--panel-line);color:var(--txt-dim);
    font-family:inherit;font-size:12px;font-weight:700;padding:8px 14px;border-radius:999px;
    cursor:pointer;box-shadow:0 8px 28px rgba(0,0,0,.45);
    backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
  #pvTuneBtn:hover{border-color:rgba(77,216,232,.5);color:var(--accent)}
  #pvTune{position:fixed;left:16px;bottom:62px;z-index:58;width:330px;max-height:calc(100vh - 140px);
    overflow:auto;display:none;flex-direction:column;gap:2px;padding:14px 16px 12px;border-radius:16px;
    background:rgba(9,13,24,.97);border:1px solid var(--panel-line);
    box-shadow:0 18px 50px rgba(0,0,0,.6);
    backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
  #pvTune.open{display:flex}
  #pvTune h4{font-size:13px;font-weight:800;color:var(--txt);margin-bottom:2px;
    display:flex;align-items:center;justify-content:space-between}
  #pvTune h4 button{background:none;border:none;color:var(--txt-faint);font-size:17px;
    line-height:1;cursor:pointer;padding:0 2px;font-family:inherit}
  #pvTune h4 button:hover{color:var(--txt)}
  #pvTune .pv-hint{font-size:11px;color:var(--txt-faint);line-height:1.6;margin-bottom:8px}
  #pvTune .pv-sec{font-size:10.5px;font-weight:800;letter-spacing:.1em;color:var(--accent);
    margin:9px 0 3px;text-transform:uppercase}
  #pvTune .pv-row{display:grid;grid-template-columns:1fr 58px;align-items:center;gap:8px;padding:3px 0}
  #pvTune .pv-row label{font-size:12px;color:var(--txt-dim);font-weight:600}
  #pvTune .pv-row output{font-size:11.5px;color:var(--txt);font-variant-numeric:tabular-nums;
    text-align:right;font-weight:700}
  #pvTune input[type=range]{grid-column:1 / -1;width:100%;margin:0;accent-color:var(--accent);height:18px}
  #pvTune .pv-acts{display:flex;gap:7px;margin-top:11px}
  #pvTune .pv-acts button{flex:1;font-family:inherit;font-size:12px;font-weight:700;padding:8px 0;
    border-radius:9px;cursor:pointer;border:1px solid var(--panel-line);
    background:rgba(255,255,255,.05);color:var(--txt-dim)}
  #pvTune .pv-acts button:hover{border-color:rgba(77,216,232,.5);color:var(--accent)}
  #pvTune .pv-acts .pv-copy{background:var(--grad);color:#04121a;border-color:transparent}
  #pvTune textarea{width:100%;margin-top:9px;height:62px;resize:vertical;font-size:11px;
    font-family:ui-monospace,SFMono-Regular,Menlo,monospace;line-height:1.5;
    background:var(--ink);border:1px solid var(--panel-line);border-radius:9px;color:var(--txt);padding:8px 10px}
  @media(max-width:900px){#pvTune,#pvTuneBtn{display:none}}
</style>
<button id="pvTuneBtn" type="button">🎛 디자인 조정</button>
<div id="pvTune">
  <h4>🎛 디자인 조정<button type="button" id="pvTuneX" aria-label="닫기">&times;</button></h4>
  <div class="pv-hint">슬라이더를 움직이면 화면에 바로 반영됩니다. 마음에 드는 값이 나오면
    <b>설정값 복사</b>를 눌러 나온 한 줄을 그대로 알려주세요. 그대로 반영해 드립니다.</div>
  <div class="pv-sec">공통</div>
  <div class="pv-row"><label>좌우 여백</label><output id="o_gut"></output>
    <input type="range" id="r_gut" min="16" max="220" step="2"></div>
  <div class="pv-sec">대시보드</div>
  <div class="pv-row"><label>히어로 크기</label><output id="o_hero"></output>
    <input type="range" id="r_hero" min="0.75" max="1.45" step="0.01" value="1"></div>
  <div class="pv-row"><label>현황·차트·공지 크기</label><output id="o_panel"></output>
    <input type="range" id="r_panel" min="0.75" max="1.45" step="0.01" value="1"></div>
  <div class="pv-row"><label>조직 버튼 크기</label><output id="o_chip"></output>
    <input type="range" id="r_chip" min="0.75" max="1.6" step="0.01" value="1"></div>
  <div class="pv-sec">TOP5</div>
  <div class="pv-row"><label>카드 글자 크기</label><output id="o_t5"></output>
    <input type="range" id="r_t5" min="0.75" max="1.45" step="0.01" value="1"></div>
  <div class="pv-row"><label>카드 높이</label><output id="o_t5h"></output>
    <input type="range" id="r_t5h" min="0.6" max="1.3" step="0.01" value="1"></div>
  <div class="pv-sec">카테고리별 AI Agent</div>
  <div class="pv-row"><label>카드 글자 크기</label><output id="o_card"></output>
    <input type="range" id="r_card" min="0.75" max="1.45" step="0.01" value="1"></div>
  <div class="pv-acts">
    <button type="button" id="pvReset">초기화</button>
    <button type="button" class="pv-copy" id="pvCopy">설정값 복사</button>
  </div>
  <textarea id="pvOut" readonly spellcheck="false"></textarea>
</div>
<div id="pvBadge">
  <span class="pv-dot"></span>
  <span><b>디자인 미리보기</b> · 백엔드 미연결, 화면 확인용 샘플 데이터</span>
  <button class="pv-x" type="button" aria-label="배너 닫기">&times;</button>
</div>
<script>
(function previewShim(){
  "use strict";
  var DEMO_NOTICES = __NOTICES__;
  var DEMO_SHARE   = __SHARE__;
  var DEMO_LOUNGE  = __LOUNGE__;
  var DEMO_BOARD   = __BOARD__;

  /* 디자인 조정 패널 — CSS 변수만 바꾼다. index.html 로직은 건드리지 않는다. */
  (function tunePanel(){
    var box = document.getElementById("pvTune"), btn = document.getElementById("pvTuneBtn");
    if(!box || !btn) return;
    var root = document.documentElement;
    var KEYS = [
      {id:"gut",   v:"--gut",         unit:"px"},
      {id:"hero",  v:"--hero-scale",  unit:"x"},
      {id:"panel", v:"--panel-scale", unit:"x"},
      {id:"chip",  v:"--chip-scale",  unit:"x"},
      {id:"t5",    v:"--t5-scale",    unit:"x"},
      {id:"t5h",   v:"--t5-h",        unit:"x"},
      {id:"card",  v:"--card-scale",  unit:"x"}
    ];
    /* --gut 은 clamp() 라 커스텀 속성 값을 직접 읽으면 NaN 이 된다.
       .sec-inner 의 padding 이 var(--gut) 이므로 그 해석된 px 을 읽는다.
       슬라이더를 건드리기 전에는 --gut 을 고정하지 않는다 — 반응형을 죽이면 안 된다. */
    var gutTouched = false;
    function readGut(){
      var probe = document.querySelector("#secTop5 .sec-inner") || document.querySelector(".sec-inner");
      return probe ? Math.round(parseFloat(getComputedStyle(probe).paddingLeft)) : 96;
    }
    var DEF_GUT = readGut() || 96;
    document.getElementById("r_gut").value = DEF_GUT;

    function refit(){ window.dispatchEvent(new Event("resize")); }
    function paint(){
      var out = [];
      KEYS.forEach(function(k){
        var r = document.getElementById("r_" + k.id), o = document.getElementById("o_" + k.id);
        var val = r.value;
        if(k.unit === "px"){
          o.textContent = val + "px";
          if(gutTouched){
            root.style.setProperty(k.v, val + "px");
            if(+val !== DEF_GUT) out.push(k.v + ":" + val + "px");
          }
        }
        else { o.textContent = (+val).toFixed(2) + "x"; root.style.setProperty(k.v, val);
               if(+val !== 1) out.push(k.v + ":" + (+val).toFixed(2)); }
      });
      document.getElementById("pvOut").value = out.length
        ? ":root{" + out.join(";") + "}"
        : "기본값 그대로입니다 (바꾼 항목 없음).";
      refit();
    }
    KEYS.forEach(function(k){
      document.getElementById("r_" + k.id).addEventListener("input", function(){
        if(k.id === "gut") gutTouched = true;
        paint();
      });
    });
    /* 손대지 않았으면 창 크기에 따라 기본 여백이 달라지므로 눈금을 따라간다 */
    window.addEventListener("resize", function(){
      if(gutTouched) return;
      setTimeout(function(){
        DEF_GUT = readGut() || DEF_GUT;
        document.getElementById("r_gut").value = DEF_GUT;
        document.getElementById("o_gut").textContent = DEF_GUT + "px";
      }, 260);
    });
    btn.addEventListener("click", function(){ box.classList.add("open"); btn.style.display = "none"; });
    document.getElementById("pvTuneX").addEventListener("click", function(){
      box.classList.remove("open"); btn.style.display = "";
    });
    document.getElementById("pvReset").addEventListener("click", function(){
      root.style.removeProperty("--gut"); gutTouched = false;
      DEF_GUT = readGut() || DEF_GUT;
      document.getElementById("r_gut").value = DEF_GUT;
      ["hero","panel","chip","t5","card"].forEach(function(i){ document.getElementById("r_" + i).value = 1; });
      document.getElementById("r_t5h").value = 1;
      paint();
    });
    document.getElementById("pvCopy").addEventListener("click", function(){
      var ta = document.getElementById("pvOut");
      ta.select(); ta.setSelectionRange(0, 99999);
      try{ document.execCommand("copy"); }catch(e){}
      var b = document.getElementById("pvCopy"), t = b.textContent;
      b.textContent = "복사됨 — 이 줄을 알려주세요";
      setTimeout(function(){ b.textContent = t; }, 1800);
    });
    paint();
  })();

  document.querySelector("#pvBadge .pv-x").addEventListener("click", function(){
    document.getElementById("pvBadge").remove();
  });

  /* 원본 로더를 데모 주입 버전으로 교체한다.
     SHARE_ITEMS / LG_POSTS / BOARD_POSTS / NOTICELIST 는 let 전역이라
     별도 classic script 에서도 같은 렉시컬 바인딩에 접근·대입할 수 있다. */
  window.loadShare = async function(){ SHARE_ITEMS = DEMO_SHARE; renderShare(); };
  window.loadLounge = async function(){ LG_POSTS = DEMO_LOUNGE; lgRenderFeed(); };
  window.loadPosts = async function(){ BOARD_POSTS = DEMO_BOARD; PAGE_SHOWN = PAGE_SIZE; renderBoardRows(); };
  window.refreshNotice = async function(){ NOTICELIST = DEMO_NOTICES; refreshNoticeHub(); };
  window.refreshBoardDot = async function(){};

  loadShare();
  refreshNotice();
  lgRenderComposer();
  loadLounge();
  loadPosts();
})();
<\\/script>
"""

shim = (shim
        .replace("__NOTICES__", json.dumps(NOTICES, ensure_ascii=False))
        .replace("__SHARE__", json.dumps(SHARE, ensure_ascii=False))
        .replace("__LOUNGE__", json.dumps(LOUNGE, ensure_ascii=False))
        .replace("__BOARD__", json.dumps(BOARD, ensure_ascii=False))
        .replace("<\\/script>", "</scr" + "ipt>"))

out = "<title>" + title + "</title>\n" + head_css + "\n" + body_inner + shim

if os.path.dirname(OUT):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
io.open(OUT, "w", encoding="utf-8").write(out)

print("wrote", OUT, len(out), "chars")
for tag in ("<!DOCTYPE", "<html", "<head>", "<body>", "</body>", "</html>"):
    assert tag not in out, "wrapper tag leaked: " + tag
print("wrapper tags: clean")
print("script blocks:", out.count("<script>"), "/", out.count("</script>"))
