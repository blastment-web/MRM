#!/usr/bin/env python3
"""MAPS V3 → V4-1 / V4-2 생성기.

두 버전 모두 **V3 을 기준**으로 만든다. 공통 수정사항 7건을 먼저 적용하고,
그 결과를 V4-1 로 확정한 뒤, 거기에 히어로 영상과 화면 분리를 얹어 V4-2 를 만든다.

  V4-1 = V3 + 공통 수정 7건 (기존 별자리 히어로 유지)
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
        '<label class="feat-item"><input type="checkbox" class="rqFeat" value="新공정/공법 개발"> 新공정/공법 개발</label>\n'
        '          <label class="feat-item"><input type="checkbox" class="rqFeat" value="해외법인 양산 지원"> 해외법인 양산 지원</label>\n'
        '          <label class="feat-item"><input type="checkbox" class="rqFeat" value="제품 개발 대응"> 제품 개발 대응</label>\n'
        '          <label class="feat-item"><input type="checkbox" class="rqFeat" value="공통 및 루틴 업무"> 공통 및 루틴 업무</label>',
        "1-d 기능추가 → 카테고리 4종",
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
# V4-2 — 히어로 영상 + 첫 화면 / 대시보드 화면 분리
# ===========================================================================
HERO_MEDIA = f'''    <!-- V4-2) 히어로 배경 영상. loop 속성 대신 JS 로 3~8초 구간만 반복한다.
         막힌 망에서는 스스로 감춰지고 아래 그라디언트만 남는다. -->
    <video id="heroVideo" aria-hidden="true" autoplay muted playsinline preload="auto">
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
  #heroVideo{position:absolute;top:var(--nav-h);left:0;right:0;
    width:100%;height:calc(100% - var(--nav-h));object-fit:cover;
    display:block;z-index:0;pointer-events:none;border:0;background:var(--ink)}
  #heroVeil{position:absolute;top:var(--nav-h);left:0;right:0;height:calc(100% - var(--nav-h));
    z-index:0;pointer-events:none;background:rgba(0,0,0,.4)}
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
