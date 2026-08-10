#!/usr/bin/env python3
"""MAPS 리허설용 로컬 정적 서버.

새 PC 를 들여오기 전에 **지금 쓰는 PC 로** 서버 구성을 미리 시험해 보기 위한 도구다.
표준 라이브러리만 쓴다 — 사내 PC 에 아무것도 설치하지 않고 바로 돌릴 수 있어야 한다.

## 왜 `python -m http.server` 를 쓰면 안 되나

파이썬 기본 서버(`SimpleHTTPRequestHandler`)는 **HTTP Range 요청을 지원하지 않는다.**
Range 헤더를 보내도 `200 OK` + 전체 본문으로 응답하고 `Accept-Ranges` 헤더도 없다.

V4-2 히어로 영상은 **3초 지점으로 seek** 해서 3~8초 구간만 반복한다.
Range 가 안 되면 그 seek 이 어긋난다. 실측 결과:

    python -m http.server   → 구간 이탈 6회, currentTime 이 0.33초까지 내려감  (깨짐)
    이 스크립트(206 지원)    → 구간 이탈 0회, 3.31~8.03초 유지               (정상)

IIS · nginx · Docker nginx 는 Range 를 기본 지원하므로 실제 서버에서는 문제가 없다.
하필 "가장 간단해서" 제일 먼저 시도하게 되는 파이썬 한 줄만 문제다.

## 사용법

    python3 tools/serve_local.py                          # 최신 릴리스를 8080 으로
    python3 tools/serve_local.py --dir releases/MAPS-V4-1
    python3 tools/serve_local.py --port 9000

기동하면 **동료에게 전달할 사내 IP URL** 을 직접 찍어 준다.
리허설의 핵심이 "내 PC 에 남이 실제로 접속되는가" 이기 때문이다.

## 주의

개인 업무 PC 에서 포트를 열고 동료에게 공유하는 것이 사내 보안 정책 위반일 수 있다.
방화벽 인바운드 허용에 관리자 권한이 필요할 수도 있다. 옆자리 1~2명에게 잠깐 보여주는
수준으로 시작하고, 부서 전체 공지는 IT 승인 후에 한다.
자세한 절차는 `docs/로컬-PC-리허설-체크리스트.md` 참고.
"""

import argparse
import http.server
import os
import re
import socket
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 파이썬 기본 MIME 추정은 환경(특히 Windows 레지스트리)에 따라 달라진다.
# 영상·JSON 이 엉뚱한 타입으로 나가면 재생이 안 되므로 명시한다.
MIME = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}

RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


def latest_release() -> Path:
    """releases/MAPS-V<n>[-<m>]/ 중 번호가 가장 큰 것.
    tools/build_standalone.py 의 같은 이름 함수와 동일한 규칙을 쓴다."""
    dirs = []
    for d in (ROOT / "releases").glob("MAPS-V*"):
        if d.is_dir() and (d / "index.html").is_file():
            parts = d.name[len("MAPS-V"):].split("-")
            if parts and all(x.isdigit() for x in parts):
                dirs.append((tuple(int(x) for x in parts), d))
    if not dirs:
        raise SystemExit("[중단] releases/MAPS-V<n>/index.html 을 찾지 못했습니다.")
    return max(dirs)[1]


def lan_ips() -> list:
    """동료에게 알려줄 사내 IP. 루프백만 잡히면 리허설이 성립하지 않으므로 걸러낸다."""
    ips = set()
    # 실제로 나가는 인터페이스를 고르는 가장 확실한 방법 — 패킷은 보내지 않는다
    for probe in ("8.8.8.8", "10.255.255.255"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((probe, 1))
            ips.add(s.getsockname()[0])
        except OSError:
            pass
        finally:
            s.close()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


class Handler(http.server.SimpleHTTPRequestHandler):
    """Range(206) 를 지원하는 정적 핸들러."""

    directory = "."   # __init__ 에서 덮어쓴다

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=type(self).directory, **kw)

    # ---- 공통 헤더 ------------------------------------------------------
    def _common(self, ctype: str):
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        # 리허설 중에는 파일을 자주 고친다. 캐시가 남으면 "왜 안 바뀌지" 로 시간을 버린다.
        self.send_header("Cache-Control", "no-store, must-revalidate")

    def guess_type(self, path):
        ext = os.path.splitext(str(path))[1].lower()
        return MIME.get(ext) or super().guess_type(path)

    # ---- GET / HEAD -----------------------------------------------------
    def do_GET(self):
        self._serve(body=True)

    def do_HEAD(self):
        self._serve(body=False)

    def _serve(self, body: bool):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            index = os.path.join(path, "index.html")
            if os.path.isfile(index):
                path = index
            else:
                return super().do_GET() if body else super().do_HEAD()
        if not os.path.isfile(path):
            self.send_error(404, "Not Found")
            return

        size = os.path.getsize(path)
        ctype = self.guess_type(path)
        m = RANGE_RE.match(self.headers.get("Range", "") or "")

        # ---- Range 없음: 통짜 응답 ----
        if not m:
            self.send_response(200)
            self._common(ctype)
            self.send_header("Content-Length", str(size))
            self.end_headers()
            if body:
                with open(path, "rb") as f:
                    self._pump(f, size)
            return

        # ---- Range 있음: 206 Partial Content ----
        s_raw, e_raw = m.group(1), m.group(2)
        if s_raw == "" and e_raw == "":
            self.send_error(400, "Bad Range")
            return
        if s_raw == "":                       # bytes=-500 → 마지막 500바이트
            length = min(int(e_raw), size)
            start, end = size - length, size - 1
        else:
            start = int(s_raw)
            end = int(e_raw) if e_raw else size - 1
            end = min(end, size - 1)

        if start >= size or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return

        self.send_response(206)
        self._common(ctype)
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        if body:
            with open(path, "rb") as f:
                f.seek(start)
                self._pump(f, end - start + 1)

    def _pump(self, f, remaining: int, chunk: int = 64 * 1024):
        """브라우저가 영상 탐색 중 연결을 끊는 건 정상이다 — 조용히 넘긴다."""
        try:
            while remaining > 0:
                buf = f.read(min(chunk, remaining))
                if not buf:
                    break
                self.wfile.write(buf)
                remaining -= len(buf)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    ap = argparse.ArgumentParser(description="MAPS 리허설용 로컬 정적 서버 (Range 지원)")
    ap.add_argument("--dir", help="서빙할 폴더 (기본: releases 의 최신 릴리스)")
    ap.add_argument("--port", type=int, default=8080, help="포트 (기본 8080)")
    args = ap.parse_args()

    target = Path(args.dir).resolve() if args.dir else latest_release()
    if not target.is_dir():
        raise SystemExit(f"[중단] 폴더가 없습니다: {target}")
    if not (target / "index.html").is_file():
        raise SystemExit(f"[중단] {target} 에 index.html 이 없습니다.")

    Handler.directory = str(target)

    try:
        srv = Server(("", args.port), Handler)
    except OSError as e:
        raise SystemExit(f"[중단] 포트 {args.port} 를 열지 못했습니다 — {e}\n"
                         f"  다른 프로그램이 쓰고 있으면 --port 로 바꿔 보세요.")

    print("=" * 64)
    print(f"  MAPS 리허설 서버  ·  Range(206) 지원")
    print(f"  폴더 : {target}")
    print("-" * 64)
    print(f"  내 PC 에서 : http://localhost:{args.port}/")
    ips = lan_ips()
    if ips:
        print("  동료에게   :")
        for ip in ips:
            print(f"               http://{ip}:{args.port}/")
        print()
        print("  ※ 동료가 접속 안 되면 방화벽 인바운드에서")
        print(f"     TCP {args.port} 를 허용해야 합니다.")
    else:
        print("  동료에게   : (사내 IP 를 찾지 못했습니다 — 유선 연결 확인)")
    print()
    print("  ※ 개인 업무 PC 공유는 사내 보안 정책 확인 후에.")
    print("     자세한 절차: docs/로컬-PC-리허설-체크리스트.md")
    print("=" * 64)
    print("  Ctrl+C 로 종료")
    print()

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
