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

# 2) 데모 데이터 --------------------------------------------------------------
NOTICES = [
    {"id": "n1", "title": "AIMS 포털 정식 오픈 안내", "ts": "2026-07-28 09:12", "category": "공지"},
    {"id": "n2", "title": "8월 AI Agent 활용 사내 교육 일정", "ts": "2026-07-24 14:03", "category": "교육"},
    {"id": "n3", "title": "온습도 이상감지 Agent 알람 기준 변경", "ts": "2026-07-21 17:40", "category": "공유"},
]

SHARE = [
    {"id": "s1", "name": "공정 이상 원인분석 리포트 템플릿", "desc": "불량 발생 구간별 원인 후보를 자동 정리하는 리포트 양식",
     "who": "김도현", "org": "이슈 원인분석", "fname": "rca_report_v2.html", "size": 184320},
    {"id": "s2", "name": "설비 알람 이력 대시보드", "desc": "최근 90일 알람을 설비·유형별로 집계",
     "who": "박서연", "org": "MRM 과제 운영", "url": "http://10.31.24.11:8080/alarm"},
    {"id": "s3", "name": "수율 드리프트 추적 노트북", "desc": "로트별 수율 변화를 시계열로 분해",
     "who": "이준호", "org": "이슈 원인분석", "fname": "yield_drift.ipynb", "size": 96256},
    {"id": "s4", "name": "기술 트렌드 스캐닝 결과 (7월)", "desc": "전고체·건식전극 관련 특허 및 논문 요약",
     "who": "익명", "org": "기술개발 도출 지원", "fname": "trend_2607.pptx", "size": 3241984},
    {"id": "s5", "name": "개발 게이트 산출물 체크리스트", "desc": "게이트별 필수 산출물 충족도 자동 점검 시트",
     "who": "정민아", "org": "제품 개발 프로세스 개선", "fname": "gate_checklist.xlsx", "size": 51200},
    {"id": "s6", "name": "과제 리스크 조기경보 기준", "desc": "일정·비용·품질 리스크 판정 임계값 정리",
     "who": "최우식", "org": "MRM 과제 운영", "url": "http://10.31.24.37:9000/risk"},
    {"id": "s7", "name": "선행기술 조사 자동화 스크립트", "desc": "키워드 입력 시 경쟁사 공개특허를 대조",
     "who": "한지우", "org": "기술개발 도출 지원", "fname": "prior_art.py", "size": 18432},
]

LOUNGE = [
    {"id": "l1", "name": "김도현", "org": "이슈 원인분석", "anon": False, "tag": "활용사례",
     "ts": "2026-07-29 10:22", "likes": 12, "liked": False, "attachments": [],
     "text": "공정 이상 원인분석 Agent로 지난주 불량 건 역추적해봤는데, 후보 3개 중 2번째가 실제 원인이었습니다.\n수작업으로 반나절 걸리던 걸 15분 만에 좁혔어요. 로트 번호만 넣으면 되니 한 번씩 써보시길.",
     "replies": [
         {"id": "r1", "name": "박서연", "org": "MRM 과제 운영", "anon": False,
          "ts": "2026-07-29 11:05", "text": "오 저희 라인에도 적용 가능할까요? 설비 구성이 좀 다른데."},
         {"id": "r2", "name": "김도현", "org": "이슈 원인분석", "anon": False,
          "ts": "2026-07-29 11:31", "text": "설비 태그만 매핑해주면 됩니다. 담당자분 연결해드릴게요."},
         {"id": "r3", "name": "", "org": "", "anon": True,
          "ts": "2026-07-29 13:47", "text": "저도 관심 있습니다. 매핑 가이드 공유 가능하신가요?"},
     ]},
    {"id": "l2", "name": "", "org": "", "anon": True, "tag": "질문",
     "ts": "2026-07-28 16:40", "likes": 4, "liked": False, "attachments": [],
     "text": "준비중으로 표시된 Agent는 언제쯤 열리나요? 오픈예정일이 안 적힌 것들이 있어서요.",
     "replies": [
         {"id": "r4", "name": "운영자", "org": "생산기술혁신센터", "anon": False,
          "ts": "2026-07-28 17:12", "text": "일정 확정된 건부터 타일에 오픈예정일을 채우고 있습니다. 8월 중 대부분 표기될 예정입니다."},
     ]},
    {"id": "l3", "name": "이준호", "org": "이슈 원인분석", "anon": False, "tag": "팁",
     "ts": "2026-07-27 09:15", "likes": 21, "liked": True, "attachments": [],
     "text": "대시보드 검색창에서 담당자 이름으로도 검색됩니다. 검색 조건을 '담당자'로 바꾸면 그 사람이 맡은 Agent만 모아볼 수 있어요.\n인수인계 때 꽤 유용했습니다.",
     "replies": []},
    {"id": "l4", "name": "정민아", "org": "제품 개발 프로세스 개선", "anon": False, "tag": "잡담",
     "ts": "2026-07-25 18:02", "likes": 7, "liked": False, "attachments": [],
     "text": "즐겨찾기(★) 눌러두면 카테고리 안에서 위로 올라옵니다. 자주 쓰는 것 3~4개만 찍어두니 훨씬 빠르네요.",
     "replies": []},
]

BOARD = [
    {"id": "b1", "title": "AIMS 포털 정식 오픈 안내", "author": "운영자", "ts": "2026-07-28 09:12",
     "views": 342, "comments": 5, "pinned": True, "category": "공지", "attachments": True, "likes": 18, "read": True},
    {"id": "b2", "title": "[필독] 대시보드 추가요청 절차 변경", "author": "운영자", "ts": "2026-07-20 11:00",
     "views": 288, "comments": 2, "pinned": True, "category": "공지", "attachments": False, "likes": 9, "read": True},
    {"id": "b3", "title": "8월 AI Agent 활용 사내 교육 일정", "author": "박서연", "ts": "2026-07-24 14:03",
     "views": 156, "comments": 8, "pinned": False, "category": "교육", "attachments": True, "likes": 11, "read": True},
    {"id": "b4", "title": "온습도 이상감지 Agent 알람 기준 변경 공유", "author": "김도현", "ts": "2026-07-21 17:40",
     "views": 97, "comments": 3, "pinned": False, "category": "공유", "attachments": False, "likes": 6, "read": True},
    {"id": "b5", "title": "수율 저하 요인 분석 결과 리포트", "author": "이준호", "ts": "2026-07-18 10:25",
     "views": 134, "comments": 4, "pinned": False, "category": "공유", "attachments": True, "likes": 14, "read": True},
    {"id": "b6", "title": "과제 진척 모니터링에 마일스톤 필터 추가 제안", "author": "최우식", "ts": "2026-07-15 13:50",
     "views": 62, "comments": 1, "pinned": False, "category": "제안", "attachments": False, "likes": 3, "read": True},
    {"id": "b7", "title": "선행기술 조사 Agent 결과가 중복되는 건 왜인가요?", "author": "익명", "ts": "2026-07-11 16:08",
     "views": 88, "comments": 6, "pinned": False, "category": "문의", "attachments": False, "likes": 0, "read": True},
    {"id": "b8", "title": "설계 변경 영향 분석 사용 후기", "author": "정민아", "ts": "2026-07-08 09:44",
     "views": 71, "comments": 2, "pinned": False, "category": "자유", "attachments": False, "likes": 5, "read": True},
]

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
  /* 좌우 여백 비교용 스위처 — 미리보기 전용, index.html 에는 없다 */
  #pvGut{position:fixed;left:16px;bottom:62px;z-index:56;
    display:flex;align-items:center;gap:6px;padding:7px 10px;border-radius:999px;
    background:rgba(13,19,34,.92);border:1px solid var(--panel-line);
    backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
    box-shadow:0 8px 28px rgba(0,0,0,.45)}
  #pvGut .pv-lbl{font-size:11px;font-weight:700;color:var(--txt-faint);margin-right:2px}
  #pvGut button{background:rgba(255,255,255,.05);border:1px solid var(--panel-line);
    color:var(--txt-dim);font-size:11.5px;font-weight:700;padding:4px 11px;border-radius:999px;
    cursor:pointer;font-family:inherit;white-space:nowrap}
  #pvGut button:hover{border-color:rgba(77,216,232,.45);color:var(--accent)}
  #pvGut button.on{background:rgba(77,216,232,.14);border-color:rgba(77,216,232,.5);color:var(--accent)}
  #pvGut .pv-now{font-size:11px;color:var(--txt-faint);font-variant-numeric:tabular-nums;margin-left:2px}
  @media(max-width:900px){#pvGut{display:none}}
</style>
<div id="pvGut">
  <span class="pv-lbl">좌우 여백</span>
  <button type="button" data-gut="clamp(20px,6vw,120px)" class="on">넉넉</button>
  <button type="button" data-gut="clamp(20px,4vw,80px)">보통</button>
  <button type="button" data-gut="clamp(16px,2.6vw,48px)">좁게</button>
  <button type="button" data-gut="26px">없음(직전)</button>
  <span class="pv-now" id="pvGutNow"></span>
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

  /* 좌우 여백 스위처 — --gut 만 바꾸고 fitScreens 를 다시 돌린다 */
  (function gutSwitch(){
    var box = document.getElementById("pvGut");
    if(!box) return;
    var now = document.getElementById("pvGutNow");
    function show(){
      var el = document.querySelector("#grid .col") || document.querySelector(".sec-inner");
      if(el && now) now.textContent = Math.round(el.getBoundingClientRect().left) + "px";
    }
    box.addEventListener("click", function(e){
      var b = e.target.closest("button[data-gut]");
      if(!b) return;
      document.documentElement.style.setProperty("--gut", b.dataset.gut);
      box.querySelectorAll("button").forEach(function(x){ x.classList.toggle("on", x === b); });
      window.dispatchEvent(new Event("resize"));
      setTimeout(show, 220);
    });
    window.addEventListener("resize", function(){ setTimeout(show, 220); });
    setTimeout(show, 600);
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
