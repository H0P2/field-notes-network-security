#!/usr/bin/env python3
"""Scan a local publish tree and optional Git history without printing matched values."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

IGNORED_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", ".tox", "dist", "build", "coverage"}
MAX_FILE_BYTES = 2_000_000

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("credential_assignment", re.compile(r"(?i)(?<![A-Za-z0-9])(?:password|passwd|secret|token|api[_-]?key)(?![A-Za-z0-9])\s*[:=]\s*['\"]?([^\s'\"#,;]{8,})")),
    ("cloud_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("openai_style_token", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("private_key_header", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("email_address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    ("korean_mobile_number", re.compile(r"(?<!\d)01[016789]-?\d{3,4}-?\d{4}(?!\d)")),
    ("url_user_password", re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^:/\s]+:[^@/\s]+@")),
)

# Git grep uses POSIX extended regular expressions, so keep equivalent patterns here.
GIT_PATTERNS = (
    r"(^|[^[:alnum:]])(password|passwd|secret|token|api[_-]?key)([^[:alnum:]])[[:space:]]*[:=][[:space:]]*['\"]?[^ '\"#,;]{8,}",
    r"AKIA[0-9A-Z]{16}",
    r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"sk-(proj-)?[A-Za-z0-9_-]{20,}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}",
    r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    r"01[016789]-?[0-9]{3,4}-?[0-9]{4}",
    r"[a-z][a-z0-9+.-]*://[^:/[:space:]]+:[^@/[:space:]]+@",
)


@dataclass(frozen=True, order=True)
class Finding:
    location: str
    line: int
    category: str


def scan_file(path: Path, root: Path) -> tuple[list[Finding], str]:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return [], "skipped_oversized"
        raw = path.read_bytes()
    except OSError:
        return [], "unreadable_file"
    if b"\0" in raw:
        return [], "skipped_binary"
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], "skipped_non_utf8"
    relative = path.relative_to(root).as_posix().replace("|", "\\|")
    findings: list[Finding] = []
    for line_number, line in enumerate(content.splitlines(), 1):
        for category, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(Finding(relative, line_number, category))
    return findings, "scanned"


def files_under(root: Path, counts: dict[str, int]) -> Iterator[Path]:
    for path in root.rglob("*"):
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in IGNORED_DIRS for part in relative_parts):
            continue
        if path.is_symlink():
            counts["skipped_symlink"] += 1
            continue
        if path.is_file():
            yield path


def scan_worktree(root: Path) -> tuple[list[Finding], dict[str, int]]:
    findings: set[Finding] = set()
    counts = {"scanned": 0, "skipped_oversized": 0, "skipped_binary": 0, "skipped_non_utf8": 0, "skipped_symlink": 0, "unreadable_file": 0}
    for path in files_under(root, counts):
        found, status = scan_file(path, root)
        findings.update(found)
        counts[status] += 1
    return sorted(findings), counts


def scan_history(root: Path, commit_limit: int) -> tuple[list[Finding], bool]:
    try:
        git = subprocess.run(
            ["git", "-C", str(root), "rev-list", "--all", f"--max-count={commit_limit + 1}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
    except OSError as exc:
        if isinstance(exc, FileNotFoundError):
            raise RuntimeError("Git executable is not available; history scan was not performed") from None
        raise RuntimeError("Git could not be started; history scan was not performed") from None
    if git.returncode != 0:
        raise RuntimeError("Git history could not be read; check that the folder is a Git repository and Git is installed")
    commits = git.stdout.splitlines()
    truncated = len(commits) > commit_limit
    commits = commits[:commit_limit]
    findings: set[Finding] = set()
    for commit in commits:
        command = ["git", "-C", str(root), "grep", "--no-color", "-n", "-I", "-E"]
        for pattern in GIT_PATTERNS:
            command.extend(["-e", pattern])
        command.extend([commit, "--"])
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace")
        assert process.stdout is not None
        for output_line in process.stdout:
            parts = output_line.rstrip("\r\n").split(":", 3)
            if len(parts) < 3:
                continue
            try:
                line_number = int(parts[2])
            except ValueError:
                continue
            path = parts[1].replace("|", "\\|")
            findings.add(Finding(f"git:{commit[:10]}/{path}", line_number, "history_match"))
        return_code = process.wait()
        # git grep returns 1 when the commit has no matches; other non-zero codes are errors.
        if return_code not in (0, 1):
            raise RuntimeError("Git could not inspect one or more commits")
    return sorted(findings), truncated


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("양의 정수를 입력하세요") from None
    if number < 1:
        raise argparse.ArgumentTypeError("양의 정수를 입력하세요")
    return number


def format_report(findings: list[Finding], counts: dict[str, int], history_requested: bool, history_truncated: bool) -> str:
    lines = [
        "# SecretFence — 공개 프로젝트 패키지 검사", "",
        f"- 발견 항목: {len(findings)}건",
        f"- 내용 검사 완료 파일: {counts['scanned']}개",
        f"- 2MB 초과로 건너뜀: {counts['skipped_oversized']}개",
        f"- 바이너리로 건너뜀: {counts['skipped_binary']}개",
        f"- UTF-8이 아니라 건너뜀: {counts['skipped_non_utf8']}개",
        f"- 심볼릭 링크로 건너뜀: {counts['skipped_symlink']}개",
        f"- 읽기 오류: {counts['unreadable_file']}개",
        f"- Git 이력 검사: {'요청됐으나 커밋 한도에서 잘림' if history_truncated else ('요청됨' if history_requested else '미검사')}", "",
    ]
    if findings:
        lines.extend(["## 발견 항목", ""])
        lines.extend(f"- `{item.location}:{item.line}` - {item.category} (원문 미표시)" for item in findings)
    else:
        lines.append("지정한 텍스트 패턴 발견 0건입니다. 이 결과는 검사 규칙과 범위 안에서만 유효합니다.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="폴더와 선택한 Git 기록에서 비밀값·연락처 패턴을 찾아 원문 없이 보고합니다.")
    parser.add_argument("root", type=Path, help="공개 전에 점검할 폴더")
    parser.add_argument("-o", "--output", type=Path, help="검사 요약 Markdown 저장 경로 (선택)")
    parser.add_argument("--git-history", action="store_true", help="모든 로컬 브랜치의 Git 커밋 트리도 점검")
    parser.add_argument("--commit-limit", type=positive_int, default=1000, help="Git 기록 점검 최대 커밋 수 (기본값: 1000)")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise RuntimeError("점검 경로는 폴더여야 합니다")
        findings, scan_counts = scan_worktree(root)
        history_truncated = False
        if args.git_history:
            history_findings, history_truncated = scan_history(root, args.commit_limit)
            findings = sorted(set(findings).union(history_findings))
    except (OSError, RuntimeError) as exc:
        print(f"SecretFence 오류: {exc}", file=sys.stderr)
        return 2

    print("SecretFence 로컬 점검 결과")
    print(f"발견 항목: {len(findings)}")
    print(f"내용 검사 완료 파일: {scan_counts['scanned']}")
    print(f"2MB 초과로 건너뜀: {scan_counts['skipped_oversized']}")
    print(f"바이너리로 건너뜀: {scan_counts['skipped_binary']}")
    print(f"UTF-8이 아니라 건너뜀: {scan_counts['skipped_non_utf8']}")
    print(f"심볼릭 링크로 건너뜀: {scan_counts['skipped_symlink']}")
    print(f"읽기 오류: {scan_counts['unreadable_file']}")
    for finding in findings:
        print(f"- {finding.location}:{finding.line} - {finding.category} (값은 표시하지 않음)")
    if history_truncated:
        print(f"주의: Git 기록이 커밋 한도 {args.commit_limit}개를 넘어 전체를 확인하지 못했습니다.")
    skipped = any(scan_counts[key] for key in ("skipped_oversized", "skipped_binary", "skipped_non_utf8", "skipped_symlink"))
    if scan_counts["unreadable_file"] or skipped:
        print("주의: 일부 항목은 내용 검사를 완료하지 못했습니다. 공개 전에 별도 확인이 필요합니다.")
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(format_report(findings, scan_counts, args.git_history, history_truncated), encoding="utf-8")
            print(f"요약 저장: {args.output}")
        except OSError as exc:
            print(f"SecretFence 오류: 요약을 저장할 수 없습니다 ({exc})", file=sys.stderr)
            return 2
    if findings or scan_counts["unreadable_file"] or history_truncated or skipped:
        return 1
    print("검사한 파일에서 지정 패턴을 찾지 못했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
