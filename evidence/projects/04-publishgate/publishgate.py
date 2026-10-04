#!/usr/bin/env python3
"""Verify real analysis reports against an evidence and provenance manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
IPV4_RE = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_public_url(value: object) -> bool:
    if not nonempty(value):
        return False
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def validate_manifest(manifest_path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    passed: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ["manifest를 읽을 수 없거나 유효한 UTF-8 JSON이 아닙니다"], passed
    if not isinstance(manifest, dict) or manifest.get("format_version") != 1:
        return ["manifest format_version 1이 필요합니다"], passed
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return ["artifacts 목록이 비어 있지 않아야 합니다"], passed

    package_root = manifest_path.parent.parent.resolve()
    ids: set[str] = set()
    for number, item in enumerate(artifacts, 1):
        prefix = f"artifacts[{number}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: 객체가 필요합니다")
            continue
        artifact_id = item.get("id")
        if not nonempty(artifact_id) or artifact_id in ids:
            errors.append(f"{prefix}.id: 중복되지 않는 이름이 필요합니다")
            continue
        ids.add(artifact_id)

        relative = item.get("report_path")
        if not nonempty(relative):
            errors.append(f"{artifact_id}: report_path가 필요합니다")
            continue
        try:
            candidate = manifest_path.parent / relative
            if candidate.is_symlink():
                raise ValueError
            report_path = candidate.resolve(strict=True)
            report_path.relative_to(package_root)
            if not report_path.is_file():
                raise ValueError
            report_raw = report_path.read_bytes()
            report = report_raw.decode("utf-8")
        except (OSError, UnicodeError, ValueError):
            errors.append(f"{artifact_id}: 보고서가 패키지 안에 없거나 읽을 수 없습니다")
            continue

        expected_report_hash = item.get("report_sha256")
        expected_input_hash = item.get("input_sha256")
        downloaded_hash = item.get("downloaded_range_sha256")
        if not isinstance(expected_report_hash, str) or not SHA256_RE.fullmatch(expected_report_hash):
            errors.append(f"{artifact_id}: report_sha256 형식이 올바르지 않습니다")
        elif sha256_bytes(report_raw) != expected_report_hash:
            errors.append(f"{artifact_id}: 공개 보고서 SHA-256이 manifest와 다릅니다")

        if not isinstance(expected_input_hash, str) or not SHA256_RE.fullmatch(expected_input_hash):
            errors.append(f"{artifact_id}: input_sha256 형식이 올바르지 않습니다")
        elif f"입력 파일 SHA-256: `{expected_input_hash}`" not in report:
            errors.append(f"{artifact_id}: 보고서에서 입력 파일 SHA-256을 확인할 수 없습니다")

        if not isinstance(downloaded_hash, str) or not SHA256_RE.fullmatch(downloaded_hash):
            errors.append(f"{artifact_id}: downloaded_range_sha256 형식이 올바르지 않습니다")
        elif f"내려받은 원본 구간 SHA-256: `{downloaded_hash}`" not in report:
            errors.append(f"{artifact_id}: 보고서에서 내려받은 원본 구간 지문을 확인할 수 없습니다")
        if not valid_public_url(item.get("source_url")):
            errors.append(f"{artifact_id}: 출처는 자격 증명·query·fragment가 없는 공개 HTTPS URL이어야 합니다")
        elif item["source_url"] not in report:
            errors.append(f"{artifact_id}: 보고서에 manifest의 공개 출처가 없습니다")

        sample_scope = item.get("sample_scope")
        if not nonempty(sample_scope) or sample_scope not in report:
            errors.append(f"{artifact_id}: 실제 표본 범위가 보고서와 연결되어야 합니다")
        limitation = item.get("limitation")
        if not nonempty(limitation) or f"표본 한계: {limitation}" not in report:
            errors.append(f"{artifact_id}: 보고서와 manifest에 같은 해석 한계가 있어야 합니다")
        if type(item.get("records_analyzed")) is not int or item["records_analyzed"] < 1:
            errors.append(f"{artifact_id}: records_analyzed는 양의 정수여야 합니다")
        elif not nonempty(item.get("record_evidence")) or item["record_evidence"] not in report:
            errors.append(f"{artifact_id}: 보고서의 기록 수 근거 문장이 필요합니다")
        else:
            count_line = re.fullmatch(r"- (?:분석 흐름|세션 집계 레코드): ([0-9]+(?:,[0-9]{3})*)건", item["record_evidence"])
            if not count_line or int(count_line.group(1).replace(",", "")) != item["records_analyzed"]:
                errors.append(f"{artifact_id}: records_analyzed와 보고서 기록 수가 다릅니다")
        if type(item.get("input_bytes")) is not int or item["input_bytes"] < 1:
            errors.append(f"{artifact_id}: input_bytes는 양의 정수여야 합니다")
        elif f"입력 파일 크기: {item['input_bytes']:,} bytes" not in report:
            errors.append(f"{artifact_id}: 보고서 입력 크기와 manifest가 다릅니다")
        if item.get("identifiers_redacted") is not True:
            errors.append(f"{artifact_id}: 식별자 비식별화 확인이 필요합니다")
        if IPV4_RE.search(report) or EMAIL_RE.search(report):
            errors.append(f"{artifact_id}: 보고서에 원문 IPv4 또는 이메일처럼 보이는 값이 있습니다")

        artifact_errors = [error for error in errors if error.startswith(f"{artifact_id}:")]
        if not artifact_errors:
            passed.append(f"{artifact_id}: 보고서 해시·입력 지문·출처·표본 범위·비식별화 통과 ({item['records_analyzed']:,}건)")

    return errors, passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="실제 분석 결과의 파일 무결성과 출처·범위·비식별화 정보를 확인합니다.")
    parser.add_argument("manifest", type=Path, help="evidence manifest JSON")
    parser.add_argument("-o", "--output", type=Path, help="확인 결과 Markdown 저장 경로 (선택)")
    args = parser.parse_args(argv)
    errors, passed = validate_manifest(args.manifest)
    lines = ["# PublishGate - 실제 증거 패키지 확인", ""]
    for item in passed:
        lines.append(f"- PASS: {item}")
    for item in errors:
        lines.append(f"- FAIL: {item}")
    if errors:
        lines.extend(["", f"결과: FAIL ({len(errors)}개 확인 항목)"])
        exit_code = 1
    else:
        lines.extend(["", f"결과: PASS ({len(passed)}개 보고서 확인)"])
        exit_code = 0
    report = "\n".join(lines) + "\n"
    print(report, end="")
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(report, encoding="utf-8")
        except OSError as exc:
            print(f"PublishGate 오류: 결과를 저장할 수 없습니다 ({exc})", file=sys.stderr)
            return 2
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
