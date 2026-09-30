#!/usr/bin/env python3
"""Build steps for the release-notes page.

  appendix  every squash-merged PR of a window, grouped by area, as an HTML snippet
  crop      cut a pixel box out of a screenshot (macOS `sips`, or Pillow)
  bundle    page.src.html + img/ + appendix -> one standalone .html (images inlined)

Examples:
  build.py appendix --since 2026-09-14 --until 2026-09-28 --out notes/appendix.html
  build.py crop notes/shots/overview.jpg notes/img/overview.jpg 372 0 1788 1330
  build.py bundle --src notes/page.src.html --images notes/img \
      --appendix notes/appendix.html --out notes/decipher-release-notes.html
"""
from __future__ import annotations

import argparse
import base64
import collections
import datetime as dt
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Conventional-commit scope -> the area heading it is listed under. Scopes not
# named here land in the last area.
AREAS: list[tuple[str, set[str]]] = [
    ("Assets, documents & signatures", {"assets", "templates", "fields", "records", "attachments"}),
    ("Configurations, fields & Wizards", {
        "configurations", "wizards", "reference-fields", "directory",
        "organizations", "persons", "people", "form-layout", "intake",
    }),
    ("Obligations & agreements", {"obligation-annotator", "agreements", "obligations"}),
    ("Search", {"search"}),
    ("Actions, discussions & alerts", {"discussions", "websockets", "alerts", "actions", "changelog", "notifications"}),
    ("Accounts, access & platform", {"accounts", "auth", "access", "experiences", "platform", "companies", "groups"}),
    ("Speed, logging & housekeeping", set()),
]
SUBJECT = re.compile(r"^([a-z]+)(?:\(([^)]*)\))?!?: (.*)$")
PR_NUMBER = re.compile(r"\s*\(#(\d+)\)\s*$")
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def repo_slug() -> str:
    url = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True
    ).stdout.strip()
    match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    return match.group(1) if match else "DecipherIP/decipher"


def cmd_appendix(args: argparse.Namespace) -> None:
    until = args.until or dt.date.today().isoformat()
    log = subprocess.run(
        ["git", "log", args.ref, f"--since={args.since} 00:00:00", f"--until={until} 23:59:59",
         "--format=%ad%x09%h%x09%s", "--date=short"],
        capture_output=True, text=True, check=True,
    ).stdout
    slug = args.repo or repo_slug()
    groups: dict[str, list[tuple[int, str, str, str]]] = collections.OrderedDict((a, []) for a, _ in AREAS)
    for line in log.splitlines():
        date, short, subject = line.split("\t", 2)
        subject = subject.replace("[REVIEW-OVERRIDE] ", "")
        match = SUBJECT.match(subject)
        scope, text = (match.group(2) or "", match.group(3)) if match else ("", subject)
        number = PR_NUMBER.search(text)
        text = PR_NUMBER.sub("", text)
        text = text[:1].upper() + text[1:]
        area = next((name for name, scopes in AREAS if scope in scopes), AREAS[-1][0])
        groups[area].append((int(number.group(1)) if number else 0, date, text, short))

    parts, total = [], 0
    for area, items in groups.items():
        if not items:
            continue
        items.sort(reverse=True)
        total += len(items)
        rows = []
        for number, date, text, short in items:
            ref = (f'<a href="https://github.com/{slug}/pull/{number}">#{number}</a>' if number
                   else f'<a href="https://github.com/{slug}/commit/{short}">{short}</a>')
            rows.append(f'<li>{ref} <span>{html.escape(text)}</span> '
                        f'<time>{date[5:].replace("-", "/")}</time></li>')
        parts.append(
            f'<section class="pr-group"><h4>{html.escape(area)} <span class="count">{len(items)}</span></h4>\n'
            f'<ul class="pr-list">\n' + "\n".join(rows) + "\n</ul></section>"
        )
    Path(args.out).write_text("\n".join(parts), encoding="utf-8")
    print(f"total {total}")
    for area, items in groups.items():
        if items:
            print(f"  {len(items):4d}  {area}")


def cmd_crop(args: argparse.Namespace) -> None:
    src, out = Path(args.src), Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("sips"):
        subprocess.run(
            ["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(args.quality),
             "-c", str(args.h), str(args.w), "--cropOffset", str(args.y), str(args.x),
             str(src), "--out", str(out)],
            check=True, capture_output=True,
        )
    else:
        from PIL import Image  # type: ignore[import-not-found]

        with Image.open(src) as image:
            image.crop((args.x, args.y, args.x + args.w, args.y + args.h)).convert("RGB").save(
                out, "JPEG", quality=args.quality
            )
    print(out)


def shrink(src: Path, max_width: int, quality: int, workdir: Path) -> Path:
    """A copy no wider than max_width; the original when no tool is available."""
    out = workdir / src.name
    if shutil.which("sips"):
        width = int(re.search(r"pixelWidth: (\d+)", subprocess.run(
            ["sips", "-g", "pixelWidth", str(src)], capture_output=True, text=True, check=True
        ).stdout).group(1))
        command = ["sips", "-s", "formatOptions", str(quality)]
        if width > max_width:
            command += ["--resampleWidth", str(max_width)]
        subprocess.run(command + [str(src), "--out", str(out)], check=True, capture_output=True)
        return out
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError:
        return src
    with Image.open(src) as image:
        if image.width > max_width:
            image = image.resize((max_width, round(image.height * max_width / image.width)))
        image.convert("RGB").save(out, "JPEG", quality=quality)
    return out


def cmd_bundle(args: argparse.Namespace) -> None:
    page = Path(args.src).read_text(encoding="utf-8")
    if "<!--APPENDIX-->" in page:
        appendix = Path(args.appendix).read_text(encoding="utf-8") if args.appendix else ""
        if not appendix:
            print("warning: no --appendix given; the placeholder is left empty", file=sys.stderr)
        page = page.replace("<!--APPENDIX-->", appendix)

    cut = page.find("</style>")
    if cut < 0:
        sys.exit("page.src.html needs its <style> block (copy assets/template.html)")
    cut += len("</style>")
    head, body = page[:cut], page[cut:]

    images = Path(args.images)
    missing: list[str] = []
    embedded = 0
    with tempfile.TemporaryDirectory() as tmp:
        def inline(match: re.Match[str]) -> str:
            nonlocal embedded
            name = match.group(1)
            path = images / name
            if not path.exists():
                missing.append(name)
                return match.group(0)
            small = shrink(path, args.max_width, args.quality, Path(tmp))
            mime = MIME.get(small.suffix.lower(), "image/jpeg")
            embedded += 1
            return f'src="data:{mime};base64,{base64.b64encode(small.read_bytes()).decode("ascii")}"'

        body = re.sub(r'src="img/([^"]+)"', inline, body)

    body = body.replace('loading="lazy"', 'decoding="async"')
    document = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<meta name=\"color-scheme\" content=\"light dark\">\n"
        f"{head.strip()}\n</head>\n<body>\n{body.strip()}\n</body>\n</html>\n"
    )
    out = Path(args.out)
    out.write_text(document, encoding="utf-8")
    print(f"{out}  {out.stat().st_size / 1e6:.2f} MB  {embedded} images inlined")
    if missing:
        sys.exit(f"missing images: {', '.join(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    appendix = sub.add_parser("appendix", help="list every merged PR of the window")
    appendix.add_argument("--since", required=True, help="YYYY-MM-DD, inclusive")
    appendix.add_argument("--until", help="YYYY-MM-DD, inclusive (default: today)")
    appendix.add_argument("--ref", default="origin/main")
    appendix.add_argument("--repo", help="owner/name for PR links (default: from origin)")
    appendix.add_argument("--out", required=True)
    appendix.set_defaults(run=cmd_appendix)

    crop = sub.add_parser("crop", help="cut a pixel box out of a screenshot")
    crop.add_argument("src")
    crop.add_argument("out")
    for name in ("x", "y", "w", "h"):
        crop.add_argument(name, type=int)
    crop.add_argument("--quality", type=int, default=84)
    crop.set_defaults(run=cmd_crop)

    bundle = sub.add_parser("bundle", help="inline images and wrap into one standalone page")
    bundle.add_argument("--src", required=True)
    bundle.add_argument("--images", required=True)
    bundle.add_argument("--appendix")
    bundle.add_argument("--out", required=True)
    bundle.add_argument("--max-width", type=int, default=1600)
    bundle.add_argument("--quality", type=int, default=78)
    bundle.set_defaults(run=cmd_bundle)

    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
