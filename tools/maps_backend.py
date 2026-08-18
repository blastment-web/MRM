#!/usr/bin/env python3
"""MAPS 등록요청 백엔드 — 참조 구현.

화면(`＋ AI Agent 등록` · 관리자 콘솔 신청현황)이 이미 기대하고 있는 계약을 그대로
구현한다. 표준 라이브러리만 쓴다.

이 파일은 두 가지 역할을 한다.

1. **검증 대상.** IIS 용 `api/maps.ashx` 는 Windows·.NET 이 없는 환경에서 실행해 볼 수
   없다. 그래서 같은 계약·같은 파일 형식을 파이썬으로 먼저 구현해 실제 화면으로
   전 과정을 돌려 보고, 그 로직을 1:1 로 옮긴다.
2. **Python 이 있는 환경의 실제 서버.** 새 PC 에 Python 을 깔 수 있다면 이걸 그대로 쓰면 된다.

## 흐름

    pending ──1차 승인(admin)──→ it_approved ──2차 승인(다른 관리자)──→ approved → 카드 생성
       └──1차 반려──→ rejected          └──2차 반려──→ rejected

1차는 `admin` 계정만, 2차는 `admin` 이 아닌 관리자만 할 수 있다. 화면의 규칙
(`isSuper = ME.id === "admin"`)을 서버에서도 그대로 강제한다.

## 저장 위치

    <data>/accounts.json     관리자 계정 (솔트 + SHA-256)
    <data>/sessions.json     로그인 세션
    <data>/requests.json     요청 목록 + 상태 + 1·2차 이력
    <data>/pending/<id>.html 승인 전 업로드 파일
    <root>/agents/<slug>/index.html    2차 승인된 것만 여기로 복사된다
    <root>/**/data/dashboards.json     2차 승인 시 카드가 추가된다

**`<data>` 는 웹 루트 밖이어야 한다.** 안에 두면 `http://IP/data/accounts.json` 으로
계정 파일이 그대로 읽히고, 승인 전 업로드 파일도 주소만 알면 열린다.

## 사용법

    python3 tools/maps_backend.py --root <웹루트> --data <데이터폴더> [--port 8080]
"""

import argparse
import hashlib
import http.server
import json
import mimetypes
import os
import re
import secrets
import shutil
import socket
import socketserver
import sys
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# index.html 의 ORG_ORDER 와 정확히 같아야 한다. 등록 모달 체크박스도 이 4개다.
ORG_ORDER = ["新 공정/공법 개발", "해외법인 양산 지원", "제품 개발 대응", "공통 및 루틴 업무"]
DEFAULT_COL = ORG_ORDER[3]

MAX_HTML = 5_000_000
SESSION_DAYS = 7

MIME = {
    ".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".mp4": "video/mp4", ".webm": "video/webm",
    ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
    ".ico": "image/x-icon", ".woff2": "font/woff2",
}
RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


# ---------------------------------------------------------------- 유틸

def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def slugify(s: str) -> str:
    """영문 소문자·숫자·하이픈만 남긴다. `../` 나 한글이 들어와도 폴더 밖으로 못 나간다."""
    out = []
    for c in (s or "").lower():
        if ("a" <= c <= "z") or ("0" <= c <= "9"):
            out.append(c)
        elif c in "-_ .":
            out.append("-")
    t = "".join(out)
    while "--" in t:
        t = t.replace("--", "-")
    return t.strip("-")[:40].strip("-")


def load_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(p: Path, obj, backup: bool = False) -> None:
    """임시 파일에 쓰고 이름을 바꾼다. 쓰는 도중에 죽어도 원본이 반쯤 망가지지 않는다."""
    p.parent.mkdir(parents=True, exist_ok=True)
    if backup and p.exists():
        shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def hash_pw(pw: str, salt: str) -> str:
    return hashlib.sha256((salt + "|" + pw).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- 저장소

class Store:
    def __init__(self, root: Path, data: Path):
        self.root = root
        self.data = data
        (self.data / "pending").mkdir(parents=True, exist_ok=True)
        self.seed_accounts()

    # ---- 계정 ----
    @property
    def accounts_path(self) -> Path:
        return self.data / "accounts.json"

    def seed_accounts(self) -> None:
        if self.accounts_path.exists():
            return
        users = []
        for uid in ("admin", "manager"):
            salt = secrets.token_hex(8)
            users.append({"id": uid, "role": "admin", "salt": salt,
                          "hash": hash_pw("maps2026!", salt)})
        save_json(self.accounts_path, {"users": users})

    def find_user(self, uid: str):
        for u in load_json(self.accounts_path, {"users": []})["users"]:
            if u["id"] == uid:
                return u
        return None

    # ---- 세션 ----
    @property
    def sessions_path(self) -> Path:
        return self.data / "sessions.json"

    def new_session(self, u: dict) -> str:
        s = load_json(self.sessions_path, {})
        sid = secrets.token_hex(16)
        s[sid] = {"id": u["id"], "role": u["role"],
                  "exp": (datetime.now() + timedelta(days=SESSION_DAYS)).strftime("%Y-%m-%d %H:%M:%S")}
        save_json(self.sessions_path, s)
        return sid

    def get_session(self, sid: str):
        if not sid:
            return None
        s = load_json(self.sessions_path, {}).get(sid)
        if not s:
            return None
        try:
            if datetime.strptime(s["exp"], "%Y-%m-%d %H:%M:%S") < datetime.now():
                return None
        except Exception:
            return None
        return s

    def drop_session(self, sid: str) -> None:
        s = load_json(self.sessions_path, {})
        if sid in s:
            del s[sid]
            save_json(self.sessions_path, s)

    # ---- 요청 ----
    @property
    def requests_path(self) -> Path:
        return self.data / "requests.json"

    def requests(self) -> dict:
        return load_json(self.requests_path, {"items": []})

    def save_requests(self, db: dict) -> None:
        save_json(self.requests_path, db)

    def add_request(self, payload: dict) -> dict:
        db = self.requests()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base = slugify(payload.get("name", "")) or slugify(
            os.path.splitext(payload.get("fname", "") or "")[0])
        rid = f"{stamp}-{base}" if base else stamp
        # 같은 초에 두 건이 들어와도 겹치지 않게 한다
        used = {q["id"] for q in db["items"]}
        if rid in used:
            n = 2
            while f"{rid}-{n}" in used:
                n += 1
            rid = f"{rid}-{n}"

        html = payload.get("html") or ""
        if html:
            (self.data / "pending" / f"{rid}.html").write_text(html, encoding="utf-8")

        item = {
            "id": rid,
            "name": (payload.get("name") or "").strip(),
            "desc": (payload.get("desc") or "").strip(),
            "org": (payload.get("org") or "").strip(),
            "team": (payload.get("team") or "").strip(),
            "features": payload.get("features") or [],
            "etc": (payload.get("etc") or "").strip(),
            "fname": (payload.get("fname") or "").strip(),
            "file": bool(html),
            "bytes": len(html),
            "ts": now(),
            "status": "pending",
            "requester": (payload.get("author") or "").strip() or "(익명)",
            "requesterName": (payload.get("author") or "").strip(),
            "requesterOrg": " ".join(x for x in [(payload.get("org") or "").strip(),
                                                 (payload.get("team") or "").strip()] if x),
            "stage1": None,
            "stage2": None,
        }
        db["items"].insert(0, item)
        self.save_requests(db)
        return item

    # ---- 카드 생성 ----
    def dashboards_files(self):
        """화면 폴더마다 사본이 있다. 전부 찾아 같이 고친다."""
        out = []
        p = self.root / "data" / "dashboards.json"
        if p.is_file():
            out.append(p)
        for d in sorted(self.root.iterdir()):
            if d.is_dir():
                q = d / "data" / "dashboards.json"
                if q.is_file():
                    out.append(q)
        return out

    def publish(self, req: dict, host: str) -> str:
        """2차 승인 — 파일을 웹으로 옮기고 카드를 만든다."""
        slug = req["id"]
        src = self.data / "pending" / f"{slug}.html"
        if src.is_file():
            dst = self.root / "agents" / slug
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / "index.html")

        addr = f"http://{host}/agents/{slug}/"
        # 카테고리 비교는 공백을 무시한다 — "新 공정/공법 개발" 과 "新공정/공법 개발" 처럼
        # 띄어쓰기 하나로 엉뚱한 칸에 들어가면 원인을 찾기 어렵다.
        norm = lambda x: re.sub(r"\s+", "", x or "")
        want = {norm(o): o for o in ORG_ORDER}
        team = next((want[norm(f)] for f in req.get("features", []) if norm(f) in want), DEFAULT_COL)

        for path in self.dashboards_files():
            data = load_json(path, None)
            if not data or "columns" not in data:
                continue
            col = next((c for c in data["columns"] if norm(c.get("team")) == norm(team)), None)
            if col is None:
                col = next((c for c in data["columns"]
                            if norm(c.get("team", "")).startswith(norm(team))), None)
            if col is None:
                continue
            items = col.setdefault("items", [])
            if any(it.get("addr") == addr for it in items):
                continue                       # 이미 있으면 두 번 만들지 않는다
            items.append({
                "name": req["name"],
                "desc": req["desc"],
                "owner": req.get("requesterName", ""),
                "addr": addr,
                # 맨 앞에 놓는다. 뒤에 붙이면 기본 표시 개수(3개) 밖으로 밀려
                # "승인했는데 카드가 안 보인다" 가 된다. 목록은 order 오름차순이다.
                "order": min([int(i.get("order") or 0) for i in items] or [1]) - 1,
                "org": req.get("org", ""),
                "likes": 0,
                "linkedAt": datetime.now().strftime("%Y-%m-%d"),   # 3일간 NEW 배지
            })
            save_json(path, data, backup=True)
        return addr


# ---------------------------------------------------------------- 핸들러

class Handler(http.server.SimpleHTTPRequestHandler):
    store: Store = None

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(type(self).store.root), **kw)

    # ---- 공통 ----
    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    def guess_type(self, path):
        return MIME.get(os.path.splitext(str(path))[1].lower()) or super().guess_type(path)

    def _json(self, obj, code=200, cookie=None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def _fail(self, msg, code=400):
        self._json({"ok": False, "error": msg}, code)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return None

    def _sid(self):
        raw = self.headers.get("Cookie") or ""
        for part in raw.split(";"):
            k, _, v = part.strip().partition("=")
            if k == "maps_sid":
                return v
        return ""

    def _me(self):
        return type(self).store.get_session(self._sid())

    def _route(self):
        """`/api/me` 든 `/v4-1/api/me` 든 `api/maps.ashx?a=me` 든 같은 곳으로 보낸다.
           화면이 api/* 를 상대 경로로 부르기 때문에 화면 폴더 아래로도 들어온다."""
        u = urllib.parse.urlsplit(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path.endswith("/api/maps.ashx") or u.path.endswith("api/maps.ashx"):
            return (q.get("a", [""])[0], q)
        m = re.search(r"(?:^|/)api/([A-Za-z0-9._-]+)$", u.path)
        return (m.group(1) if m else None, q)

    # ---- GET ----
    def do_GET(self):
        act, q = self._route()
        if act:
            return self._api(act, q, "GET")
        self._static(body=True)

    def do_HEAD(self):
        act, _ = self._route()
        if act:
            return self._fail("GET/POST 만 받습니다.", 405)
        self._static(body=False)

    def do_POST(self):
        act, q = self._route()
        if not act:
            return self._fail("없는 주소입니다.", 404)
        self._api(act, q, "POST")

    # ---- API ----
    def _api(self, act, q, method):
        st = type(self).store
        me = self._me()

        if act == "me":
            return self._json({"auth": True, "id": me["id"], "role": me["role"]} if me
                              else {"auth": False})

        if act == "login":
            b = self._body() or {}
            u = st.find_user((b.get("id") or "").strip())
            if not u or hash_pw(b.get("pw") or "", u["salt"]) != u["hash"]:
                return self._fail("아이디 또는 비밀번호가 맞지 않습니다.", 401)
            sid = st.new_session(u)
            return self._json({"ok": True, "id": u["id"], "role": u["role"]},
                              cookie=f"maps_sid={sid}; Path=/; HttpOnly; SameSite=Lax")

        if act == "logout":
            st.drop_session(self._sid())
            return self._json({"ok": True}, cookie="maps_sid=; Path=/; Max-Age=0")

        if act == "dash-request":
            b = self._body()
            if b is None:
                return self._fail("요청 형식을 읽지 못했습니다.")
            if not (b.get("name") or "").strip():
                return self._fail("AI Agent 명이 필요합니다.")
            if len(b.get("html") or "") > MAX_HTML:
                return self._fail("파일이 너무 큽니다.", 413)
            item = st.add_request(b)
            return self._json({"ok": True, "id": item["id"]})

        if act == "dash-requests":
            if not me:
                return self._fail("로그인이 필요합니다.", 401)
            return self._json({"ok": True, "items": st.requests()["items"]})

        if act == "req-file":
            if not me:
                return self._fail("로그인이 필요합니다.", 401)
            rid = q.get("id", [""])[0]
            p = st.data / "pending" / f"{slugify_id(rid)}.html"
            if not p.is_file():
                return self._fail("파일이 없습니다.", 404)
            raw = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Disposition",
                             f'attachment; filename="{slugify_id(rid)}.html"')
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            return self.wfile.write(raw)

        if act == "approve-dash-request":
            if not me or me["role"] != "admin":
                return self._fail("관리자만 처리할 수 있습니다.", 403)
            b = self._body() or {}
            rid, approve = b.get("id"), bool(b.get("approve"))
            reason = (b.get("reason") or "").strip()
            db = st.requests()
            req = next((x for x in db["items"] if x["id"] == rid), None)
            if not req:
                return self._fail("요청을 찾을 수 없습니다.", 404)
            is_super = me["id"] == "admin"
            stamp = {"by": me["id"], "ts": now(),
                     "decision": "approved" if approve else "rejected", "reason": reason}

            if req["status"] == "pending":
                if not is_super:
                    return self._fail("1차 검토는 admin 계정만 할 수 있습니다.", 403)
                if not approve and not reason:
                    return self._fail("반려 사유가 필요합니다.")
                req["stage1"] = stamp
                req["status"] = "it_approved" if approve else "rejected"
            elif req["status"] == "it_approved":
                if is_super:
                    return self._fail("2차 검토는 다른 관리자 계정이 해야 합니다.", 403)
                if not approve and not reason:
                    return self._fail("반려 사유가 필요합니다.")
                req["stage2"] = stamp
                req["status"] = "approved" if approve else "rejected"
                if approve:
                    req["addr"] = st.publish(req, self.headers.get("Host") or "localhost")
            else:
                return self._fail("이미 처리된 요청입니다.")

            st.save_requests(db)
            return self._json({"ok": True, "status": req["status"]})

        if act == "dash-request-cancel":
            if not me or me["role"] != "admin":
                return self._fail("관리자만 처리할 수 있습니다.", 403)
            b = self._body() or {}
            db = st.requests()
            n = len(db["items"])
            db["items"] = [x for x in db["items"] if x["id"] != b.get("id")]
            st.save_requests(db)
            return self._json({"ok": True, "removed": n - len(db["items"])})

        # 구현하지 않은 나머지 api/* — 화면이 조용히 넘어가도록 형식만 맞춘다
        return self._json({"ok": False, "error": "not implemented"}, 404)

    # ---- 정적 (Range 지원 — 영상 구간 반복에 필요) ----
    def _static(self, body: bool):
        path = self.translate_path(urllib.parse.urlsplit(self.path).path)
        if os.path.isdir(path):
            idx = os.path.join(path, "index.html")
            if os.path.isfile(idx):
                path = idx
        if not os.path.isfile(path):
            return self.send_error(404, "Not Found")
        size = os.path.getsize(path)
        ctype = self.guess_type(path)
        m = RANGE_RE.match(self.headers.get("Range", "") or "")
        if not m:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(size))
            self.end_headers()
            if body:
                with open(path, "rb") as f:
                    self._pump(f, size)
            return
        s_raw, e_raw = m.group(1), m.group(2)
        if s_raw == "":
            length = min(int(e_raw or 0), size)
            start, end = size - length, size - 1
        else:
            start = int(s_raw)
            end = min(int(e_raw) if e_raw else size - 1, size - 1)
        if start >= size or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return
        self.send_response(206)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        if body:
            with open(path, "rb") as f:
                f.seek(start)
                self._pump(f, end - start + 1)

    def _pump(self, f, remaining, chunk=64 * 1024):
        try:
            while remaining > 0:
                buf = f.read(min(chunk, remaining))
                if not buf:
                    break
                self.wfile.write(buf)
                remaining -= len(buf)
        except (BrokenPipeError, ConnectionResetError):
            pass


def slugify_id(s: str) -> str:
    """요청 id 는 우리가 만든 값이지만, 밖에서 들어온 것으로 취급해 한 번 더 거른다."""
    return re.sub(r"[^A-Za-z0-9-]", "", s or "")[:60]


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def lan_ips():
    ips = set()
    for probe in ("8.8.8.8", "10.255.255.255"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((probe, 1))
            ips.add(s.getsockname()[0])
        except OSError:
            pass
        finally:
            s.close()
    return sorted(i for i in ips if not i.startswith("127."))


def main():
    ap = argparse.ArgumentParser(description="MAPS 등록요청 백엔드 (참조 구현)")
    ap.add_argument("--root", required=True, help="웹 루트 (wwwroot)")
    ap.add_argument("--data", required=True, help="데이터 폴더 — 웹 루트 밖이어야 한다")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()

    root, data = Path(a.root).resolve(), Path(a.data).resolve()
    if not root.is_dir():
        raise SystemExit(f"[중단] 웹 루트가 없습니다: {root}")
    if data == root or data.is_relative_to(root):
        raise SystemExit(f"[중단] --data 는 웹 루트 밖이어야 합니다.\n"
                         f"  안에 두면 http://…/data/accounts.json 으로 계정이 그대로 읽힙니다.")

    Handler.store = Store(root, data)
    srv = Server(("", a.port), Handler)

    print("=" * 64)
    print(f"  MAPS 백엔드  ·  웹루트 {root}")
    print(f"                데이터 {data}")
    print(f"  내 PC : http://localhost:{a.port}/")
    for ip in lan_ips():
        print(f"  동료  : http://{ip}:{a.port}/")
    print("  관리자 : admin / maps2026!   (1차)")
    print("           manager / maps2026! (2차)")
    print("=" * 64)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
