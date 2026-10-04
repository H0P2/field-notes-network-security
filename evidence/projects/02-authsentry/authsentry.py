#!/usr/bin/env python3
"""Summarize real Cowrie session aggregates without exposing identifiers or credentials."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TextIO


@dataclass(frozen=True)
class SessionSummary:
    first_seen_day: date
    source: str
    failed_logins: int
    successful_logins: int


def parse_count(value: object, field: str) -> int:
    if type(value) is not int and not (isinstance(value, str) and value.strip().isascii() and value.strip().isdigit()):
        raise ValueError(f"{field} must be a non-negative integer")
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a non-negative integer") from None
    if result < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return result


def parse_first_seen(value: object) -> date:
    if not isinstance(value, str):
        raise ValueError("first_seen must be a timestamp string")
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).date()
    except ValueError:
        raise ValueError("first_seen must be an ISO timestamp") from None


def open_text(path: Path) -> TextIO:
    if path.name.lower().endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("r", encoding="utf-8-sig", newline="")


def load_cowrie_jsonl(path: Path) -> tuple[list[SessionSummary], list[int]]:
    sessions: list[SessionSummary] = []
    invalid: list[int] = []
    with open_text(path) as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("record must be an object")
                source = record.get("src_ip")
                if not isinstance(source, str) or not source.strip():
                    raise ValueError("src_ip is required")
                sessions.append(SessionSummary(
                    first_seen_day=parse_first_seen(record.get("first_seen")),
                    source=source.strip(),
                    failed_logins=parse_count(record.get("cnt_login_failed", 0), "cnt_login_failed"),
                    successful_logins=parse_count(record.get("cnt_login_success", 0), "cnt_login_success"),
                ))
            except (json.JSONDecodeError, ValueError):
                invalid.append(line_number)
    return sessions, invalid


def source_aliases(sessions: list[SessionSummary]) -> dict[str, str]:
    totals: Counter[str] = Counter()
    for session in sessions:
        totals[session.source] += session.failed_logins
    ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    return {source: f"source-{number:02d}" for number, (source, _) in enumerate(ordered, 1)}


def make_report(sessions: list[SessionSummary], invalid: list[int], top: int, input_bytes: int, input_sha256: str, source_url: str | None, source_range_sha256: str | None, sample_note: str | None, limitation: str | None) -> str:
    failed_by_day: Counter[date] = Counter()
    successful_by_day: Counter[date] = Counter()
    failures_by_source_day: Counter[tuple[str, date]] = Counter()
    failures_by_source: Counter[str] = Counter()
    for session in sessions:
        failed_by_day[session.first_seen_day] += session.failed_logins
        successful_by_day[session.first_seen_day] += session.successful_logins
        failures_by_source_day[(session.source, session.first_seen_day)] += session.failed_logins
        failures_by_source[session.source] += session.failed_logins

    aliases = source_aliases(sessions)
    source_days = sorted(
        ((source, day, count) for (source, day), count in failures_by_source_day.items() if count),
        key=lambda row: (-row[2], row[1], aliases[row[0]]),
    )
    days = sorted(failed_by_day, key=lambda day: (-failed_by_day[day], day))[:top]

    lines = [
        "# AuthSentry — Cowrie 인증 세션 요약", "", "## 데이터 요약", "",
        f"- 세션 집계 레코드: {len(sessions):,}건",
        f"- 실패 로그인 이벤트 합계: {sum(failed_by_day.values()):,}건",
        f"- 성공 로그인 이벤트 합계: {sum(successful_by_day.values()):,}건",
        f"- 관측된 source 수: {len(failures_by_source):,}개",
        f"- 제외된 레코드: {len(invalid):,}건",
        f"- 입력 파일 크기: {input_bytes:,} bytes",
        f"- 입력 파일 SHA-256: `{input_sha256}`",
    ]
    if source_url:
        lines.append(f"- 원본 출처: {source_url}")
    if source_range_sha256:
        lines.append(f"- 내려받은 원본 구간 SHA-256: `{source_range_sha256}`")
    if sample_note:
        lines.append(f"- 입력 구간: {sample_note}")
    if limitation:
        lines.append(f"- 표본 한계: {limitation}")
    lines.extend([
        "- 사용자명·비밀번호 열: 읽지 않음",
        "- source 표시: 보고서별 별칭만 출력", "",
        "## 날짜별 로그인 이벤트", "",
        "이 데이터는 세션 단위 집계이므로 한 세션의 로그인 이벤트를 `first_seen` 날짜에 귀속했습니다.", "",
        "| first_seen 날짜 | 실패 로그인 | 성공 로그인 |", "| --- | ---: | ---: |",
    ])
    for day in days:
        lines.append(f"| {day.isoformat()} | {failed_by_day[day]:,} | {successful_by_day[day]:,} |")
    if not days:
        lines.append("| 로그인 이벤트 없음 | 0 | 0 |")

    lines.extend(["", "## 실패 로그인 상위 source·날짜 조합", "", "| source 별칭 | 날짜 | 실패 로그인 |", "| --- | --- | ---: |"])
    for source, day, count in source_days[:top]:
        lines.append(f"| {aliases[source]} | {day.isoformat()} | {count:,} |")
    if not source_days:
        lines.append("| 실패 로그인 없음 | — | 0 |")

    if invalid:
        examples = ", ".join(str(number) for number in invalid[:10])
        if len(invalid) > 10:
            examples += " …"
        lines.extend(["", f"잘못된 레코드는 건너뛰었습니다. 행 번호(최대 10개): {examples}"])
    lines.extend([
        "", "> 이것은 Cowrie honeypot에서 관측된 unsolicited SSH 상호작용의 집계입니다. 실제 인터넷 전체의 공격률을 대표하지 않습니다.",
        "> `first_seen` 날짜로 세션 집계치를 묶은 요약이며, 개별 로그인 시각이나 사용자명별 password-spray를 판정하지 않습니다.",
        "> 보고서에는 source 원문, 사용자명, 비밀번호를 내보내지 않습니다.",
    ])
    return "\n".join(lines) + "\n"


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("양의 정수를 입력하세요") from None
    if number < 1:
        raise argparse.ArgumentTypeError("양의 정수를 입력하세요")
    return number


def input_fingerprint(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cowrie JSONL session aggregation을 로컬에서 요약합니다.")
    parser.add_argument("input", type=Path, help="session_aggregation.jsonl 또는 .jsonl.gz")
    parser.add_argument("-o", "--output", type=Path, help="보고서 경로 (기본값: 입력 파일 옆 authsentry-report.md)")
    parser.add_argument("--top", type=positive_int, default=20, help="표에 표시할 최대 행 수 (기본값: 20)")
    parser.add_argument("--source-url", help="입력 원본의 공개 출처 URL")
    parser.add_argument("--source-range-sha256", help="내려받은 원본 바이트 구간의 SHA-256")
    parser.add_argument("--sample-note", help="입력한 실제 표본의 범위와 변환 설명")
    parser.add_argument("--limitation", help="결과를 과대해석하지 않도록 표본/자료의 한계 설명")
    args = parser.parse_args(argv)
    if args.top > 100:
        parser.error("--top은 100 이하여야 합니다")
    output = args.output or args.input.with_name("authsentry-report.md")
    try:
        sessions, invalid = load_cowrie_jsonl(args.input)
        if not sessions:
            raise ValueError("분석할 유효한 세션 집계가 없습니다")
        input_bytes, input_sha256 = input_fingerprint(args.input)
        report = make_report(sessions, invalid, args.top, input_bytes, input_sha256, args.source_url, args.source_range_sha256, args.sample_note, args.limitation)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
    except (OSError, UnicodeError, gzip.BadGzipFile, ValueError) as exc:
        print(f"AuthSentry 오류: {exc}", file=sys.stderr)
        return 1
    print(f"보고서 저장: {output}")
    if invalid:
        print(f"주의: 잘못된 레코드 {len(invalid)}개를 제외했습니다.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
