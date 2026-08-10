#!/usr/bin/env python3
"""릴리스 HTML 안의 `FALLBACK` 을 뽑아 `data/dashboards.json` 을 만든다.

## 왜 필요한가

`loadData()` 는 `data/dashboards.json` 을 먼저 찾고, 없으면 코드 안 `FALLBACK` 으로
대체한다. 즉 이 파일을 서버에 놓는 순간부터 **카드 목록의 진짜 원본은 이 파일**이 된다.
AI Agent 를 연결한다는 것은 이 파일의 해당 항목에 `addr` 을 채우는 일이다.

그런데 이 JSON 을 손으로 처음부터 쓰면 반드시 틀리는 지점이 있다.

- `column.team` 은 `ORG_ORDER` 4개 문자열과 **접두 일치**해야 정렬이 맞는다
- item 의 `org` 는 조직 필터 칩 5개 중 하나와 **정확히 일치**해야 필터가 걸린다

그래서 사람이 쓰지 않고 코드에서 그대로 뽑는다.

## 파싱 방법

`FALLBACK` 은 따옴표 없는 키를 쓰는 JS 객체 리터럴이라 `json.loads` 로 못 읽는다.
정규식으로 JS 를 파싱하려 들지 말고 **node 에게 평가시켜 JSON 으로 받는다.**

## 사용법

    python3 tools/make_dashboards_json.py                         # 최신 릴리스 → data/dashboards.json
    python3 tools/make_dashboards_json.py --live sample-agent \
            --addr http://localhost/agents/sample-agent/          # 첫 항목 하나를 LIVE 로
    python3 tools/make_dashboards_json.py --out /tmp/x.json
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# index.html 의 ORG_ORDER 와 같아야 한다. 뽑아낸 결과를 검증하는 용도다.
ORG_ORDER = ["新 공정/공법 개발", "해외법인 양산 지원", "제품 개발 대응", "공통 및 루틴 업무"]


def latest_release() -> Path:
    dirs = []
    for d in (ROOT / "releases").glob("MAPS-V*"):
        if d.is_dir() and (d / "index.html").is_file():
            parts = d.name[len("MAPS-V"):].split("-")
            if parts and all(x.isdigit() for x in parts):
                dirs.append((tuple(int(x) for x in parts), d))
    if not dirs:
        raise SystemExit("[중단] releases/ 에서 릴리스를 찾지 못했습니다.")
    return max(dirs)[1]


def extract_fallback(html: str) -> dict:
    """`const FALLBACK={...};` 구간을 잘라 node 로 평가한다."""
    start = html.find("const FALLBACK=")
    if start < 0:
        raise SystemExit("[중단] 원본에서 `const FALLBACK=` 를 찾지 못했습니다.")
    i = html.find("{", start)
    depth, j, in_str, quote, esc = 0, i, False, "", False
    while j < len(html):
        c = html[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                in_str = False
        elif c in "\"'":
            in_str, quote = True, c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    if depth != 0:
        raise SystemExit("[중단] FALLBACK 의 중괄호 짝이 맞지 않습니다.")
    literal = html[i:j + 1]

    out = subprocess.run(
        ["node", "-e", "process.stdout.write(JSON.stringify(" + literal + "))"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"[중단] node 평가 실패:\n{out.stderr.strip()}")
    return json.loads(out.stdout)


def check(data: dict) -> None:
    """뽑아낸 값이 화면 로직의 전제를 만족하는지 본다. 틀리면 조용히 어긋나므로 여기서 잡는다."""
    cols = data.get("columns") or []
    if not cols:
        raise SystemExit("[중단] columns 가 비어 있습니다.")
    for c in cols:
        team = c.get("team", "")
        if not any(team.startswith(o) for o in ORG_ORDER):
            raise SystemExit(
                f"[중단] 카테고리 '{team}' 이 ORG_ORDER 와 접두 일치하지 않습니다.\n"
                f"  ORG_ORDER : {ORG_ORDER}"
            )
        if not c.get("items"):
            raise SystemExit(f"[중단] '{team}' 에 항목이 없습니다.")


def main() -> None:
    ap = argparse.ArgumentParser(description="FALLBACK → data/dashboards.json")
    ap.add_argument("--src", help="입력 HTML (기본: 최신 릴리스의 index.html)")
    ap.add_argument("--out", default=str(ROOT / "data" / "dashboards.json"))
    ap.add_argument("--live", metavar="NAME",
                    help="이 이름의 항목 하나를 LIVE 로 만든다 (--addr 와 함께)")
    ap.add_argument("--addr", help="--live 항목에 넣을 전체 URL")
    args = ap.parse_args()

    src = Path(args.src) if args.src else (latest_release() / "index.html")
    if not src.is_file():
        raise SystemExit(f"[중단] 입력 파일이 없습니다: {src}")

    data = extract_fallback(src.read_text(encoding="utf-8"))
    check(data)

    if args.live:
        if not args.addr:
            raise SystemExit("[중단] --live 를 쓰면 --addr 도 필요합니다.")
        # normAddr() 이 스킴 없는 값에 http:// 를 붙여 http://agents/... 로 깨뜨린다.
        if not re.match(r"^https?://", args.addr, re.I):
            raise SystemExit(
                f"[중단] addr 는 전체 URL 이어야 합니다: {args.addr}\n"
                f"  상대경로를 넣으면 normAddr() 이 'http://{args.addr}' 로 만들어 깨집니다."
            )
        hit = None
        for c in data["columns"]:
            for it in c["items"]:
                if it["name"] == args.live:
                    hit = it
                    break
            if hit:
                break
        if not hit:
            names = [it["name"] for c in data["columns"] for it in c["items"]]
            raise SystemExit(f"[중단] '{args.live}' 항목이 없습니다.\n  있는 이름: {names[:5]} …")
        hit["addr"] = args.addr

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    n = sum(len(c["items"]) for c in data["columns"])
    live = sum(1 for c in data["columns"] for it in c["items"] if (it.get("addr") or "").strip())
    print(f"{out}  ·  카테고리 {len(data['columns'])}개 · 항목 {n}개 · LIVE {live}개")


if __name__ == "__main__":
    main()
