#!/usr/bin/env python3
"""MAPS V3 → V4-1 / V4-2 생성기.

두 버전 모두 **V3 을 기준**으로 만든다. 공통 수정사항 7건을 먼저 적용하고,
그 결과를 V4-1 로 확정한 뒤, 거기에 히어로 영상과 화면 분리를 얹어 V4-2 를 만든다.

  V4-1 = V3 + 공통 수정 7건 + Agent 팝업 (기존 별자리 히어로 유지)
  V4-2 = V4-1 + 히어로를 배경 영상으로 교체 + 첫 화면/대시보드 화면 분리

원본(`releases/MAPS-V3/index.html`)은 읽기만 한다.

사용법:
    python3 tools/build_v4.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "releases" / "MAPS-V3" / "index.html"
OUT1 = ROOT / "releases" / "MAPS-V4-1" / "index.html"
OUT2 = ROOT / "releases" / "MAPS-V4-2" / "index.html"

VIDEO_URL = "https://www.lgensol.com/inc/video/video_main01.mp4#t=3,8"


def sub1(text: str, old: str, new: str, label: str, count: int = 1) -> str:
    """정확히 count 번 나오지 않으면 조용히 넘어가지 않고 중단한다."""
    n = text.count(old)
    if n != count:
        raise SystemExit(f"[중단] {label}: {n}번 발견(기대 {count})\n  대상: {old[:90]!r}")
    return text.replace(old, new, count)


# ===========================================================================
# 공통 수정사항 7건
# ===========================================================================
def common(s: str) -> str:
    # ---- 1) AI Agent 등록 요청 모달 -------------------------------------
    s = sub1(
        s,
        "<h2>AI Agent 등록 요청</h2><p>1차 IT 검토 → 2차 적절성 검토 후 등록됩니다</p>",
        "<h2>AI Agent 등록 요청</h2>",
        "1-a 검토 절차 문구 삭제",
    )
    s = sub1(
        s,
        '<div class="field"><label>요청자</label><input id="rqAuthor" maxlength="40" placeholder="이름 (비우면 \'익명\')"></div>\n'
        '      <div class="field"><label>조직</label><input id="rqOrg" placeholder="예: 해외법인 양산 지원"></div>',
        '<div class="field"><label>요청자</label><input id="rqAuthor" maxlength="40" placeholder="이름"></div>\n'
        '      <div class="field"><label>기술그룹</label><input id="rqOrg" placeholder="예 : 전극기술그룹"></div>\n'
        '      <div class="field"><label>팀</label><input id="rqTeam" maxlength="60" placeholder="예 : 믹싱공정기술팀"></div>',
        "1-b 요청자 플레이스홀더 · 조직→기술그룹 · 팀 추가",
    )
    s = sub1(
        s,
        '<textarea id="rqDesc" rows="3" placeholder="용도·요청 사유 등"></textarea>',
        '<textarea id="rqDesc" rows="3" placeholder="AI Agent에 대한 부연설명 기입"></textarea>',
        "1-c 설명 플레이스홀더",
    )
    s = sub1(
        s,
        "<div class=\"field\"><label>기능추가</label>",
        "<div class=\"field\"><label>카테고리</label>",
        "1-h 기능추가 → 카테고리",
    )
    # 기능추가 → 카테고리 4종. ORG_ORDER 와 같은 문자열을 쓴다.
    s = sub1(
        s,
        '<label class="feat-item"><input type="checkbox" class="rqFeat" value="데이터 서버저장"> 데이터 서버저장</label>\n'
        '          <label class="feat-item"><input type="checkbox" class="rqFeat" value="공개(비로그인 화면)"> 공개(비로그인 화면)</label>\n'
        '          <label class="feat-item"><input type="checkbox" class="rqFeat" value="비공개(로그인 화면)"> 비공개(로그인 화면)</label>',
        '<label class="feat-item"><input type="checkbox" class="rqFeat" value="新 공정/공법 개발"> 新 공정/공법 개발</label>\n'
        '          <label class="feat-item"><input type="checkbox" class="rqFeat" value="해외법인 양산 지원"> 해외법인 양산 지원</label>\n'
        '          <label class="feat-item"><input type="checkbox" class="rqFeat" value="제품 개발 대응"> 제품 개발 대응</label>\n'
        '          <label class="feat-item"><input type="checkbox" class="rqFeat" value="공통 및 루틴 업무"> 공통 및 루틴 업무</label>',
        "1-d 기능추가 → 카테고리 4종",   # 값은 ORG_ORDER 와 글자까지 같아야 한다
                                        # (승인 시 이 값으로 들어갈 카테고리를 고른다)
    )
    # 새로 생긴 rqTeam 을 초기화·전송에 연결한다(빠뜨리면 입력해도 안 넘어간다)
    s = sub1(
        s,
        '["rqName","rqAuthor","rqOrg","rqDesc"].forEach',
        '["rqName","rqAuthor","rqOrg","rqTeam","rqDesc"].forEach',
        "1-e 팀 입력칸 초기화 대상에 추가",
    )
    s = sub1(
        s,
        '  const org=document.getElementById("rqOrg").value.trim();\n'
        '  const desc=document.getElementById("rqDesc").value.trim();',
        '  const org=document.getElementById("rqOrg").value.trim();\n'
        '  const team=document.getElementById("rqTeam")?document.getElementById("rqTeam").value.trim():"";\n'
        '  const desc=document.getElementById("rqDesc").value.trim();',
        "1-f 팀 값 읽기",
    )
    s = sub1(
        s,
        "body:JSON.stringify({name,author,org,desc,features,etc,html,fname})",
        "body:JSON.stringify({name,author,org,team,desc,features,etc,html,fname})",
        "1-g 팀 값 전송",
    )

    # ---- 2) 파우치형기술그룹 → 파우치/각형기술그룹 -----------------------
    n = s.count("파우치형기술그룹")
    if n < 1:
        raise SystemExit("[중단] 2 파우치형기술그룹을 찾지 못했습니다.")
    s = s.replace("파우치형기술그룹", "파우치/각형기술그룹")
    print(f"  ✓ 2 파우치형기술그룹 → 파우치/각형기술그룹 ({n}곳)")

    # ---- 3) 태그라인 Manufacturing AI agent … (MAPS) ---------------------
    s = sub1(
        s,
        '<span class="aria-ltr">M</span>anufacturing <span class="aria-ltr">A</span>gent '
        '<span class="aria-ltr">P</span>latform &amp; <span class="aria-ltr">S</span>hared-dashboard',
        '<span class="aria-ltr">M</span>anufacturing <span class="aria-ltr">A</span>I agent '
        '<span class="aria-ltr">P</span>latform &amp; <span class="aria-ltr">S</span>hared-dashboard',
        "3-a 히어로 태그라인",
    )
    s = sub1(
        s,
        "Manufacturing Agent Platform &amp; Shared-dashboard<br>",
        '<span class="aria-ltr">M</span>anufacturing <span class="aria-ltr">A</span>I agent '
        '<span class="aria-ltr">P</span>latform &amp; <span class="aria-ltr">S</span>hared-dashboard<br>',
        "3-b 푸터 태그라인",
    )
    # 푸터에는 .aria-ltr 강조 규칙이 없어 그냥 흰 글자로 나온다 — 히어로와 같은 강조를 준다
    s = sub1(
        s,
        "  .brand-tagline .aria-ltr{color:#4dd8e8;font-weight:700}",
        "  .brand-tagline .aria-ltr{color:#4dd8e8;font-weight:700}\n"
        "  .foot-tag .aria-ltr{color:var(--accent);font-weight:800}",
        "3-c 푸터 강조 규칙",
    )

    # ---- 3-d) 푸터 버전 표기 --------------------------------------------
    s = sub1(
        s,
        "<span>생산기술혁신센터 AI 플랫폼 v0.1 · 사내 전용</span>",
        "<span>생산기술혁신센터 AI 플랫폼 v1.0 · 사내 전용</span>",
        "3-d 푸터 버전 v0.1 → v1.0",
    )

    # ---- 4) "준비중" 앞 기호를 다른 칩과 같은 ● 로 -----------------------
    # 두 곳이다: 범례 칩(정적 마크업)과 카드 배지(statusBadge). 카드 배지 쪽이
    # 화면에서 훨씬 많이 보이므로 빠뜨리면 고친 티가 안 난다.
    s = sub1(
        s,
        '<span class="chip soon">▪ 준비중</span>',
        '<span class="chip soon">● 준비중</span>',
        "4-a 범례 칩 ▪ → ●",
    )
    s = sub1(
        s,
        '\'<span class="v10badge soon">▪ 준비중</span>\'',
        '\'<span class="v10badge soon">● 준비중</span>\'',
        "4-b 카드 상태 배지 ▪ → ●",
    )

    # ---- 5) 카테고리별 AI Agent 화면 상단 버튼 ---------------------------
    # "대시보드" 라벨과 "추가요청" 버튼을 걷고, 대시보드 화면과 같은 등록 버튼을 둔다.
    # id(dashReqBtn)는 유지한다 — 히어로의 #agentRegBtn 이 이 버튼을 click() 으로
    # 위임하고 있어서, id 를 바꾸면 히어로 버튼이 조용히 죽는다.
    s = sub1(
        s,
        '        <span class="sys-label">대시보드</span>\n'
        '        <button class="sys-btn" id="dashReqBtn">추가요청</button>\n',
        '        <button class="sys-btn cat-reg-btn" id="dashReqBtn">＋ AI Agent 등록</button>\n',
        "5-a 대시보드 라벨 제거 · 등록 버튼으로 교체",
    )
    s = sub1(
        s,
        "  .dash-req-box{display:inline-flex;align-items:center;gap:6px;flex-wrap:wrap}",
        "  .dash-req-box{display:inline-flex;align-items:center;gap:6px;flex-wrap:wrap}\n"
        "  /* V4) 카탈로그 툴바용 등록 버튼 — 대시보드 화면의 #agentRegBtn 과 같은 얼굴에\n"
        "     툴바 높이(.sys-btn)만 맞춘다.\n"
        "     .sys-btn 을 두 번 겹쳐 쓴 이유: 아래쪽(661행)에 .banner-btn,.sys-btn 규칙이\n"
        "     또 있어 클래스 하나짜리로는 뒤에 오는 그 규칙에 밀린다. */\n"
        "  .sys-btn.cat-reg-btn{background:var(--grad);color:#04121a;border-color:transparent;\n"
        "    font-weight:800;box-shadow:var(--glow)}\n"
        "  .sys-btn.cat-reg-btn:hover{background:var(--grad);color:#04121a;border-color:transparent;\n"
        "    box-shadow:0 0 30px rgba(77,216,232,.4)}",
        "5-b 등록 버튼 스타일",
    )

    # ---- 6·7) 공지: [공지] 글만 · 3~4건만 --------------------------------
    s = sub1(
        s,
        "  var NOTICE_N = 5, NOTICE_TOTAL = 0;",
        "  /* V4) 6) 한 화면에서 잘리지 않도록 기본 3건 — 나머지는 더보기로 펼친다\n"
        "         7) [공지] 글만 노출 */\n"
        "  var NOTICE_BASE = 3;\n"
        "  var NOTICE_N = NOTICE_BASE, NOTICE_TOTAL = 0;\n"
        "  function isNoticeOnly(p){\n"
        "    var c = String((p && p.category) || \"\").trim();\n"
        "    var t = String((p && p.title) || \"\");\n"
        "    return c === \"공지\" || c === \"[공지]\" || /^\\s*\\[공지\\]/.test(t);\n"
        "  }",
        "6·7-a 표시 개수 4건 · [공지] 판정 함수",
    )
    s = sub1(
        s,
        "    var sample = !list.length;\n"
        "    if(sample) list = NOTICE_SAMPLE.slice();\n",
        "    var sample = !list.length;\n"
        "    if(sample) list = NOTICE_SAMPLE.slice();\n"
        "    list = list.filter(isNoticeOnly);            /* V4) [공지] 태그 글만 */\n",
        "6·7-b [공지] 필터 적용",
    )
    s = sub1(
        s,
        '      _more.style.display = (NOTICE_TOTAL > 5) ? "" : "none";',
        '      _more.style.display = (NOTICE_TOTAL > NOTICE_BASE) ? "" : "none";',
        "6-c 더보기 노출 기준",
    )
    s = sub1(
        s,
        "      NOTICE_N = (NOTICE_N > 5) ? 5 : Math.max(5, NOTICE_TOTAL);",
        "      NOTICE_N = (NOTICE_N > NOTICE_BASE) ? NOTICE_BASE : Math.max(NOTICE_BASE, NOTICE_TOTAL);",
        "6-d 더보기 토글 기준",
    )
    # 폴백 샘플의 [공지] 글은 3건뿐이라 그대로 두면 더보기가 펼칠 게 없다.
    # 백엔드가 없는 환경에서도 더보기 동작을 눈으로 확인할 수 있게 3건을 더 넣는다.
    s = sub1(
        s,
        '{id:0, title:"AI Agent 등록 신청 절차 안내", ts:"2026-08-01", category:"안내"},',
        '{id:0, title:"AI Agent 등록 신청 절차 안내", ts:"2026-08-01", category:"안내"},   /* 공지 아님 — 필터에서 빠진다 */\n'
        '    {id:0, title:"AI Agent 담당자 지정 및 운영 책임 안내", ts:"2026-07-26", category:"공지"},\n'
        '    {id:0, title:"2분기 AI Agent 활용 실적 집계 결과", ts:"2026-07-19", category:"공지"},\n'
        '    {id:0, title:"사내 AI 활용 가이드라인 개정 시행", ts:"2026-07-12", category:"공지"},',
        "7-e 폴백 샘플 [공지] 3건 추가 (더보기 확인용)",
    )
    return s


# ===========================================================================
# 공통 8) Agent 팝업 — 올린 HTML 을 새 탭 대신 페이지 안 레이어로 실행
#
# 링크를 만드는 렌더러가 3곳이다(카탈로그 카드 · TOP5 · 인기 모듈). 셋 다
# `a.href=normAddr(addr); a.target="_blank"` 로 같다. 각각을 고치는 대신
# document 캡처 단계에서 한 번에 가로챈다 — 앞으로 렌더러가 늘어도 따라온다.
# ===========================================================================
POPUP_CSS = '''  /* ===================== 공통 8) Agent 팝업 =====================
     새 탭은 맥락을 잃는다. 여러 자료를 훑는 사용 방식에서는 탭이 쌓이고
     돌아왔을 때 스크롤·필터·검색어가 초기화된다. 페이지 안 레이어로 띄운다. */
  body.modal-open{overflow:hidden}
  /* 기본 .overlay 는 z-index 50 이라 고정 네비(80)와 챗봇 버튼(60) 아래에 깔린다.
     그대로 두면 팝업 제목이 네비에 가린다. 자료를 보는 동안은 앱 크롬을 덮는 게 맞다. */
  #agentOv{padding:0;align-items:center;z-index:90}
  .modal.agent{width:min(1500px,94vw);height:92vh;max-width:none;
    display:flex;flex-direction:column;overflow:hidden}
  .modal.agent .modal-head{flex-shrink:0;gap:12px;padding:14px 18px}
  .ag-title{min-width:0}
  .ag-title h2{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;outline:none}
  .ag-chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}
  .ag-chip{font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px;
    border:1px solid var(--panel-line);color:var(--txt-dim)}
  .ag-acts{display:flex;gap:6px;align-items:center;flex-shrink:0}
  .ag-body{position:relative;flex:1 1 auto;min-height:0;background:var(--ink)}
  #agentFrame{width:100%;height:100%;border:0;display:block;background:#fff}
  .ag-load{position:absolute;inset:0;display:flex;flex-direction:column;
    align-items:center;justify-content:center;gap:14px;
    background:var(--ink);color:var(--txt-dim);font-size:13px;text-align:center;padding:20px}
  .ag-load[hidden]{display:none}
  .ag-spin{width:34px;height:34px;border-radius:50%;
    border:3px solid var(--panel-line);border-top-color:var(--accent);
    animation:agSpin .9s linear infinite}
  @keyframes agSpin{to{transform:rotate(360deg)}}
  .ag-slow{display:none;flex-direction:column;align-items:center;gap:12px}
  .ag-load.slow .ag-spin,.ag-load.slow .ag-wait{display:none}
  .ag-load.slow .ag-slow{display:flex}
  .modal.agent .modal-foot{flex-shrink:0;padding:12px 18px}
  .ag-url{flex:1 1 auto;min-width:0;font-size:12px;color:var(--txt-faint);
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:left}
  /* 저사양·원격 데스크톱에서 회전 애니메이션은 화면 갱신 비용만 만든다 */
  body.lite .ag-spin{animation:none}
  @media (prefers-reduced-motion:reduce){.ag-spin{animation:none}}
  @media (max-width:820px){
    .modal.agent{width:100vw;height:100dvh;border-radius:0;border:0}
    .ag-acts .minibtn{padding:5px 7px}
  }
'''

POPUP_HTML = '''
<!-- 공통 8) Agent 팝업 — 올린 HTML 을 이 안에서 실행한다 -->
<div class="overlay" id="agentOv">
  <div class="modal agent" role="dialog" aria-modal="true" aria-labelledby="agTitle">
    <div class="modal-head">
      <div class="ag-title">
        <h2 id="agTitle" tabindex="-1">AI Agent</h2>
        <div class="ag-chips" id="agChips"></div>
      </div>
      <div class="ag-acts">
        <button class="minibtn" id="agNewWin" title="별도 창으로 엽니다">새 창</button>
        <button class="minibtn" id="agFull" title="전체화면">전체화면</button>
        <button class="xbtn" id="agClose" aria-label="닫기" title="닫기 (ESC)">&times;</button>
      </div>
    </div>
    <div class="ag-body">
      <!-- allow-same-origin 을 주지 않는다. 남이 만든 페이지가 MAPS 의 DOM·쿠키·api/* 에
           닿지 못하도록 불투명 출처로 격리한다. allow-top-navigation 도 주지 않는다. -->
      <iframe id="agentFrame" title="AI Agent 실행 화면" referrerpolicy="no-referrer"
              sandbox="allow-scripts allow-forms allow-popups allow-modals allow-downloads"></iframe>
      <div class="ag-load" id="agLoad">
        <div class="ag-spin" aria-hidden="true"></div>
        <div class="ag-wait">불러오는 중…</div>
        <div class="ag-slow">
          <div>응답이 없습니다.<br>이 자료는 팝업 안에서 열리지 않는 종류일 수 있습니다.</div>
          <button class="btn btn-primary" id="agOpenTab">새 탭에서 열기</button>
        </div>
      </div>
    </div>
    <div class="modal-foot">
      <span class="ag-url" id="agUrl"></span>
      <div class="foot-btns">
        <button class="btn btn-ghost" id="agCopy">주소 복사</button>
        <button class="btn btn-ghost" id="agCloseB">닫기</button>
      </div>
    </div>
  </div>
</div>
'''

POPUP_JS = r'''
  /* ---------------------------------------------------------------
     공통 8) Agent 팝업

     설계 근거를 남긴다.

     1) 렌더러를 고치지 않는다. 링크를 만드는 곳이 카탈로그 카드 ·
        TOP5 · 인기 모듈 3곳이고 앞으로 늘 수 있다. document 캡처
        단계에서 한 번 가로채면 전부 커버되고 앞으로도 따라온다.

     2) 아무거나 팝업으로 열지 않는다. 다른 서버의 대시보드는 대개
        X-Frame-Options 로 프레이밍을 거부하는데, 교차 출처라
        그 실패를 자바스크립트로 감지할 방법이 없다. 흰 화면만 남는다.
        그래서 우리가 올린 자료(같은 출처 + 경로에 /agents/)만 팝업이고
        나머지는 새 탭 그대로다. 항목에 open:"popup"/"tab" 으로 강제 가능.

     3) 성공은 load 이벤트로만 알 수 있고 실패는 알 수 없다. 감지하는
        척하지 않고 8초가 지나면 "새 탭에서 열기" 라는 탈출구를 준다.
     --------------------------------------------------------------- */
  (function agentPopup(){
    var ov = document.getElementById("agentOv");
    var frame = document.getElementById("agentFrame");
    if(!ov || !frame) return;

    var SLOW_MS = 8000;
    var elTitle = document.getElementById("agTitle");
    var elChips = document.getElementById("agChips");
    var elUrl   = document.getElementById("agUrl");
    var elLoad  = document.getElementById("agLoad");

    var opened = false, curUrl = "", lastFocus = null, slowT = null;

    function abs(u){ try{ return new URL(u, location.href).href; }catch(e){ return ""; } }

    function isOurs(u){
      try{
        var x = new URL(u, location.href);
        return x.origin === location.origin && x.pathname.indexOf("/agents/") >= 0;
      }catch(e){ return false; }
    }
    function slugOf(u){
      try{
        var m = new URL(u, location.href).pathname.match(/\/agents\/([^\/]+)/);
        return m ? decodeURIComponent(m[1]) : "";
      }catch(e){ return ""; }
    }
    function hashSlug(){
      var m = (location.hash || "").match(/agent=([^&]+)/);
      return m ? decodeURIComponent(m[1]) : "";
    }

    /* dashboards.json 의 항목을 찾아 제목·조직·open 설정을 얻는다.
       덕분에 렌더러에 data-* 속성을 심지 않아도 된다. */
    function recFor(pred){
      try{
        var cols = (typeof STATE !== "undefined" && STATE && STATE.columns) || [];
        for(var i = 0; i < cols.length; i++){
          var its = cols[i].items || [];
          for(var j = 0; j < its.length; j++) if(pred(its[j])) return { col: cols[i], it: its[j] };
        }
      }catch(e){}
      return null;
    }
    function recByUrl(u){ return recFor(function(it){ return it.addr && abs(it.addr) === u; }); }
    function recBySlug(sl){ return recFor(function(it){ return it.addr && slugOf(it.addr) === sl; }); }

    function textIn(a, sel){ var n = a.querySelector(sel); return n ? n.textContent.trim() : ""; }

    function setChips(list){
      elChips.innerHTML = "";
      list.forEach(function(t){
        if(!t) return;
        var s = document.createElement("span");
        s.className = "ag-chip"; s.textContent = t;
        elChips.appendChild(s);
      });
    }

    function openAgent(url, name, chips, push){
      curUrl = abs(url);
      if(!curUrl) return;
      elTitle.textContent = name || "AI Agent";
      setChips(chips || []);
      elUrl.textContent = curUrl;
      elLoad.hidden = false;
      elLoad.classList.remove("slow");
      frame.setAttribute("src", curUrl);
      ov.classList.add("open");
      document.body.classList.add("modal-open");
      opened = true;
      if(slowT) clearTimeout(slowT);
      slowT = setTimeout(function(){ elLoad.classList.add("slow"); }, SLOW_MS);
      try{ elTitle.focus(); }catch(e){}
      if(push){
        var sl = slugOf(curUrl);
        var st = { maps: "agent", slug: sl }, h = "#agent=" + encodeURIComponent(sl);
        /* 이미 팝업 상태면 항목을 새로 쌓지 않고 바꾼다. 팝업에서 팝업으로 옮겨 다녀도
           뒤로가기 한 번이면 목록으로 돌아온다. */
        try{
          if(history.state && history.state.maps === "agent") history.replaceState(st, "", h);
          else history.pushState(st, "", h);
        }catch(e){}
      }
    }

    function openBySlug(sl, push){
      if(!sl) return;
      var r = recBySlug(sl);
      openAgent(r ? r.it.addr : ("agents/" + encodeURIComponent(sl) + "/"),
                r ? r.it.name : sl,
                r ? [r.col.team, r.it.org || r.it.owner] : [],
                push);
    }

    function closeAgent(fromHistory){
      if(!opened) return;
      opened = false;
      if(slowT){ clearTimeout(slowT); slowT = null; }
      ov.classList.remove("open");
      document.body.classList.remove("modal-open");
      /* 남겨 두면 숨겨진 채 계속 돈다. 원격 데스크톱에서는 그 비용이 그대로 보인다. */
      frame.setAttribute("src", "about:blank");
      if(document.fullscreenElement){ try{ document.exitFullscreen(); }catch(e){} }
      if(!fromHistory){
        /* history.back() 은 쓰지 않는다. 비동기라서, 닫자마자 다른 Agent 를 열면
           뒤늦게 도착한 popstate 가 방금 연 팝업을 닫아 버린다.
           현재 항목의 해시만 지우면 경합 없이 결정적으로 끝난다.
           (대신 수동으로 닫은 뒤의 뒤로가기 한 번은 아무 일도 하지 않는다) */
        if((location.hash || "").indexOf("agent=") >= 0){
          try{ history.replaceState(null, "", location.pathname + location.search); }catch(e){}
        }
      }
      if(lastFocus && lastFocus.focus){ try{ lastFocus.focus(); }catch(e){} }
      lastFocus = null;
    }

    frame.addEventListener("load", function(){
      if(!opened) return;
      if(frame.getAttribute("src") === "about:blank") return;
      if(slowT){ clearTimeout(slowT); slowT = null; }
      elLoad.hidden = true;
    });

    /* ---- 링크 가로채기 (캡처 단계) ----
       stopPropagation 은 하지 않는다. 카드에 이미 붙어 있는
       api/dash-access 비콘 리스너가 그대로 살아야 접속 기록이 남는다. */
    document.addEventListener("click", function(e){
      if(e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;  /* 새 탭으로 여는 습관은 존중한다 */
      var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
      if(!a || a.getAttribute("aria-disabled") === "true") return;
      var href = a.getAttribute("href");
      if(!href || href.charAt(0) === "#") return;
      var u = abs(href);
      if(!u) return;
      var r = recByUrl(u);
      var mode = (r && r.it && r.it.open) ? r.it.open : (isOurs(u) ? "popup" : "tab");
      if(mode !== "popup") return;
      e.preventDefault();
      lastFocus = a;
      openAgent(u,
        r ? r.it.name : (textIn(a, ".cell-name") || textIn(a, ".t5-name") || textIn(a, ".ih-pop-name") || "AI Agent"),
        r ? [r.col.team, r.it.org || r.it.owner]
          : [textIn(a, ".v10cat") || textIn(a, ".ih-pop-team"), textIn(a, ".v10org")],
        true);
    }, true);

    /* ---- 닫기 ----
       주의: iframe 안에 포커스가 있으면 부모로 keydown 이 오지 않아 ESC 가 듣지 않는다.
       샌드박스라 iframe 문서에 리스너를 심을 수도 없다. 그래서 × 버튼이 실질적인 닫기다. */
    document.addEventListener("keydown", function(e){
      if(e.key !== "Escape" || !opened) return;
      e.stopPropagation();          /* 기존 전역 ESC 핸들러가 정리 없이 닫아 버리는 것을 막는다 */
      closeAgent(false);
    }, true);
    ov.addEventListener("click", function(e){ if(e.target === ov) closeAgent(false); });
    document.getElementById("agClose").addEventListener("click", function(){ closeAgent(false); });
    document.getElementById("agCloseB").addEventListener("click", function(){ closeAgent(false); });

    window.addEventListener("popstate", function(){
      var sl = hashSlug();
      if(!sl){ closeAgent(true); return; }
      if(opened && slugOf(curUrl) === sl) return;   /* 이미 그 화면이면 다시 열지 않는다 */
      openBySlug(sl, false);
    });

    /* ---- 보조 동작 ---- */
    document.getElementById("agNewWin").addEventListener("click", function(){
      var u = curUrl;
      window.open(u, "_blank", "noopener,width=1440,height=900");
      closeAgent(false);
    });
    document.getElementById("agOpenTab").addEventListener("click", function(){
      var u = curUrl;
      window.open(u, "_blank", "noopener");
      closeAgent(false);
    });
    document.getElementById("agFull").addEventListener("click", function(){
      var box = ov.querySelector(".modal.agent");     /* iframe 이 아니라 모달을 — 제목·닫기가 남아야 한다 */
      if(document.fullscreenElement){ try{ document.exitFullscreen(); }catch(e){} return; }
      if(box.requestFullscreen){ box.requestFullscreen().catch(function(){}); }
    });
    document.getElementById("agCopy").addEventListener("click", function(){
      var btn = this, u = curUrl;
      function done(){ var t = btn.textContent; btn.textContent = "복사됨"; setTimeout(function(){ btn.textContent = t; }, 1200); }
      function fallback(){
        var ta = document.createElement("textarea");
        ta.value = u; ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.select();
        try{ document.execCommand("copy"); done(); }catch(e){}
        document.body.removeChild(ta);
      }
      /* http:// 사내 주소는 보안 컨텍스트가 아니라 navigator.clipboard 가 없다. 폴백이 본체다. */
      if(navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(u).then(done, fallback);
      else fallback();
    });

    /* ---- 딥링크 ----
       #agent=<폴더> 로 들어오면 그 팝업이 열린 상태로 뜬다. 링크를 그대로
       동료에게 전달할 수 있다. 제목을 채우려면 STATE 가 있어야 해서 조금 기다린다. */
    function boot(){ var sl = hashSlug(); if(sl) openBySlug(sl, false); }
    if(document.readyState === "complete") setTimeout(boot, 400);
    else window.addEventListener("load", function(){ setTimeout(boot, 400); });
  })();
'''


def popup(s: str) -> str:
    s = sub1(s, "\n</style>\n</head>", "\n" + POPUP_CSS + "\n</style>\n</head>",
             "8-a 팝업 CSS")
    s = sub1(s, "</div>\n\n<!-- 게시판 (탭 전환형 섹션) -->",
             "</div>\n" + POPUP_HTML + "\n<!-- 게시판 (탭 전환형 섹션) -->",
             "8-b 팝업 마크업")
    s = sub1(s, "\n})();\n</script>\n</body>", "\n" + POPUP_JS + "\n})();\n</script>\n</body>",
             "8-c 팝업 스크립트")
    return s

# ===========================================================================
# 공통 9) 원격 화면(화면 전송) 대응
#
# 사내 클라우드·원격 데스크톱에서는 브라우저가 그린 픽셀이 네트워크로 전송된다.
# 화면에 계속 움직이는 영역이 크면 인코더가 그 영역에 대역을 다 쓰고, 주변 글자가
# 손실 압축으로 뭉개진다("글자가 깨진다"). 처음에 저화질로 오다가 점점 선명해지는
# 것도 같은 이유다. 2560x1080 은 1920x1080 보다 픽셀이 33% 많아 넓은 화면에서만
# 무너진다.
#
# 자동 감지만으로는 안 된다. 원본 강등은 requestAnimationFrame 간격을 재는데,
# 원격에서는 이 값이 정상으로 나온다 — 브라우저는 VM 안에서 잘 그리고 있고 막히는
# 곳은 인코더이며, 브라우저는 자기 화면이 전송된다는 사실을 모른다. 그래서
# **사용자가 직접 켜는 스위치가 본체**이고, WebGL 렌더러 문자열로 하는 자동 감지는 보조다.
# ===========================================================================
LITE_CSS = '''  /* ----- 원격 화면 최적화(body.lite) 추가분 -----
     여기 있는 것들이 화면 전송 비용의 대부분이다. 흐림 효과는 위에서 --blur 로 이미 꺼진다. */
  body.lite .reveal{opacity:1;transform:none;transition:none}
  /* 큰 글자를 transform 으로 움직이면 그 구간 동안 텍스트가 레이어로 굳어 뭉개진다 */
  body.lite :is(#secHome,#secDash) .hero-title{filter:none}
  /* filter 를 끄는 대신 딤을 조금 올려 제목 대비를 지킨다 (V4-2) */
  body.lite #heroVeil{background:rgba(0,0,0,.52)}
  body.lite .cell,body.lite .t5,body.lite .col,body.lite .panel,body.lite .modal{box-shadow:none}
  body.lite .brand-logo,body.lite .logo-pulse{animation:none}
'''

LITE_ROW = '''      <div class="set-row">
        <div class="set-lab"><label>원격 화면 최적화</label><span class="set-hint">사내 클라우드·원격 접속에서 화면이 흐리거나 글자가 뭉개질 때 켜세요</span></div>
        <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--txt-dim);white-space:nowrap;cursor:pointer"><input type="checkbox" id="setLite" style="width:auto;margin:0">켜기</label>
      </div>
'''

LITE_JS_STATE = '''  var SET      = { fs:"m", showN:3, lite:null };   /* lite:null = 아직 고르지 않음(자동 판단) */

  /* 원격 데스크톱·가상 화면은 대부분 소프트웨어 렌더러로 뜬다.
     프레임 시간으로는 판별할 수 없어(원격에서도 VM 안에서는 60fps 가 나온다)
     렌더러 이름을 본다. 어디까지나 보조 판단이고, 사용자의 선택이 언제나 이긴다. */
  function looksRemote(){
    try{
      var c  = document.createElement("canvas");
      var gl = c.getContext("webgl") || c.getContext("experimental-webgl");
      if(!gl) return true;                       /* 가속 자체가 없으면 켜 두는 편이 낫다 */
      var ex = gl.getExtension("WEBGL_debug_renderer_info");
      var r  = ex ? String(gl.getParameter(ex.UNMASKED_RENDERER_WEBGL) || "") : "";
      return /swiftshader|llvmpipe|softwarerasterizer|basic render|vmware|virtualbox|citrix|parallels|remotefx/i.test(r);
    }catch(e){ return false; }
  }
  function applyLite(on){
    document.body.classList.toggle("lite", !!on);
    var cb = document.getElementById("setLite");
    if(cb) cb.checked = !!on;
  }
'''

LITE_JS_LOAD = '''      if(o && typeof o.lite === "boolean") SET.lite = o.lite;
'''

LITE_JS_WIRE = '''
    var lb = document.getElementById("setLite");
    if(lb) lb.addEventListener("change", function(){
      SET.lite = !!lb.checked; setSave(); applyLite(SET.lite);
      toast(SET.lite ? "원격 화면 최적화를 켰습니다." : "원격 화면 최적화를 껐습니다.");
    });
'''


def lite(s: str) -> str:
    s = sub1(
        s,
        "  body.lite .modal{backdrop-filter:none;-webkit-backdrop-filter:none}\n",
        "  body.lite .modal{backdrop-filter:none;-webkit-backdrop-filter:none}\n" + LITE_CSS,
        "9-a 원격 화면 CSS",
    )
    s = sub1(
        s,
        '      <div class="set-row">\n'
        '        <div class="set-lab"><label>좋아요 · 즐겨찾기</label>',
        LITE_ROW +
        '      <div class="set-row">\n'
        '        <div class="set-lab"><label>좋아요 · 즐겨찾기</label>',
        "9-b 설정 패널 스위치",
    )
    s = sub1(
        s,
        '  var SET      = { fs:"m", showN:3 };\n',
        LITE_JS_STATE,
        "9-c 설정 상태 + 자동 판단",
    )
    s = sub1(
        s,
        "      if(o && [3,5,10,20].indexOf(+o.showN) >= 0) SET.showN = +o.showN;\n",
        "      if(o && [3,5,10,20].indexOf(+o.showN) >= 0) SET.showN = +o.showN;\n" + LITE_JS_LOAD,
        "9-d 설정 불러오기",
    )
    s = sub1(
        s,
        "    var rb = document.getElementById(\"setResetBtn\");",
        LITE_JS_WIRE + "\n    var rb = document.getElementById(\"setResetBtn\");",
        "9-e 스위치 배선",
    )
    s = sub1(
        s,
        "    markFsSeg(SET.fs);\n    var ss = document.getElementById(\"setShowN\");\n"
        "    if(ss) ss.value = String(SET.showN);\n    open(\"setOv\");",
        "    markFsSeg(SET.fs);\n    var ss = document.getElementById(\"setShowN\");\n"
        "    if(ss) ss.value = String(SET.showN);\n"
        "    var lb = document.getElementById(\"setLite\");\n"
        "    if(lb) lb.checked = document.body.classList.contains(\"lite\");\n"
        "    open(\"setOv\");",
        "9-f 설정 열 때 스위치 상태 동기화",
    )
    s = sub1(
        s,
        "    applyFontScale(SET.fs);\n    applyShowN(SET.showN, false);",
        "    /* 사용자가 고른 적이 있으면 그 값, 없으면 자동 판단 */\n"
        "    applyLite(SET.lite === null ? looksRemote() : SET.lite);\n"
        "    applyFontScale(SET.fs);\n    applyShowN(SET.showN, false);",
        "9-g 시작 시 적용",
    )
    return s

# ===========================================================================
# 공통 10) 등록요청 업로드 — 3단 폴백
#
# 지금은 api/dash-request 로 POST 하고, 실패하면 빨간 글씨 한 줄로 끝난다.
# IIS 는 정적 파일만 주므로 백엔드가 없으면 항상 그 길로 간다. 막다른 길을 없앤다.
#
#   1) api/dash-request        — 나중에 진짜 백엔드가 붙어도 그대로 동작한다
#   2) api/dash-request.ashx   — IIS + ASP.NET 로 올린 핸들러
#   3) 요청서 내려받기          — 둘 다 없으면 파일로 받아 관리자에게 전달
#
# 3단계 산출물은 "메타를 주석으로 얹은 원본 HTML" 이다. 관리자가 이름만 index.html 로
# 바꿔 agents\<폴더>\ 에 넣으면 그대로 동작한다. 별도 해석 도구가 필요 없다.
# ===========================================================================
UPLOAD_HELPERS = '''function setReqStatus(m,c){const e=document.getElementById("reqStatus");e.className="status"+(c?(" "+c):"");e.textContent=m;}
/* 서버가 못 받았을 때 — 입력값과 원본 HTML 을 한 파일로 묶어 내려받게 한다.
   결과물은 메타를 주석으로 얹은 원본 HTML 이라, 관리자가 index.html 로 이름만 바꿔
   agents 폴더에 넣으면 바로 동작한다. */
function buildRequestDoc(p){
  var meta = [
    "MAPS AI Agent 등록요청",
    "요청 시각   : " + new Date().toLocaleString("ko-KR"),
    "AI Agent 명 : " + (p.name || ""),
    "요청자      : " + (p.author || ""),
    "기술그룹    : " + (p.org || ""),
    "팀          : " + (p.team || ""),
    "카테고리    : " + ((p.features || []).join(", ")),
    "설명        : " + (p.desc || ""),
    "원본 파일명 : " + (p.fname || "(첨부 없음)")
  ].join("\\n  ").replace(/-->/g, "- ->");   /* 값 안에 --> 가 있으면 주석이 일찍 닫힌다 */
  var head = "<!--\\n  " + meta +
    "\\n\\n  이 파일을 서버의  agents\\\\<폴더이름>\\\\index.html  로 넣으면 그대로 동작합니다.\\n-->\\n";
  if(p.html) return head + p.html;
  /* body 태그는 쓰지 않는다 — 이 문자열이 index.html 안에 들어가는데,
     standalone 빌더가 </bo dy> 를 유일한 앵커로 쓰기 때문이다. div 로 충분하다. */
  return head + '<!DOCTYPE html><meta charset="utf-8"><title>' + esc(p.name || "등록요청") + '</title>' +
    '<div style="font-family:sans-serif;padding:36px;line-height:1.8;background:#0b1120;color:#eaf0fb;min-height:100vh">' +
    '<h1>' + esc(p.name || "") + '</h1><p>첨부 HTML 이 없는 등록요청입니다. 위 주석의 내용을 확인해 주세요.</p></div>';
}
function offerRequestDownload(p){
  var el = document.getElementById("reqStatus");
  el.className = "status err";
  el.innerHTML = '서버가 업로드를 받지 못했습니다. ' +
    '<button class="minibtn" type="button" id="rqDlBtn" style="margin-left:6px">요청서 내려받기</button>';
  var btn = document.getElementById("rqDlBtn");
  btn.addEventListener("click", function(){
    var blob = new Blob([buildRequestDoc(p)], {type:"text/html;charset=utf-8"});
    var url  = URL.createObjectURL(blob);
    var a    = document.createElement("a");
    a.href = url;
    /* 파일 이름은 ASCII 로만 만든다. 브라우저에 따라 a.download 의 비ASCII 이름을
       통째로 버리고 "download" 로 저장해 버린다(헤드리스 Chromium 에서 실측).
       한글 이름은 파일 안 주석에 그대로 남으므로 정보가 사라지지 않는다. */
    var d = new Date(), z = function(n){ return (n < 10 ? "0" : "") + n; };
    var stamp = d.getFullYear() + z(d.getMonth()+1) + z(d.getDate()) + "-" + z(d.getHours()) + z(d.getMinutes());
    var tail = String(p.name || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 30);
    a.download = "MAPS-request-" + stamp + (tail ? "-" + tail : "") + ".html";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function(){ URL.revokeObjectURL(url); }, 2000);
    setReqStatus("내려받았습니다. 이 파일을 관리자에게 전달해 주세요.", "ok");
  });
}'''

UPLOAD_CHECK = '''  if(!name){setReqStatus("대시보드명을 입력하세요.","err");return;}
  if(f){
    if(!/\\.html?$/i.test(f.name)){setReqStatus("HTML 파일만 올릴 수 있습니다.","err");return;}
    /* 서버(ASP.NET)의 기본 요청 한도가 4MB 다. 문자열로 부풀 것을 감안해 3MB 에서 막는다.
       보내고 나서 실패하는 것보다 보내기 전에 이유를 말해 주는 편이 낫다. */
    if(f.size > 3*1024*1024){setReqStatus("파일이 3MB 를 넘습니다. 이미지를 줄이거나 나눠 주세요.","err");return;}
  }'''

UPLOAD_BODY = '''  setReqStatus("전송 중…");
  let html="",fname="";
  if(f){
    try{ html=await f.text(); fname=f.name; }
    catch(e){ setReqStatus("파일을 읽지 못했습니다.","err"); return; }
  }
  const payload={name,author,org,team,desc,features,etc,html,fname};
  const body=JSON.stringify(payload);
  /* 1) 진짜 백엔드 → 2) IIS 핸들러 → 3) 파일로 받아 전달 */
  for(const url of ["api/dash-request","api/maps.ashx?a=dash-request"]){
    try{
      const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body});
      if(!r.ok) continue;                       /* 404·405 면 다음 후보로 */
      const j=await r.json().catch(()=>null);
      if(j&&j.ok){
        close("reqOv");
        alert("등록 요청이 접수되었습니다.\\n관리자가 확인한 뒤 화면에 반영됩니다.");
        return;
      }
      if(j&&j.error){ setReqStatus(j.error,"err"); return; }   /* 서버가 이유를 말해 준 경우 */
    }catch(e){}
  }
  offerRequestDownload(payload);'''


def upload(s: str) -> str:
    s = sub1(
        s,
        'function setReqStatus(m,c){const e=document.getElementById("reqStatus");'
        'e.className="status"+(c?(" "+c):"");e.textContent=m;}',
        UPLOAD_HELPERS,
        "10-a 요청서 내려받기 도우미",
    )
    s = sub1(
        s,
        '  if(!name){setReqStatus("대시보드명을 입력하세요.","err");return;}',
        UPLOAD_CHECK,
        "10-b 업로드 전 검사",
    )
    s = sub1(
        s,
        '''  setReqStatus("전송 중…");
  try{
    let html="",fname="";
    if(f){html=await f.text();fname=f.name;}
    const r=await fetch("api/dash-request",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,author,org,team,desc,features,etc,html,fname})});
    const j=await r.json();
    if(r.ok&&j.ok){close("reqOv");alert("대시보드 추가요청이 접수되었습니다. 관리자 검토 후 반영됩니다.");}
    else setReqStatus(j.error||"요청 실패","err");
  }catch(e){setReqStatus("서버에 연결할 수 없습니다.","err");}''',
        UPLOAD_BODY,
        "10-c 3단 폴백 제출",
    )
    return s

# ===========================================================================
# 공통 11) api/* 호출을 apiFetch 로 바꿔 두 종류의 서버를 모두 받아들인다
#
#   1) 있는 그대로 (api/me …)        — 진짜 백엔드가 붙으면 여기서 끝난다
#   2) api/maps.ashx?a=me            — IIS + ASP.NET 로 올린 핸들러
#
# 404/405 일 때만 2번으로 넘어간다. 500 이나 401 은 서버가 응답한 것이므로 그대로 쓴다.
# 화면 전체가 이 한 함수를 지나가므로, 나중에 백엔드가 바뀌어도 여기만 손보면 된다.
# ===========================================================================
API_HELPER = '''function esc(t){const d=document.createElement("div");d.textContent=t==null?"":t;return d.innerHTML}
/* api/* 호출 창구. 아래 두 곳을 차례로 시도한다.
     1) 있는 그대로            — 진짜 백엔드(예: maps_backend.py)가 있으면 여기서 끝
     2) api/maps.ashx?a=...    — IIS 에 올린 ASP.NET 핸들러
   404·405 만 다음 후보로 넘긴다. 401·403·500 은 서버가 판단해 답한 것이라 그대로 돌려준다. */
async function apiFetch(path, opts){
  try{
    const r = await fetch(path, opts);
    if(r.status !== 404 && r.status !== 405) return r;
  }catch(e){ /* 연결 자체가 안 되면 아래에서 한 번 더 시도한다 */ }
  const i = path.indexOf("?");
  const name = (i < 0 ? path.slice(4) : path.slice(4, i));
  const rest = (i < 0 ? "" : "&" + path.slice(i + 1));
  return fetch("api/maps.ashx?a=" + name + rest, opts);
}'''


def api(s: str) -> str:
    s = sub1(
        s,
        'function esc(t){const d=document.createElement("div");d.textContent=t==null?"":t;return d.innerHTML}',
        API_HELPER,
        "11-a apiFetch 창구",
    )
    # 링크는 폴백을 걸 수 없다. 두 서버가 모두 알아듣는 형태 하나로 고정한다
    # (maps_backend.py 도 api/maps.ashx?a= 형태를 함께 받는다).
    s = sub1(
        s,
        'href="api/req-file?id=${encodeURIComponent(q.id)}"',
        'href="api/maps.ashx?a=req-file&id=${encodeURIComponent(q.id)}"',
        "11-b 첨부 내려받기 링크",
    )
    n = s.count('fetch("api/')
    if n < 40:
        raise SystemExit(f"[중단] 11-c api 호출이 {n}곳뿐입니다 — 원본 구조가 바뀌었습니다.")
    s = s.replace('fetch("api/', 'apiFetch("api/')
    # 방금 만든 apiFetch 안의 두 줄은 원래대로 되돌린다(자기 자신을 부르면 무한 재귀다)
    s = s.replace('const r = await apiFetch(path, opts);', 'const r = await fetch(path, opts);')
    s = s.replace('return apiFetch("api/maps.ashx?a=" + name + rest, opts);',
                  'return fetch("api/maps.ashx?a=" + name + rest, opts);')
    print(f"  ✓ 11-c api 호출 {n}곳을 apiFetch 로 교체")
    return s

# ===========================================================================
# V4-2 — 히어로 영상 + 첫 화면 / 대시보드 화면 분리
# ===========================================================================
HERO_MEDIA = f'''    <!-- V4-2) 히어로 배경 영상. loop 속성 대신 JS 로 3~8초 구간만 반복한다.
         막힌 망에서는 스스로 감춰지고 아래 그라디언트만 남는다.

         source 가 둘인 이유: 같은 폴더에 hero.mp4 가 있으면 그것을 먼저 쓰고,
         없으면(404) 브라우저가 다음 source 로 넘어가 지금처럼 사내 홈페이지에서
         받아온다. 나중에 ffmpeg 로 만든 파일을 폴더에 넣기만 하면 코드를 고치지
         않고 로컬 재생으로 바뀐다 — 외부 왕복이 사라져 첫 재생 지연이 없어진다.

         preload 는 metadata 가 아니라 auto 다. metadata 는 머리말만 받아 두고
         본체는 재생 시점에 받기 시작해서 초반이 끊긴다. -->
    <video id="heroVideo" aria-hidden="true" autoplay muted playsinline preload="auto">
      <source src="hero.mp4#t=3,8" type="video/mp4">
      <source src="{VIDEO_URL}" type="video/mp4">
    </video>
    <div id="heroVeil" aria-hidden="true"></div>
'''

HERO_CSS = '''  /* ===================== V4-2) 히어로 배경 영상 =====================
     첫 화면은 메인 타이틀과 영상만 보인다. 3패널은 아래 #secDash 로 내려갔으므로
     영상을 자를 이유가 없다 — 섹션(메뉴 아래~화면 끝) 전체를 그대로 채운다.
     top 이 0 이 아니라 --nav-h 인 이유: header 가 position:fixed 이고 최상단에서
     배경이 transparent 라, 0 부터 깔면 메뉴 글자가 영상 위에 얹힌다.
     height 를 calc 로 못 박는 이유: <video> 는 대체 요소라 height:auto 면
     top/bottom 이 아니라 영상의 고유 종횡비로 높이를 잡아 섹션 아래가 빈다. */
  /* translateZ(0) · contain:paint — 영상과 딤을 각각 독립 합성 레이어로 고정한다.
     매 프레임 주변까지 다시 칠하지 않게 해, 원격 데스크톱처럼 GPU 없는 환경에서
     화면 갱신 범위를 히어로 안으로 가둔다.
     딤을 filter:brightness() 로 영상에 합치는 방법은 쓰지 않는다 — 필터는 매 프레임
     연산이라 GPU 없는 VM 에서 오히려 손해다. 단색 레이어 합성이 싸다. */
  #heroVideo{position:absolute;top:var(--nav-h);left:0;right:0;
    width:100%;height:calc(100% - var(--nav-h));object-fit:cover;
    display:block;z-index:0;pointer-events:none;border:0;background:var(--ink);
    transform:translateZ(0);backface-visibility:hidden;contain:paint}
  #heroVeil{position:absolute;top:var(--nav-h);left:0;right:0;height:calc(100% - var(--nav-h));
    z-index:0;pointer-events:none;background:rgba(0,0,0,.4);transform:translateZ(0)}
  #heroVideo[hidden],#heroVeil[hidden]{display:none}
  /* 첫 화면은 히어로만 있으므로 세로 가운데로 모은다 */
  #secHome{justify-content:center}
  #secHome .home-inner{justify-content:center}
  /* 문구는 영상 위에 얹힌다 — 박스형 스크림(.hero::before)은 밝은 영상에서 어두운
     타원으로 드러나므로 쓰지 않고, 글자 자체에 그림자를 준다.
     제목은 text-shadow 가 아니라 filter:drop-shadow 다. 안의 <span class="grad"> 가
     background-clip:text + text-fill-color:transparent 라 text-shadow 는 투명한
     글자 속으로 비쳐 지저분해진다. drop-shadow 는 렌더 결과의 알파를 따른다. */
  #secHome .hero::before{display:none}
  #secHome .hero-title{filter:drop-shadow(0 2px 14px rgba(5,7,14,.85))}
  #secHome .hero .eyebrow,
  #secHome .hero-tagline,
  #secHome .hero .sub{text-shadow:0 1px 10px rgba(5,7,14,.85)}
  /* 스크롤을 유도하는 힌트 — 첫 화면이 히어로뿐이라 아래가 있다는 신호가 필요하다 */
  /* 하단 고정 검색바(.dockbar: bottom 18px + 높이 48px)를 피해 그 위에 둔다.
     26px 에 두면 검색바에 정확히 가려진다. */
  #heroScrollHint{position:absolute;left:50%;bottom:82px;transform:translateX(-50%);
    z-index:2;display:flex;flex-direction:column;align-items:center;gap:6px;
    background:none;border:0;padding:6px 10px;cursor:pointer;font-family:inherit;
    font-size:11.5px;font-weight:700;letter-spacing:.14em;color:var(--txt-dim)}
  #heroScrollHint:hover{color:var(--accent)}
  #heroScrollHint .chev{width:16px;height:16px;border-right:2px solid currentColor;
    border-bottom:2px solid currentColor;transform:rotate(45deg);animation:heroChev 1.8s ease-in-out infinite}
  @keyframes heroChev{0%,100%{transform:rotate(45deg) translate(0,0);opacity:.55}
    50%{transform:rotate(45deg) translate(3px,3px);opacity:1}}
  @media (prefers-reduced-motion:reduce){#heroScrollHint .chev{animation:none}}
  @media(max-width:900px){#heroScrollHint{bottom:70px}}
  /* 챗봇 창이 열리면 검색바와 함께 물러난다 */
  body.chatopen #heroScrollHint{opacity:0;pointer-events:none}
'''

HERO_JS = '''  /* ---------------------------------------------------------------
     1) 히어로 배경 영상 (V4-2 — 별자리 파티클 네트워크를 대체)
        · loop 속성 대신 3~8초 구간만 되돌려 반복한다.
        · 화면 밖 · 탭 비활성일 때는 세워 둔다 — 배경 영상이 계속 디코딩되면
          스크롤이 무거워진다(파티클 캔버스를 세우던 것과 같은 이유).
        · 영상이 막힌 망에서는 스스로 감춰지고 섹션 그라디언트만 남는다.
     --------------------------------------------------------------- */
  (function heroVideo(){
    var v = document.getElementById("heroVideo");
    var hero = document.getElementById("secHome");
    if(!v || !hero) return;

    var START = 3.0, END = 8.0;
    var visible = true, dead = false;

    function seekStart(){
      try{ if(v.currentTime < START || v.currentTime >= END) v.currentTime = START; }catch(e){}
    }
    function play(){
      if(dead || !visible || document.hidden || REDUCED) return;
      var p = v.play();
      if(p && p.catch) p.catch(function(){});   /* 자동재생 차단은 오류가 아니다 */
    }
    function pause(){ try{ v.pause(); }catch(e){} }

    v.addEventListener("loadedmetadata", function(){ seekStart(); play(); });
    /* 구간 반복 — timeupdate 는 초당 4~5회라 종료 지점을 살짝 넘길 수 있다.
       되돌린 뒤 다시 재생시켜 루프 순간 멈추는 것을 막는다. */
    v.addEventListener("timeupdate", function(){
      if(v.currentTime >= END){ v.currentTime = START; play(); }
    });
    v.addEventListener("ended", function(){ v.currentTime = START; play(); });

    function fail(){
      if(dead) return;
      dead = true;
      v.hidden = true;
      var veil = document.getElementById("heroVeil");
      if(veil) veil.hidden = true;               /* 영상 없이 딤만 남으면 더 어색하다 */
      pause();
    }
    v.addEventListener("error", fail, true);
    var srcEl = v.querySelector("source");
    if(srcEl) srcEl.addEventListener("error", fail);
    setTimeout(function(){ if(!dead && v.readyState < 2) fail(); }, 8000);

    document.addEventListener("visibilitychange", function(){
      if(document.hidden) pause(); else play();
    });
    if("IntersectionObserver" in window){
      new IntersectionObserver(function(es){
        visible = es[0].isIntersecting;
        if(visible) play(); else pause();
      }, { threshold: 0 }).observe(hero);
    }

    /* 스크롤 중에는 세운다 — 사내 클라우드(원격 데스크톱)에서 버벅임이 가장 심한
       구간이 "스크롤 + 영상 재생"이 겹칠 때다. 원격 프로토콜이 화면 이동과 영상
       변화를 동시에 인코딩해야 하기 때문이다. 멈추면 곧바로 다시 튼다.
       재개는 play() 를 그대로 쓴다 — visible · document.hidden · dead 검사가
       이미 들어 있어 히어로 밖에서는 되살아나지 않는다. */
    var scrollT = null;
    window.addEventListener("scroll", function(){
      if(!v.paused) pause();
      if(scrollT) clearTimeout(scrollT);
      scrollT = setTimeout(play, 180);
    }, { passive: true });

    if(REDUCED){ v.addEventListener("loadeddata", function(){ seekStart(); pause(); }); }
    else { play(); }
  })();

  /* 스크롤 힌트 — 첫 화면이 히어로뿐이라 아래가 있다는 신호를 준다 */
  (function heroHint(){
    var b = document.getElementById("heroScrollHint");
    if(!b) return;
    b.addEventListener("click", function(){
      var t = document.getElementById("secDash");
      if(t) t.scrollIntoView({behavior:"smooth", block:"start"});
    });
    /* 첫 화면을 벗어나면 힌트를 숨긴다 */
    if("IntersectionObserver" in window){
      var hero = document.getElementById("secHome");
      if(hero) new IntersectionObserver(function(es){
        b.style.opacity = es[0].isIntersecting ? "" : "0";
        b.style.pointerEvents = es[0].isIntersecting ? "" : "none";
      }, { threshold: 0.35 }).observe(hero);
    }
  })();'''


def v4_2(s: str) -> str:
    # ---- 마크업: #secHome 을 히어로 전용으로, 나머지는 #secDash 로 분리 ----
    start = s.index('  <section class="sec screen" id="secHome">')
    end = s.index('  <!-- ===================== §2 TOP5 ===================== -->')
    block = s[start:end]

    hero_html = block[block.index('      <div class="hero">'):block.index('      <div class="home-actions')]
    rest_html = block[block.index('      <div class="home-actions'):block.rindex("    </div>\n  </section>")]

    new_block = (
        '  <section class="sec screen" id="secHome">\n'
        + HERO_MEDIA
        + '    <div class="home-inner">\n\n'
        + hero_html
        + '    </div>\n'
        + '    <button type="button" id="heroScrollHint" aria-label="대시보드로 이동">\n'
        + '      <span>SCROLL</span><span class="chev" aria-hidden="true"></span>\n'
        + '    </button>\n'
        + '  </section>\n\n'
        + '  <!-- ===================== §1-2 대시보드 (V4-2 에서 히어로와 분리) ===================== -->\n'
        + '  <section class="sec screen" id="secDash">\n'
        + '    <div class="sec-inner">\n'
        + '      <div class="sec-head">\n'
        + '        <div class="sec-eyebrow reveal">대시보드</div>\n'
        + '        <h2 class="sec-title reveal" data-d="1">생산기술혁신센터 <span class="grad">AI Agent</span> 현황</h2>\n'
        + '        <p class="sec-desc reveal" data-d="2">전체 Agent와 참여 팀, 카테고리별 분포, 그리고 공지사항을 한 화면에서 확인합니다.</p>\n'
        + '      </div>\n'
        + rest_html
        + '    </div>\n'
        + '  </section>\n\n'
    )
    s = s[:start] + new_block + s[end:]
    print("  ✓ V4-2-a 첫 화면(#secHome) / 대시보드(#secDash) 분리")

    # ---- CSS: #secHome 자손 선택자를 #secDash 에도 적용 ------------------
    # :is() 는 인자 중 가장 높은 특이성을 취하므로 #secHome 과 특이성이 같다 —
    # 뒤따르는 규칙들의 우선순위가 흐트러지지 않는다.
    style_end = s.index("</style>")
    head, tail = s[:style_end], s[style_end:]
    head, n = re.subn(r"#secHome(?=[ .](?![a-zA-Z-]*\{))", "SECBOTH", head)
    head = head.replace("SECBOTH", ":is(#secHome,#secDash)")
    print(f"  ✓ V4-2-b 패널 CSS 를 #secDash 에도 적용 ({n}곳)")
    s = head + tail

    # ---- 영상 CSS · JS 주입, 별자리 제거 ---------------------------------
    s = sub1(
        s,
        "  #pxNet{position:absolute;inset:0;width:100%;height:100%;display:block;z-index:0;pointer-events:none}",
        HERO_CSS.rstrip("\n"),
        "V4-2-c 히어로 영상 CSS (별자리 캔버스 CSS 대체)",
    )
    s = sub1(
        s,
        "     #pxNet 은 absolute 지만 style.height 에 px 이 박혀 있어 .measuring 중에도\n"
        "     scrollHeight 를 부풀렸다 → 대시보드가 늘 .tighter 로 눌린 채 여백만 남았다. */\n"
        "  .sec.screen.measuring #pxNet{display:none}",
        "     배경 레이어가 .measuring 중 scrollHeight 를 부풀리면 대시보드가 늘 .tighter 로\n"
        "     눌린 채 여백만 남는다. 측정 동안만 빼 둔다. (V3 의 #pxNet 자리) */\n"
        "  .sec.screen.measuring #heroVideo,\n  .sec.screen.measuring #heroVeil{display:none}",
        "V4-2-d 측정 보정 대상 교체",
    )

    # 파티클 IIFE 통째로 교체
    p0 = s.index("  /* ---------------------------------------------------------------\n     1) 히어로 파티클 네트워크")
    p1 = s.index("  /* ---------------------------------------------------------------\n     2) 스크롤 리빌")
    s = s[:p0] + HERO_JS + "\n\n" + s[p1:]
    print("  ✓ V4-2-e 파티클 IIFE → 히어로 영상 제어로 교체")

    # ---- 네비·CTA 를 대시보드 화면으로 ----------------------------------
    s = sub1(s, '<a href="#secHome">대시보드</a>', '<a href="#secDash">대시보드</a>',
             "V4-2-f 네비·푸터 대시보드 링크", count=2)
    s = sub1(s, '<a class="cta-primary" href="#secTop5">AI Agent 둘러보기 <span>→</span></a>',
             '<a class="cta-primary" href="#secDash">AI Agent 둘러보기 <span>→</span></a>',
             "V4-2-g CTA 목적지")

    # ---- #secDash 섹션 헤드 여백을 다른 섹션과 맞춘다 --------------------
    # 이 목록에 #secDash 가 빠져 있어 .sec-head 가 기본 margin-bottom:52px 를 쓴다.
    # 그래서 헤드와 3패널 사이가 넓게 벌어지고 등록 버튼이 아래로 밀려 있었다.
    s = sub1(
        s,
        "  #secTop5 .sec-head,#secPlatform .sec-head,#secCommunity .sec-head{margin-bottom:clamp(14px,2.4vh,28px)}",
        "  #secTop5 .sec-head,#secPlatform .sec-head,#secCommunity .sec-head,\n"
        "  #secDash .sec-head{margin-bottom:clamp(14px,2.4vh,28px)}",
        "V4-2-i #secDash 섹션 헤드 여백",
    )
    # 등록 버튼 줄도 3패널 쪽으로 조금 더 붙인다
    s = sub1(
        s,
        "  .home-actions{justify-content:flex-end;margin-bottom:0}",
        "  .home-actions{justify-content:flex-end;margin-bottom:0}\n"
        "  /* V4-2) 대시보드 화면의 등록 버튼을 헤드 쪽으로 조금 올린다 */\n"
        "  #secDash .home-actions{margin-top:clamp(-14px,-1.2vh,-4px);margin-bottom:clamp(4px,1vh,10px)}",
        "V4-2-j 등록 버튼 위치",
    )

    # ---- 화면 높이 자동 맞춤 대상에 #secDash 추가 ------------------------
    s = sub1(s, 'var FIT_IDS = ["secHome", "secTop5", "secPlatform"];',
             'var FIT_IDS = ["secHome", "secDash", "secTop5", "secPlatform"];',
             "V4-2-h fitScreens 대상")
    # #secHome 은 스크롤 0 에서 시작하지만 #secDash 는 네비 아래에 붙는다 —
    # 원본의 avail 계산이 secHome 만 예외 처리하고 있어 그대로 두면 된다.
    return s


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"[중단] 입력이 없습니다: {SRC}")
    base = SRC.read_text(encoding="utf-8")
    print(f"입력: {SRC.relative_to(ROOT)}  ({len(base):,} bytes)")

    print("\n[공통 수정사항 7건]")
    v1 = common(base)
    print("\n[공통 8) Agent 팝업]")
    v1 = popup(v1)
    print("\n[공통 9) 원격 화면 최적화]")
    v1 = lite(v1)
    print("\n[공통 10) 등록요청 업로드]")
    v1 = upload(v1)
    print("\n[공통 11) api 창구]")
    v1 = api(v1)
    OUT1.parent.mkdir(parents=True, exist_ok=True)
    OUT1.write_text(v1, encoding="utf-8")
    print(f"\n출력: {OUT1.relative_to(ROOT)}  ({len(v1):,} bytes)")

    print("\n[V4-2 추가]")
    v2 = v4_2(v1)
    OUT2.parent.mkdir(parents=True, exist_ok=True)
    OUT2.write_text(v2, encoding="utf-8")
    print(f"\n출력: {OUT2.relative_to(ROOT)}  ({len(v2):,} bytes)")

    # 주석 속 이력 표기는 남겨 두므로, 실제로 살아 있는 참조만 잡는다
    for tag in ('id="pxNet"', 'getElementById("pxNet")', "#pxNet{", "particleNet"):
        if tag in v2:
            print(f"  주의: V4-2 에 살아 있는 참조 '{tag}' 가 남아 있습니다 — 확인 필요")


if __name__ == "__main__":
    main()
