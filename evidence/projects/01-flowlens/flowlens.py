#!/usr/bin/env python3
"""Analyze authorized network flow exports locally; never opens a network connection."""
from __future__ import annotations

import argparse
import csv
import hashlib
import ipaddress
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

FIELDS = ("timestamp", "src_ip", "dst_ip", "src_port", "dst_port", "protocol", "bytes", "action")
CTU_FIELDS = {"StartTime", "SrcAddr", "Sport", "DstAddr", "Dport", "Proto", "TotBytes", "Label"}
TOKEN_RE = re.compile(r"[A-Za-z0-9_.+-]{1,32}\Z")
LABEL_RE = re.compile(r"[A-Za-z0-9_.=:/+-]{1,160}\Z")
BLOCKED_ACTIONS = {"deny", "denied", "block", "blocked", "drop", "reject"}
COMMON_PORTS = {22: "SSH", 53: "DNS", 80: "HTTP", 123: "NTP", 443: "HTTPS", 445: "SMB", 3389: "RDP"}


@dataclass(frozen=True)
class Flow:
    timestamp: datetime
    src_ip: str
    dst_ip: str
    src_port: int | None
    dst_port: int | None
    protocol: str
    byte_count: int
    action: str | None
    label_family: str | None


def parse_timestamp(value: str, ctu_format: bool = False) -> datetime:
    cleaned = value.strip()
    try:
        result = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return result
    except ValueError:
        if ctu_format:
            for pattern in ("%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S"):
                try:
                    # CTU-13 StartTime has no timezone field; retain the source clock without guessing.
                    return datetime.strptime(cleaned, pattern)
                except ValueError:
                    pass
        raise ValueError("timestamp must be timezone-aware ISO 8601 or a CTU-13 source timestamp") from None


def parse_ip(value: str, field: str) -> str:
    try:
        return str(ipaddress.ip_address(value.strip()))
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be an IPv4 or IPv6 address") from None


def parse_uint(value: str, field: str, maximum: int | None = None) -> int:
    cleaned = value.strip()
    if not re.fullmatch(r"\d+", cleaned):
        raise ValueError(f"{field} must be a non-negative integer")
    number = int(cleaned)
    if maximum is not None and number > maximum:
        raise ValueError(f"{field} must be at most {maximum}")
    return number


def parse_port(value: str, field: str) -> int | None:
    cleaned = value.strip().lower()
    if cleaned in {"", "?", "-", "na", "none"}:
        return None
    try:
        number = int(cleaned, 16) if cleaned.startswith("0x") else int(cleaned)
    except ValueError:
        raise ValueError(f"{field} must be a decimal/hex port or missing") from None
    if not 0 <= number <= 65535:
        raise ValueError(f"{field} must be between 0 and 65535")
    return number


def parse_token(value: str, field: str) -> str:
    cleaned = value.strip()
    if not TOKEN_RE.fullmatch(cleaned):
        raise ValueError(f"{field} contains unsupported characters or is too long")
    return cleaned.lower()


def label_family(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if not LABEL_RE.fullmatch(cleaned):
        raise ValueError("Label contains unsupported characters or is too long")
    normalized = cleaned.lower().removeprefix("flow=")
    if normalized.startswith("from-botnet"):
        return "From-Botnet"
    if normalized.startswith("to-botnet"):
        return "To-Botnet"
    if normalized.startswith("from-normal"):
        return "From-Normal"
    if normalized.startswith("to-normal"):
        return "To-Normal"
    if "background" in normalized:
        return "Background"
    if "botnet" in normalized:
        return "Botnet (other label)"
    return "Other"


def load_flows(path: Path) -> tuple[list[Flow], list[int], str]:
    flows: list[Flow] = []
    invalid_lines: list[int] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        if set(FIELDS).issubset(headers):
            schema = "standard CSV"
            is_ctu = False
        elif CTU_FIELDS.issubset(headers):
            schema = "CTU-13/Argus flow CSV"
            is_ctu = True
        else:
            expected = ", ".join(FIELDS)
            ctu_expected = ", ".join(sorted(CTU_FIELDS))
            raise ValueError(f"CSV must use the standard columns ({expected}) or CTU-13 columns ({ctu_expected})")
        for row in reader:
            try:
                if is_ctu:
                    flows.append(Flow(
                        timestamp=parse_timestamp(row.get("StartTime") or "", ctu_format=True),
                        src_ip=parse_ip(row.get("SrcAddr") or "", "SrcAddr"),
                        dst_ip=parse_ip(row.get("DstAddr") or "", "DstAddr"),
                        src_port=parse_port(row.get("Sport") or "", "Sport"),
                        dst_port=parse_port(row.get("Dport") or "", "Dport"),
                        protocol=parse_token(row.get("Proto") or "", "Proto"),
                        byte_count=parse_uint(row.get("TotBytes") or "", "TotBytes"),
                        action=None,
                        label_family=label_family(row.get("Label") or ""),
                    ))
                else:
                    action_value = row.get("action") or ""
                    action = parse_token(action_value, "action") if action_value.strip() else None
                    raw_label = row.get("label") or row.get("Label") or ""
                    flows.append(Flow(
                        timestamp=parse_timestamp(row.get("timestamp") or ""),
                        src_ip=parse_ip(row.get("src_ip") or "", "src_ip"),
                        dst_ip=parse_ip(row.get("dst_ip") or "", "dst_ip"),
                        src_port=parse_port(row.get("src_port") or "", "src_port"),
                        dst_port=parse_port(row.get("dst_port") or "", "dst_port"),
                        protocol=parse_token(row.get("protocol") or "", "protocol"),
                        byte_count=parse_uint(row.get("bytes") or "", "bytes"),
                        action=action,
                        label_family=label_family(raw_label) if raw_label.strip() else None,
                    ))
            except ValueError:
                invalid_lines.append(reader.line_num)
    return flows, invalid_lines, schema


def network_aliases(flows: list[Flow]) -> dict[str, str]:
    totals: dict[str, tuple[int, int]] = {}
    for flow in flows:
        for value in (flow.src_ip, flow.dst_ip):
            address = ipaddress.ip_address(value)
            prefix = 24 if address.version == 4 else 64
            network = str(ipaddress.ip_network(f"{value}/{prefix}", strict=False))
            count, byte_count = totals.get(network, (0, 0))
            totals[network] = (count + 1, byte_count + flow.byte_count)
    ordered = sorted(totals.items(), key=lambda item: (-item[1][1], -item[1][0], item[0]))
    return {network: f"net-{number:02d}" for number, (network, _) in enumerate(ordered, 1)}


def display_ip(value: str, reveal: bool, aliases: dict[str, str]) -> str:
    if reveal:
        return value
    address = ipaddress.ip_address(value)
    prefix = 24 if address.version == 4 else 64
    network = str(ipaddress.ip_network(f"{value}/{prefix}", strict=False))
    return aliases[network]


def table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def window_number(timestamp: datetime, window_minutes: int) -> int:
    if timestamp.tzinfo is not None and timestamp.utcoffset() is not None:
        seconds = timestamp.astimezone(timezone.utc).timestamp()
    else:
        seconds = (timestamp - datetime(1970, 1, 1)).total_seconds()
    return int(seconds) // (window_minutes * 60)


def format_window_start(window: int, window_minutes: int, source_clock: bool) -> str:
    seconds = window * window_minutes * 60
    if source_clock:
        value = datetime(1970, 1, 1) + timedelta(seconds=seconds)
        return value.strftime("%Y-%m-%d %H:%M (source clock)")
    value = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return value.strftime("%Y-%m-%d %H:%M UTC")


def input_fingerprint(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def build_report(flows: list[Flow], invalid_lines: list[int], schema: str, threshold: int, window_minutes: int, top: int, reveal: bool, input_bytes: int, input_sha256: str, source_url: str | None, source_range_sha256: str | None, sample_note: str | None, limitation: str | None) -> str:
    aliases = {} if reveal else network_aliases(flows)
    protocols = Counter(flow.protocol.upper() for flow in flows)
    destination_ports: Counter[int | None] = Counter()
    source_flows: Counter[str] = Counter()
    source_bytes: Counter[str] = Counter()
    destination_flows: Counter[str] = Counter()
    destination_bytes: Counter[str] = Counter()
    labels = Counter(flow.label_family for flow in flows if flow.label_family)
    blocked_windows: Counter[tuple[str, int]] = Counter()
    has_action_field = any(flow.action is not None for flow in flows)
    total_bytes = 0

    for flow in flows:
        destination_ports[flow.dst_port] += 1
        source_flows[flow.src_ip] += 1
        source_bytes[flow.src_ip] += flow.byte_count
        destination_flows[flow.dst_ip] += 1
        destination_bytes[flow.dst_ip] += flow.byte_count
        total_bytes += flow.byte_count
        if flow.action in BLOCKED_ACTIONS:
            blocked_windows[(flow.src_ip, window_number(flow.timestamp, window_minutes))] += 1

    lines = ["# FlowLens — 네트워크 흐름 보고서", "", "## 요약", ""]
    lines.append(f"- 입력 형식: {schema}")
    lines.append(f"- 분석 흐름: {len(flows):,}건")
    lines.append(f"- 건너뛴 잘못된 행: {len(invalid_lines):,}건")
    lines.append(f"- 합계 전송량: {total_bytes:,} bytes")
    lines.append(f"- 주소 표시: {'원문 표시(사용자 선택)' if reveal else '대역별 별칭(net-##)으로 익명화'}")
    lines.append(f"- 입력 파일 크기: {input_bytes:,} bytes")
    lines.append(f"- 입력 파일 SHA-256: `{input_sha256}`")
    if source_url:
        lines.append(f"- 원본 출처: {source_url}")
    if source_range_sha256:
        lines.append(f"- 내려받은 원본 구간 SHA-256: `{source_range_sha256}`")
    if sample_note:
        lines.append(f"- 입력 구간: {sample_note}")
    if limitation:
        lines.append(f"- 표본 한계: {limitation}")
    if schema.startswith("CTU-13"):
        lines.append("- 원본 시각: 시간대가 없는 CTU-13 시각 문자열 그대로 유지")
    lines.extend(["", "## 프로토콜", ""])
    lines.extend(table(("프로토콜", "흐름 수"), [(name, f"{count:,}") for name, count in protocols.most_common()]))

    if labels:
        lines.extend(["", "## 원본 라벨 계열", ""])
        lines.extend(table(("라벨 계열", "흐름 수"), [(str(name), f"{count:,}") for name, count in labels.most_common(top)]))
        lines.append("")
        lines.append("라벨은 데이터 제공자가 붙인 분류입니다. `To-Botnet`/`To-Normal`은 해당 호스트를 향한 흐름이며 그 자체를 악성/정상 발신으로 간주하지 않습니다.")

    port_rows = []
    for port, count in destination_ports.most_common(top):
        if port is None:
            label = "미상 포트"
        else:
            label = f"{port} ({COMMON_PORTS[port]})" if port in COMMON_PORTS else str(port)
        port_rows.append((label, f"{count:,}"))
    lines.extend(["", "## 목적지 포트", ""])
    lines.extend(table(("포트", "흐름 수"), port_rows or [("없음", "0")]))

    def endpoint_rows(counts: Counter[str], byte_counts: Counter[str]) -> list[tuple[str, ...]]:
        grouped: dict[str, tuple[int, int]] = {}
        for host, count in counts.items():
            label = display_ip(host, reveal, aliases)
            previous_count, previous_bytes = grouped.get(label, (0, 0))
            grouped[label] = (previous_count + count, previous_bytes + byte_counts[host])
        ordered = sorted(grouped.items(), key=lambda item: (-item[1][1], -item[1][0], item[0]))[:top]
        return [(label, f"{count:,}", f"{byte_count:,}") for label, (count, byte_count) in ordered]

    lines.extend(["", "## 상위 출발지", ""])
    lines.extend(table(("주소", "흐름 수", "bytes"), endpoint_rows(source_flows, source_bytes) or [("없음", "0", "0")]))
    lines.extend(["", "## 상위 목적지", ""])
    lines.extend(table(("주소", "흐름 수", "bytes"), endpoint_rows(destination_flows, destination_bytes) or [("없음", "0", "0")]))

    if has_action_field:
        bursts = sorted(
            ((host, window, count) for (host, window), count in blocked_windows.items() if count >= threshold),
            key=lambda item: (-item[2], item[0], item[1]),
        )
        burst_rows = []
        source_clock = any(flow.timestamp.tzinfo is None for flow in flows)
        for host, window, count in bursts[:top]:
            start = format_window_start(window, window_minutes, source_clock)
            burst_rows.append((display_ip(host, reveal, aliases), start, f"{count:,}"))
        lines.extend(["", f"## 차단 집중 구간 ({window_minutes}분 창, {threshold}건 이상)", ""])
        lines.extend(table(("출발지", "구간 시작", "차단 흐름"), burst_rows or [("기준 초과 없음", "—", "0")]))
    else:
        lines.extend(["", "## 차단 이벤트", "", "입력에는 방화벽 action 열이 없어 차단 집중 분석을 적용하지 않았습니다."])

    if invalid_lines:
        shown = ", ".join(str(number) for number in invalid_lines[:10])
        suffix = " …" if len(invalid_lines) > 10 else ""
        lines.extend(["", f"잘못된 행은 분석에서 제외했습니다. 행 번호(최대 10개): {shown}{suffix}"])
    lines.extend(["", "> 이 도구는 입력 파일만 읽으며 네트워크 연결이나 패킷 수집을 하지 않습니다."])
    return "\n".join(lines) + "\n"


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("양의 정수를 입력하세요") from None
    if parsed < 1:
        raise argparse.ArgumentTypeError("양의 정수를 입력하세요")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="승인된 네트워크 흐름 CSV를 로컬에서 분석하고 익명화 Markdown 보고서를 만듭니다.")
    parser.add_argument("input", type=Path, help="표준 CSV 또는 CTU-13/Argus binetflow CSV")
    parser.add_argument("-o", "--output", type=Path, help="보고서 경로 (기본값: 입력 파일 옆 flowlens-report.md)")
    parser.add_argument("--threshold", type=positive_int, default=5, help="차단 집중 기준 건수 (기본값: 5)")
    parser.add_argument("--window-minutes", type=positive_int, default=10, help="차단 집계 시간창(분, 기본값: 10)")
    parser.add_argument("--top", type=positive_int, default=10, help="표에 표시할 최대 행 수 (기본값: 10)")
    parser.add_argument("--show-addresses", action="store_true", help="보고서에 IP 원문 표시 (기본은 네트워크 단위 익명화)")
    parser.add_argument("--source-url", help="입력 원본의 공개 출처 URL")
    parser.add_argument("--source-range-sha256", help="내려받은 원본 바이트 구간의 SHA-256")
    parser.add_argument("--sample-note", help="입력한 실제 표본의 범위와 변환 설명")
    parser.add_argument("--limitation", help="결과를 과대해석하지 않도록 표본/자료의 한계 설명")
    args = parser.parse_args(argv)
    if args.top > 50:
        parser.error("--top은 50 이하여야 합니다")

    output = args.output or args.input.with_name("flowlens-report.md")
    try:
        flows, invalid_lines, schema = load_flows(args.input)
        if not flows:
            raise ValueError("분석할 유효한 흐름이 없습니다")
        input_bytes, input_sha256 = input_fingerprint(args.input)
        report = build_report(flows, invalid_lines, schema, args.threshold, args.window_minutes, args.top, args.show_addresses, input_bytes, input_sha256, args.source_url, args.source_range_sha256, args.sample_note, args.limitation)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(f"FlowLens 오류: {exc}", file=sys.stderr)
        return 1

    print(f"보고서 저장: {output}")
    if invalid_lines:
        print(f"주의: 잘못된 행 {len(invalid_lines)}개를 제외했습니다.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
