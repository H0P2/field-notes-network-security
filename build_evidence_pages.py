#!/usr/bin/env python3
"""Build self-contained-browser-safe HTML views of local Markdown, Python and JSON evidence."""
from __future__ import annotations

import html
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent
BACKTICK = chr(96)
FENCE = BACKTICK * 3


def view_path(source: Path) -> Path:
    suffix = source.suffix.lower()
    if suffix == ".py":
        return source.with_name(f"{source.stem}-source.html")
    if suffix == ".json":
        return source.with_name(f"{source.stem}-data.html")
    return source.with_suffix(".html")


def is_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines) or not lines[index].lstrip().startswith("|"):
        return False
    divider = lines[index + 1].strip()
    return bool(re.fullmatch(r"\|?[\s:|-]+\|?", divider)) and "-" in divider


def rewrite_local_link(url: str, source: Path) -> str:
    parts = urlsplit(url)
    if parts.scheme or parts.netloc or not parts.path:
        return url
    candidate = (source.parent / unquote(parts.path)).resolve()
    if candidate.suffix.lower() in {".md", ".py", ".json"} and candidate.is_file():
        rendered = os.path.relpath(view_path(candidate), source.parent).replace(os.sep, "/")
        return urlunsplit(("", "", rendered, parts.query, parts.fragment))
    return url


def inline(text: str, source: Path) -> str:
    held: list[str] = []

    def hold(markup: str) -> str:
        token = f"ZZHOLD{len(held)}ZZ"
        held.append(markup)
        return token

    code_pattern = re.compile(re.escape(BACKTICK) + r"([^" + re.escape(BACKTICK) + r"]+)" + re.escape(BACKTICK))

    def code_span(match: re.Match[str]) -> str:
        return hold(f"<code>{html.escape(match.group(1))}</code>")

    text = code_pattern.sub(code_span, text)

    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    def link_span(match: re.Match[str]) -> str:
        label, raw_url = match.group(1), match.group(2).strip()
        url = rewrite_local_link(raw_url, source)
        safe_url = html.escape(url, quote=True)
        if urlsplit(url).scheme in {"http", "https"}:
            return hold(f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">{html.escape(label)}</a>')
        return hold(f'<a href="{safe_url}">{html.escape(label)}</a>')

    text = link_pattern.sub(link_span, text)
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    url_pattern = re.compile(r"(?<![\"'=])https?://[^\s<]+")

    def autolink(match: re.Match[str]) -> str:
        raw = match.group(0)
        trailing = ""
        while raw and raw[-1] in ".,;:)":
            trailing = raw[-1] + trailing
            raw = raw[:-1]
        if not raw:
            return match.group(0)
        safe_url = html.escape(raw, quote=True)
        return f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">{html.escape(raw)}</a>{trailing}'

    text = url_pattern.sub(autolink, text)
    for index, markup in enumerate(held):
        text = text.replace(f"ZZHOLD{index}ZZ", markup)
    return text


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def markdown_body(source: Path) -> str:
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    blocks: list[str] = []
    index = 0
    skipped_title = False
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith(FENCE):
            language = stripped[len(FENCE):].strip()
            index += 1
            code_lines: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith(FENCE):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            lang_class = f' class="language-{html.escape(language, quote=True)}"' if language else ""
            blocks.append(f"<pre class=\"code-block\"><code{lang_class}>{html.escape(chr(10).join(code_lines))}</code></pre>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", stripped)
        if heading:
            level = len(heading.group(1))
            if level == 1 and not skipped_title:
                skipped_title = True
            else:
                blocks.append(f"<h{level}>{inline(heading.group(2), source)}</h{level}>")
            index += 1
            continue
        if re.fullmatch(r"(?:-{3,}|\*{3,}|_{3,})", stripped):
            blocks.append("<hr>")
            index += 1
            continue
        if is_table_start(lines, index):
            headers = table_cells(lines[index])
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(table_cells(lines[index]))
                index += 1
            head = "".join(f"<th scope=\"col\">{inline(cell, source)}</th>" for cell in headers)
            body_rows = []
            for row in rows:
                cells = "".join(f"<td>{inline(cell, source)}</td>" for cell in row)
                body_rows.append(f"<tr>{cells}</tr>")
            blocks.append(f'<div class="table-scroll"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>')
            continue
        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_lines.append(re.sub(r"^\s*>\s?", "", lines[index].strip()))
                index += 1
            blocks.append(f'<blockquote><p>{inline(" ".join(quote_lines), source)}</p></blockquote>')
            continue
        list_match = re.match(r"^\s*([-*]|\d+\.)\s+(.+)$", line)
        if list_match:
            ordered = list_match.group(1).endswith(".")
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            while index < len(lines):
                current = re.match(r"^\s*([-*]|\d+\.)\s+(.+)$", lines[index])
                if not current or current.group(1).endswith(".") != ordered:
                    break
                items.append(f"<li>{inline(current.group(2), source)}</li>")
                index += 1
            blocks.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue
        if stripped.startswith("<"):
            blocks.append(f"<p>{inline(stripped, source)}</p>")
            index += 1
            continue
        paragraph = [stripped]
        index += 1
        while index < len(lines):
            next_line = lines[index]
            next_stripped = next_line.strip()
            if not next_stripped or next_stripped.startswith(FENCE) or re.match(r"^#{1,6}\s", next_stripped) or next_stripped.startswith(">") or re.match(r"^\s*([-*]|\d+\.)\s+", next_line) or is_table_start(lines, index) or re.fullmatch(r"(?:-{3,}|\*{3,}|_{3,})", next_stripped):
                break
            paragraph.append(next_stripped)
            index += 1
        blocks.append(f"<p>{inline(' '.join(paragraph), source)}</p>")
    return "\n".join(blocks)


def display_name(source: Path) -> str:
    stem = source.stem.replace("-", " ").replace("_", " ")
    return " ".join(part.capitalize() if part.isascii() else part for part in stem.split())


def document_html(source: Path) -> str:
    destination = view_path(source)
    relative = source.relative_to(ROOT).as_posix()
    stylesheet = os.path.relpath(ROOT / "evidence.css", destination.parent).replace(os.sep, "/")
    favicon = os.path.relpath(ROOT / "favicon.svg", destination.parent).replace(os.sep, "/")
    home = os.path.relpath(ROOT / "index.html", destination.parent).replace(os.sep, "/")
    overview_path = ROOT / "evidence" / "projects" / "README.html"
    overview = os.path.relpath(overview_path, destination.parent).replace(os.sep, "/")
    name = display_name(source)
    is_markdown = source.suffix.lower() == ".md"
    if is_markdown:
        body = f'<article class="report-copy">{markdown_body(source)}</article>'
        kind = "EVIDENCE / REPORT"
        title = re.search(r"^#\s+(.+)$", source.read_text(encoding="utf-8-sig"), re.M)
        page_title = title.group(1).strip() if title else name
        deck = "실제 입력 표본의 값과 범위를 확인하는 기록입니다. 아래 수치는 본문에 표시된 표본·한계 안에서 해석해야 합니다."
        note = "이 화면은 사이트 안에서 바로 읽도록 만든 HTML 보기입니다. 원본 표본과 분석 한계는 보고서 본문을 따릅니다."
    else:
        raw = source.read_text(encoding="utf-8-sig")
        code_lines = raw.splitlines()
        lines_markup = "\n".join(
            f'<span class="code-line"><span class="line-number" aria-hidden="true">{number:03d}</span><span class="line-content">{html.escape(line) if line else "&nbsp;"}</span></span>'
            for number, line in enumerate(code_lines, 1)
        )
        kind = "SOURCE / " + ("PYTHON" if source.suffix.lower() == ".py" else "JSON")
        kind_name = {
            "flowlens": "FlowLens 코드",
            "authsentry": "AuthSentry 코드",
            "secretfence": "SecretFence 코드",
            "publishgate": "PublishGate 코드",
            "independent-audit": "독립 대조 스크립트",
            "evidence-manifest": "PublishGate 증거 manifest",
        }.get(source.stem.lower(), name)
        page_title = kind_name
        deck = "원본 파일을 이 페이지 안에서 확인할 수 있도록 줄 번호와 함께 표시했습니다."
        note = "줄 번호는 화면에서 읽기 위한 표시입니다. 실제 분석 코드는 아래 원문 그대로입니다."
        body = f'<section class="source-panel" aria-label="소스 파일 본문"><div class="source-meta"><span>{html.escape(source.name)}</span><span>{len(code_lines):,} lines</span></div><pre class="source-view"><code>{lines_markup}</code></pre></section>'
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <meta name="description" content="검증된 네트워크·보안 프로젝트의 {html.escape(kind.lower())} 보기">
  <title>{html.escape(page_title)} — FIELD NOTES</title>
  <link rel="icon" type="image/svg+xml" href="{html.escape(favicon, quote=True)}">
  <link rel="stylesheet" href="{html.escape(stylesheet, quote=True)}">
</head>
<body>
  <header class="reader-header">
    <a class="reader-brand" href="{html.escape(home, quote=True)}"><span class="reader-mark" aria-hidden="true">•</span><span>FIELD NOTES <small>/ EVIDENCE</small></span></a>
    <nav aria-label="기록 내비게이션"><a href="{html.escape(overview, quote=True)}">기록 목록</a><a class="back-link" href="{html.escape(home, quote=True)}">소개 페이지로 <span aria-hidden="true">↗</span></a></nav>
  </header>
  <main class="reader-shell">
    <p class="reader-kicker"><span class="reader-signal" aria-hidden="true"></span>{html.escape(kind)} <span class="reader-path">{html.escape(relative)}</span></p>
    <h1 class="reader-title">{html.escape(page_title)}</h1>
    <p class="reader-deck">{html.escape(deck)}</p>
    {body}
    <aside class="reader-note"><span aria-hidden="true">↳</span><p>{html.escape(note)}</p></aside>
  </main>
  <footer class="reader-footer"><span>FIELD NOTES / SOURCE TRACE</span><a href="{html.escape(home, quote=True)}">페이지로 돌아가기 ↑</a></footer>
</body>
</html>
"""


def main() -> int:
    extensions = {".md", ".py", ".json"}
    sources = sorted(
        path for path in ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in extensions and path.name != Path(__file__).name
    )
    for source in sources:
        view_path(source).write_text(document_html(source), encoding="utf-8")
    print(f"HTML 보기 생성: {len(sources)}개")
    for source in sources:
        print(f"- {source.relative_to(ROOT).as_posix()} -> {view_path(source).relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
