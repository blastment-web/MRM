#!/usr/bin/env python3
"""리허설 꾸러미(zip) 를 만든다.

## 왜 스크립트인가

지금까지 꾸러미는 손으로 모아 압축했다. 그 결과 "새 파일을 보냈는데 예전 화면이
그대로" 가 반복됐다 — 새 zip 을 안 풀었는지, 풀었는데 배치를 안 돌렸는지,
브라우저 캐시인지 구분할 방법이 없었다.

그래서 꾸러미에 **빌드 스탬프**를 세 군데 같은 값으로 박는다.

    zip 파일 이름      MAPS-실험-<스탬프>.zip
    풀린 폴더 이름     MAPS-실험-<스탬프>\\
    폴더 안 빌드.txt   화면별 스탬프 목록

`1_서버켜기.bat` 이 꾸러미 파일과 **서버가 실제로 내보내는 응답**에서 각각 스탬프를
뽑아 나란히 찍으므로, 어긋나면 어디서 끊겼는지 한 줄로 드러난다.

스탬프는 시각이 아니라 **내용 해시**다. 내용이 같으면 두 번 만들어도 같은 이름이 나온다.

## 사용법

    python3 tools/make_rehearsal_zip.py              # dist/ 에 zip 생성
    python3 tools/make_rehearsal_zip.py --rebuild    # 릴리스부터 다시 만들고 압축
    python3 tools/make_rehearsal_zip.py --out /tmp
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_stamp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REH = ROOT / "tools" / "rehearsal"

# index-<이름>.html 하나가 주소 하나가 된다. 왼쪽이 원본, 오른쪽이 꾸러미 안 이름.
SCREENS = {
    "v4-1": ROOT / "releases" / "MAPS-V4-1" / "index.standalone.html",
    "v4-2": ROOT / "releases" / "MAPS-V4-2" / "index.standalone.html",
}
# 선택 화면은 없앴다 - 주소창에 IP 만 치면 곧바로 MAIN 화면이 뜬다.
FLAT = ["1_서버켜기.bat", "2_서버끄기.bat", "3_에이전트연결.bat", "읽어보세요.txt"]
TREES = ["api", "agents"]

# 샘플 카드 하나를 LIVE 로 켜 둔다 — 팝업이 실제로 열리는지 바로 볼 수 있게.
LIVE_NAME = "공정 조건 최적화 Agent"
LIVE_ADDR = "http://localhost/agents/sample-agent/"


def rebuild() -> None:
    """릴리스 → standalone 까지 다시 만든다. 꾸러미가 옛 산출물을 담는 일을 막는다."""
    run = lambda *a: subprocess.run([sys.executable, *a], cwd=ROOT, check=True,
                                    stdout=subprocess.DEVNULL)
    run("tools/build_v4.py")
    for slug, src in SCREENS.items():
        run("tools/build_standalone.py", str(src.parent / "index.html"), str(src))
    run("tools/make_rehearsal_bats.py")


def stage(tmp: Path) -> dict:
    """꾸러미 내용을 tmp 에 모으고 화면별 스탬프를 돌려준다."""
    tmp.mkdir(parents=True)
    for n in FLAT:
        src = REH / n
        if not src.is_file():
            raise SystemExit(f"[중단] 꾸러미 구성 파일이 없습니다: {src}")
        shutil.copy2(src, tmp / n)
    for n in TREES:
        if (REH / n).is_dir():
            shutil.copytree(REH / n, tmp / n)

    stamps = {}
    for slug, src in SCREENS.items():
        if not src.is_file():
            raise SystemExit(f"[중단] 화면 파일이 없습니다: {src}\n  먼저 --rebuild 로 만드세요.")
        text = src.read_text(encoding="utf-8")
        got = build_stamp.read(text)
        want = build_stamp.compute(text)
        if not got:
            raise SystemExit(f"[중단] {src} 에 빌드 스탬프가 없습니다 — 빌더를 다시 돌리세요.")
        if got != want:
            raise SystemExit(
                f"[중단] {src} 의 스탬프가 내용과 맞지 않습니다 ({got} != {want}).\n"
                f"  빌드 뒤에 파일을 직접 고쳤다는 뜻입니다. 빌더로 다시 만드세요."
            )
        shutil.copy2(src, tmp / f"index-{slug}.html")
        stamps[slug] = got

    (tmp / "data").mkdir()
    subprocess.run(
        [sys.executable, "tools/make_dashboards_json.py",
         "--out", str(tmp / "data" / "dashboards.json"),
         "--live", LIVE_NAME, "--addr", LIVE_ADDR],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
    )
    return stamps


def pkg_stamp(tmp: Path) -> str:
    """폴더 전체 내용의 해시 8자. 파일 하나만 달라져도 값이 바뀐다."""
    h = hashlib.sha256()
    for p in sorted(tmp.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(tmp).as_posix().encode("utf-8"))
            h.update(b"\0")
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()[:8]


BUILD_TXT = """MAPS 리허설 꾸러미 - 빌드 표시

  꾸러미 : {pkg}
{lines}
이 값이 왜 있나
  "고쳤는데 화면은 그대로" 를 두 갈래로 가르기 위한 것입니다.

  1_서버켜기.bat 을 관리자 권한으로 실행하면 화면마다 두 값을 나란히 찍습니다.

     /v4-1/  200   꾸러미 {first}   서버 {first}   같음

  - 두 값이 다르다  -> 배치가 복사를 못 했습니다. 배치를 다시 실행하세요.
  - 두 값이 같은데 화면이 예전 그대로다  -> 브라우저 캐시입니다. Ctrl+F5.

  화면 맨 아래 푸터에도 같은 값이 "build {first}" 로 찍혀 있습니다.
  지금 보고 있는 화면이 어느 것인지 그 줄로 확인할 수 있습니다.
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="리허설 꾸러미 zip 생성")
    ap.add_argument("--rebuild", action="store_true", help="릴리스부터 다시 만든 뒤 압축")
    ap.add_argument("--out", default=str(ROOT / "dist"), help="zip 을 놓을 폴더")
    args = ap.parse_args()

    if args.rebuild:
        print("[다시 빌드]")
        rebuild()

    work = Path(args.out) / ".stage"
    if work.exists():
        shutil.rmtree(work)
    tmp = work / "pkg"
    stamps = stage(tmp)
    pkg = pkg_stamp(tmp)

    first = next(iter(stamps.values()))
    lines = "".join(f"  {('index-' + s + '.html'):<20} {b}\n" for s, b in stamps.items())
    (tmp / "빌드.txt").write_bytes(
        ("﻿" + BUILD_TXT.format(pkg=pkg, lines=lines, first=first))
        .replace("\n", "\r\n").encode("utf-8")
    )

    name = f"MAPS-실험-{pkg}"
    dest = Path(args.out) / f"{name}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(tmp.rglob("*")):
            if not p.is_file():
                continue
            zi = zipfile.ZipInfo(f"{name}/{p.relative_to(tmp).as_posix()}")
            # 범용 비트 11. 세우지 않으면 Windows 탐색기가 한글 파일명을 깨뜨린다.
            zi.flag_bits |= 0x800
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, p.read_bytes())
    shutil.rmtree(work)

    print(f"\n{dest}  ({dest.stat().st_size:,} bytes)")
    print(f"  꾸러미 스탬프 : {pkg}")
    for s, b in stamps.items():
        print(f"  index-{s}.html : {b}")


if __name__ == "__main__":
    main()
