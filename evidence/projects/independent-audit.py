#!/usr/bin/env python3
"""Recompute the published real-data summaries without importing either analyzer."""
from __future__ import annotations

import argparse
import csv
import hashlib
import ipaddress
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-z0-9_.+-]{1,32}\Z")
LABEL_RE = re.compile(r"[A-Za-z0-9_.=:/+-]{1,160}\Z")
MISSING_PORTS = {"", "?", "-", "na", "none"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_port(value: str) -> int | None:
    cleaned = value.strip().lower()
    if cleaned in MISSING_PORTS:
        return None
    port = int(cleaned, 16) if cleaned.startswith("0x") else int(cleaned)
    if not 0 <= port <= 65535:
        raise ValueError("port out of range")
    return port


def check_flows(input_path: Path, report_path: Path, source_range_path: Path) -> tuple[list[str], dict[str, object]]:
    report = report_path.read_text(encoding="utf-8")
    rows: list[dict[str, str]] = []
    invalid = Counter()
    protocols: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    network_bytes: Counter[str] = Counter()
    network_flows: Counter[str] = Counter()
    source_flows: Counter[str] = Counter()
    source_bytes: Counter[str] = Counter()
    total_bytes = 0
    missing_destination_ports = 0

    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                timestamp = row["StartTime"].strip()
                parsed_time = False
                for fmt in ("%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S"):
                    try:
                        datetime.strptime(timestamp, fmt)
                        parsed_time = True
                        break
                    except ValueError:
                        pass
                if not parsed_time:
                    raise ValueError("invalid source timestamp")

                src = ipaddress.ip_address(row["SrcAddr"].strip())
                dst = ipaddress.ip_address(row["DstAddr"].strip())
                parse_port(row["Sport"])
                dst_port = parse_port(row["Dport"])
                if dst_port is None:
                    missing_destination_ports += 1
                proto = row["Proto"].strip()
                if not TOKEN_RE.fullmatch(proto):
                    raise ValueError("invalid protocol token")
                byte_count = int(row["TotBytes"].strip())
                if byte_count < 0:
                    raise ValueError("negative byte count")
                raw_label = row["Label"].strip()
                if raw_label and not LABEL_RE.fullmatch(raw_label):
                    raise ValueError("invalid label token")
            except (KeyError, TypeError, ValueError) as exc:
                invalid[str(exc)] += 1
                continue

            rows.append(row)
            total_bytes += byte_count
            protocols[proto.upper()] += 1
            normalized = raw_label.lower().removeprefix("flow=")
            if normalized.startswith("from-botnet"):
                family = "From-Botnet"
            elif normalized.startswith("to-botnet"):
                family = "To-Botnet"
            elif normalized.startswith("from-normal"):
                family = "From-Normal"
            elif normalized.startswith("to-normal"):
                family = "To-Normal"
            elif "background" in normalized:
                family = "Background"
            elif "botnet" in normalized:
                family = "Botnet (other label)"
            else:
                family = "Other"
            if raw_label:
                labels[family] += 1

            for endpoint in (src, dst):
                prefix = 24 if endpoint.version == 4 else 64
                network = str(ipaddress.ip_network(f"{endpoint}/{prefix}", strict=False))
                network_bytes[network] += byte_count
                network_flows[network] += 1
            source_network = str(ipaddress.ip_network(f"{src}/{24 if src.version == 4 else 64}", strict=False))
            source_flows[source_network] += 1
            source_bytes[source_network] += byte_count

    ordered_networks = sorted(network_bytes, key=lambda item: (-network_bytes[item], -network_flows[item], item))
    aliases = {network: f"net-{index:02d}" for index, network in enumerate(ordered_networks, 1)}
    top_source = sorted(source_flows, key=lambda net: (-source_bytes[net], -source_flows[net], aliases[net]))[0]
    expected_labels = {"Background": 15098, "From-Botnet": 128, "From-Normal": 86, "To-Normal": 1}
    checks = [
        (len(rows) == 15313, "유효 흐름 수 15,313"),
        (sum(invalid.values()) == 0, "잘못된 행 0"),
        (missing_destination_ports == 27, "미상 목적지 포트 27개를 유효 행으로 보존"),
        (total_bytes == 157353488, "전송량 합계 157,353,488 bytes"),
        (dict(labels) == expected_labels, "제공자 라벨 계열 수 일치"),
        ((aliases[top_source], source_flows[top_source], source_bytes[top_source]) == ("net-01", 6148, 58696409), "상위 출발지 별칭·흐름·bytes 일치"),
        (sha256(input_path) in report, "입력 SHA-256이 보고서와 일치"),
        (sha256(source_range_path) == "8f52127f49a3076003848bc6c5584c15b7008fb58581266190cfd8cd5c02274b", "원본 구간 SHA-256 재계산 일치"),
    ]
    return [f"{'PASS' if ok else 'FAIL'} - FlowLens: {name}" for ok, name in checks], {
        "records": len(rows), "invalid": sum(invalid.values()), "missing_destination_ports": missing_destination_ports,
        "bytes": total_bytes, "labels": dict(labels), "top_source": aliases[top_source],
        "top_source_flows": source_flows[top_source], "top_source_bytes": source_bytes[top_source],
        "input_sha256": sha256(input_path), "source_range_sha256": sha256(source_range_path),
        "all_pass": all(ok for ok, _ in checks),
    }


def check_auth(input_path: Path, report_path: Path, source_range_path: Path) -> tuple[list[str], dict[str, object]]:
    report = report_path.read_text(encoding="utf-8")
    sessions = []
    invalid = 0
    with input_path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError("record is not an object")
                sessions.append(item)
            except (json.JSONDecodeError, ValueError):
                invalid += 1

    failed = sum(int(item.get("cnt_login_failed", 0)) for item in sessions)
    successful = sum(int(item.get("cnt_login_success", 0)) for item in sessions)
    sources = {item["src_ip"] for item in sessions}
    first_seen_days = [item["first_seen"][:10] for item in sessions]
    credential_key_records = sum(any(key.lower() in {"username", "password"} for key in item) for item in sessions)
    checks = [
        (len(sessions) == 58334, "세션 집계 레코드 58,334"),
        (invalid == 0, "잘못된 JSONL 행 0"),
        ((failed, successful) == (53602, 4645), "실패/성공 로그인 합계 일치"),
        (len(sources) == 6511, "source 식별자 6,511개"),
        ((min(first_seen_days), max(first_seen_days), len(set(first_seen_days))) == ("2025-06-27", "2025-08-14", 13), "first_seen 날짜 범위/고유 날짜 수 일치"),
        (credential_key_records == 0, "username/password 키가 모든 표본 레코드에서 부재"),
        (sha256(input_path) in report, "분석 입력 SHA-256이 보고서와 일치"),
        (sha256(source_range_path) == "eadeb1736a3e36cd2547d2576a0e27f2acda14dd67fd5d946ac476bc45a3cf5a", "압축 원본 구간 SHA-256 재계산 일치"),
    ]
    return [f"{'PASS' if ok else 'FAIL'} - AuthSentry: {name}" for ok, name in checks], {
        "records": len(sessions), "invalid": invalid, "failed": failed, "successful": successful,
        "sources": len(sources), "date_min": min(first_seen_days), "date_max": max(first_seen_days),
        "distinct_days": len(set(first_seen_days)), "credential_key_records": credential_key_records,
        "input_sha256": sha256(input_path), "source_range_sha256": sha256(source_range_path),
        "all_pass": all(ok for ok, _ in checks),
    }


def check_manifest(projects: Path, manifest_path: Path) -> tuple[list[str], bool]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = []
    for item in manifest["artifacts"]:
        report_path = (manifest_path.parent / item["report_path"]).resolve()
        report = report_path.read_text(encoding="utf-8")
        ok = sha256(report_path) == item["report_sha256"] and item["input_sha256"] in report and item["source_url"] in report
        results.append((ok, item["id"]))
    return [f"{'PASS' if ok else 'FAIL'} - PublishGate manifest/report 지문 일치: {name}" for ok, name in results], all(ok for ok, _ in results)


def main() -> int:
    parser = argparse.ArgumentParser(description="분석기 코드를 가져오지 않고 실제 표본의 보고서 수치를 다시 계산합니다.")
    parser.add_argument("--projects", type=Path, required=True, help="outputs/projects 폴더")
    parser.add_argument("--work", type=Path, required=True, help="두 실제 입력 표본이 있는 로컬 폴더")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Markdown 감사 기록 경로")
    args = parser.parse_args()
    try:
        flow_checks, flow = check_flows(args.work / "ctu13-botnet42-mid-complete.binetflow", args.projects / "01-flowlens" / "flowlens-ctu13-report.md", args.work / "ctu13-botnet42-mid.bin")
        auth_checks, auth = check_auth(args.work / "cowrie-session-prefix.jsonl", args.projects / "02-authsentry" / "authsentry-cowrie-report.md", args.work / "cowrie-session-prefix.gz")
        manifest_checks, manifest_ok = check_manifest(args.projects, args.projects / "04-publishgate" / "evidence-manifest.json")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Independent audit error: {exc}", file=sys.stderr)
        return 2

    all_pass = flow["all_pass"] and auth["all_pass"] and manifest_ok
    lines = [
        "# 독립 재계산 기록", "",
        "FlowLens/AuthSentry 분석기 코드를 import하지 않고 Python 표준 라이브러리로 입력 표본을 다시 읽었습니다.",
        "", "## FlowLens", "",
        f"- 흐름 {flow['records']:,}건 / 잘못된 행 {flow['invalid']}건 / 전송량 {flow['bytes']:,} bytes",
        f"- 라벨 계열: `{json.dumps(flow['labels'], ensure_ascii=False, sort_keys=True)}`",
        f"- 미상 목적지 포트: {flow['missing_destination_ports']}건. 포트 `-`는 원본에 존재하며 FlowLens 규칙상 허용된 미상 값입니다.",
        f"- 상위 출발지 별칭: {flow['top_source']} / {flow['top_source_flows']:,} flows / {flow['top_source_bytes']:,} bytes",
        f"- 입력 SHA-256: `{flow['input_sha256']}`", "",
        "## AuthSentry", "",
        f"- 세션 집계 {auth['records']:,}건 / 잘못된 행 {auth['invalid']}건",
        f"- 실패 {auth['failed']:,} / 성공 {auth['successful']:,} / source {auth['sources']:,}",
        f"- first_seen: {auth['date_min']} - {auth['date_max']} / 서로 다른 날짜 {auth['distinct_days']}개",
        f"- username/password 키가 포함된 레코드: {auth['credential_key_records']}건",
        f"- 입력 SHA-256: `{auth['input_sha256']}`", "",
        "## 교차 확인", "", *flow_checks, *auth_checks, *manifest_checks, "",
        "초기 빠른 대조는 `Dport`의 `-`를 잘못된 값으로 처리해 27행을 제외했습니다. 실제 parser 계약을 확인해 미상 포트를 유효하게 보존한 독립 재계산에서는 전체 수치가 보고서와 일치했습니다. 분석 결과 파일은 이 교차 확인 과정에서 바꾸지 않았습니다.",
        "", f"최종 판정: {'PASS - 보고서 수치와 SHA-256이 독립 재계산과 일치' if all_pass else 'FAIL - 불일치가 있어 소개 페이지 사용 전에 수정 필요'}", "",
        "제한: 두 분석 자료는 선택된 부분 구간입니다. 일치 검사는 입력/보고서 간 재현성과 값 확인이지 원본 데이터셋 전체에 대한 통계적 대표성을 뜻하지 않습니다.",
    ]
    report = "\n".join(lines) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
