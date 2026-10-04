"""Compare three preserved CTU-13 byte ranges; never downloads or generates traffic."""
import argparse
import csv
import hashlib
import importlib.util
import ipaddress
import json
import sys
from collections import Counter
from pathlib import Path

RANGES = [
    ('prefix', '시작', '0-2097151', '2d0af0c7ff129bb2fefe18a74ba81828f4ee4640cb45982e28171af1dae2141d'),
    ('mid', '중간', '192266059-194363210', '8f52127f49a3076003848bc6c5584c15b7008fb58581266190cfd8cd5c02274b'),
    ('tail', '끝', '384532119-386629270', '9d98509776c3d7f4f89f82cb990355e57492de80977f087207a66347df9f8add'),
]
SOURCE = 'https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-42/detailed-bidirectional-flow-labels/capture20110810.binetflow'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(work, flow_path):
    spec = importlib.util.spec_from_file_location('flowlens_samplescope', flow_path)
    flow = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = flow
    spec.loader.exec_module(flow)
    results = []
    for key, label, byte_range, expected in RANGES:
        raw = work / f'ctu13-botnet42-{key}.bin'
        source = work / f'ctu13-botnet42-{key}-complete.binetflow'
        if digest(raw) != expected:
            raise ValueError(f'{key}: preserved source fingerprint changed')
        raw_lines = raw.read_bytes().splitlines()
        input_rows = source.read_bytes().splitlines()[1:]
        derived_rows_match = any(input_rows == raw_lines[start:end]
                                 for start in (0, 1) for end in (len(raw_lines), len(raw_lines) - 1))
        if not derived_rows_match:
            raise ValueError(f'{key}: input rows do not match the preserved byte range')
        with source.open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        protocols = Counter(row['Proto'].strip().upper() for row in rows)
        botnet = sum(row['Label'].strip().lower().removeprefix('flow=').startswith('from-botnet') for row in rows)
        byte_total = sum(int(row['TotBytes']) for row in rows)
        parsed, invalid, _ = flow.load_flows(source)
        eligible = []
        excluded = Counter()
        for row in rows:
            try:
                ipaddress.ip_address(row['SrcAddr'].strip())
                ipaddress.ip_address(row['DstAddr'].strip())
            except ValueError:
                excluded[row['Proto'].upper()] += 1
                continue
            eligible.append(row)
        crosscheck = (len(parsed) == len(eligible) and len(invalid) == sum(excluded.values())
                      and Counter(r.protocol.upper() for r in parsed) == Counter(r['Proto'].upper() for r in eligible)
                      and sum(r.byte_count for r in parsed) == sum(int(r['TotBytes']) for r in eligible)
                      and sum(r.label_family == 'From-Botnet' for r in parsed) == botnet)
        if not crosscheck:
            raise ValueError(f'{key}: CSV aggregate and FlowLens parser disagree')
        results.append(dict(segment=key, label=label, byte_range=byte_range, records=len(rows),
                            flowlens_excluded=len(invalid), excluded_protocols=dict(excluded), flowlens_records=len(parsed), protocols=dict(sorted(protocols.items())),
                            from_botnet=botnet, from_botnet_pct=round(botnet / len(rows) * 100, 4),
                            total_bytes=byte_total, input_sha256=digest(source), raw_sha256=expected,
                            derived_rows_match_raw=derived_rows_match, parser_crosscheck=crosscheck))
    return dict(source_url=SOURCE, method='Preserved non-random byte slices; direct CSV versus FlowLens parsing',
                limitation='Three selected byte ranges are not random samples and do not estimate population attack prevalence.',
                total_records=sum(r['records'] for r in results), segments=results)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--flowlens', type=Path, default=Path(__file__).resolve().parent.parent / '01-flowlens/flowlens.py')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = run(args.work, args.flowlens)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'samplescope-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# SampleScope — 표본 위치에 따른 네트워크 흐름 비교', '',
             '실행일: 2026-10-02 (한국 시간). 기존에 보관한 실제 CTU-13 세 바이트 구간을 재사용했습니다.',
             f'원본 출처: {SOURCE}', '', '## 실제 결과', '',
             '| 구간 | 흐름 | UDP | TCP | From-Botnet 라벨 | 라벨 비율 |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in result['segments']:
        lines.append(f"| {r['label']} | {r['records']:,} | {r['protocols'].get('UDP', 0):,} | {r['protocols'].get('TCP', 0):,} | {r['from_botnet']:,} | {r['from_botnet_pct']:.4f}% |")
    lines += ['', f"세 구간 합계: {result['total_records']:,}행. 세 구간 모두 원본 구간 해시 일치, 분석 입력의 각 행이 원본 구간의 연속된 완전한 행과 일치, IPv4/IPv6 범위에서 FlowLens 파서와 CSV 별도 집계 일치.",
              '', '## 재현 방법', '', 'Python 3.10 이상에서 보관된 입력 6개를 포함한 폴더를 지정합니다.', '',
              '`python samplescope.py --work <원본-보관-폴더> --output <결과-폴더>`', '',
              '원시 자료는 공개 사이트에 포함하지 않습니다. 동일 입력이 있어야 재실행할 수 있습니다.', '',
              '## 검사 중 발견한 차이', '',
              '시작 구간 CSV는 15,279행입니다. IPX/SPX 1행의 주소가 IPv4/IPv6 형식이 아니므로 FlowLens는 이를 제외해 15,278행을 분석합니다. SampleScope 원본 분포에는 이 1행을 포함하며, 교차 확인은 IPv4/IPv6 주소가 있는 행에 한정합니다. 중간·끝 구간은 제외 행이 없습니다.', '',
              '## 판단과 제한', '',
              '중간 구간에서만 From-Botnet 발신 라벨이 관측되었습니다. 구간 선택에 따라 관측값이 달라진다는 근거이며, 0건인 구간을 안전하다고 판정할 수 없습니다.',
              '세 구간은 과거 목적 탐색에서 선택한 비무작위 바이트 구간입니다. 독립 확률 표본, 전체 공격률 추정, 탐지 성능 평가가 아닙니다.',
              'From-Botnet은 제공자 라벨이며 이 프로젝트에서 새로 탐지한 공격이 아닙니다. 모든 구현·집계는 AI가 수행했으며 사용자 본인의 실습 성과로 주장하지 않습니다.',
              'CSV 별도 집계와 FlowLens 파서를 비교했습니다. 구현 경로가 다른 교차 확인이며 제3자 감사가 아닙니다.', '', '## 입력 지문', '']
    for r in result['segments']:
        lines += [f"### {r['label']}", f"- 원본 bytes: {r['byte_range']}", f"- 원본 구간 SHA-256: `{r['raw_sha256']}`", f"- 분석 입력 SHA-256: `{r['input_sha256']}`", '']
    (args.output / 'samplescope-report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
